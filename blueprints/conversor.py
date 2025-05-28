from flask import Blueprint, render_template, request, flash, send_file, url_for, current_app, session, redirect
import pandas as pd
import os
import unicodedata
from datetime import timedelta
from openpyxl.styles import PatternFill, Font

conversor_bp = Blueprint('conversor', __name__, template_folder='templates')

DAY_NAMES = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
    4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
}

SERVICES = [
    'Sop_Conectividad', 'Sop_Flow', 'Esp_CATV', 'Esp_Movil', 'Esp_XDSL',
    'Digital', 'CBS', 'SMB_TecnicaIN', 'SMB_Digital'
]

@conversor_bp.route('/conversor', methods=['GET', 'POST'])
def conversor():
    download_url = None
    if request.method == 'POST':
        servicio  = request.form.get('servicio')
        prog_file = request.files.get('prog_file')
        if not servicio or not prog_file:
            flash('Selecciona un servicio y un archivo.', 'warning')
            return render_template('conversor.html', title='Conversor', services=SERVICES)

        upload_dir = current_app.config.get('UPLOAD_FOLDER', os.getcwd())
        in_path    = os.path.join(upload_dir, 'input_prog.xlsx')
        prog_file.save(in_path)

        # 1) Leer programación y filtrar
        df = pd.read_excel(in_path)
        if 'SERVICIO' in df.columns:
            key = servicio.split('_')[-1]
            df = df[df['SERVICIO'].str.contains(key, case=False, na=False)]

        # 2) Expandir nombres
        df = df.dropna(subset=['Nombres_Presentes'])
        records = []
        for _, row in df.iterrows():
            for raw in str(row['Nombres_Presentes']).split(';'):
                name = raw.strip().upper()
                if not name:
                    continue
                if ',' in name:
                    ape, nom = [p.strip() for p in name.split(',',1)]
                    name = f"{nom} {ape}"
                new_row = row.copy()
                new_row['Nombre'] = name
                records.append(new_row)
        df = pd.DataFrame(records)

        # 3) Cargar nómina con DNI, SUPERVISOR e INGRESO
        nomina_path = session.get('nomina_path')
        if not nomina_path or not os.path.exists(nomina_path):
            flash("No se encontró la nómina cargada.", 'danger')
            return render_template('conversor.html', title='Conversor', services=SERVICES)

        df_nom = pd.read_excel(nomina_path)
        df_nom.columns = df_nom.columns.str.strip()
        required = ('NOMBRE','DNI','SUPERIOR','INGRESO')
        if not all(c in df_nom.columns for c in required):
            flash("La nómina debe tener columnas 'NOMBRE','DNI','SUPERIOR','INGRESO'.", 'danger')
            return render_template('conversor.html', title='Conversor', services=SERVICES)

        df_nom = df_nom[['NOMBRE','DNI','SUPERIOR','INGRESO']].rename(
            columns={'NOMBRE':'Nombre','DNI':'DNI','INGRESO':'Ingreso'}
        )
        df_nom['Nombre']  = df_nom['Nombre'].str.upper().str.strip()
        df_nom['DNI']     = df_nom['DNI'].astype(str).str.strip()
        df_nom['Ingreso'] = pd.to_datetime(
            df_nom['Ingreso'].astype(str), errors='coerce'
        ).dt.time

        # 4) Merge programación + nómina
        df = df.merge(df_nom, on='Nombre', how='left')
        if df[['DNI','SUPERIOR','Ingreso']].isnull().any().any():
            flash("Revisa que los nombres coincidan y que 'DNI','Ingreso' estén presentes.", 'danger')
            return render_template('conversor.html', title='Conversor', services=SERVICES)

        # 5) Fechas e intervalos
        df['Fecha']        = pd.to_datetime(df['Fecha'], errors='coerce').dt.date
        df = df.dropna(subset=['Fecha'])
        df['Intervalo_dt'] = pd.to_datetime(
            df['Intervalo'], format='%H:%M', errors='coerce'
        ).dt.time
        df['Intervalo']    = df['Intervalo_dt'].astype(str)
        df['Semana']       = df['Fecha'].apply(lambda d: d - timedelta(days=d.weekday()))
        df = df.sort_values(['Fecha','Intervalo_dt'])

        # 6) Generar Excel con formato
        file_name = f'convertido_tabs_{servicio}.xlsx'
        out_path  = os.path.join(upload_dir, file_name)
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            workbook = writer.book
            header_blue   = PatternFill('solid', fgColor='538DD5')
            header_yellow = PatternFill('solid', fgColor='FFC000')
            font_bold     = Font(color='000000', bold=True)

            for semana, group in df.groupby('Semana'):
                hoja = semana.strftime('Sem %Y-%m-%d')
                tmp  = group.copy()
                tmp['Dia_Num']  = tmp['Fecha'].apply(lambda d: d.weekday())
                tmp['Presente'] = 1

                # Pivot de presencia
                pivot = tmp.pivot_table(
                    index='Nombre', columns='Dia_Num',
                    values='Presente', aggfunc='sum', fill_value=0
                )
                for i in range(7):
                    pivot[i] = pivot.get(i, 0)
                pivot = pivot.reindex(columns=range(7), fill_value=0)
                pivot.rename(columns=DAY_NAMES, inplace=True)
                pivot = pivot.reset_index()

                # 0→'Franco', >0→1
                for col in DAY_NAMES.values():
                    pivot[col] = pivot[col].apply(lambda v: 1 if v>0 else 'Franco')

                # Añadir DNI, SUPERVISOR e Intervalo real (Ingreso)
                map_df = tmp.groupby('Nombre').agg({'SUPERIOR':'first'}).reset_index()
                map_df = map_df.merge(
                    df_nom[['Nombre','DNI','Ingreso']],
                    on='Nombre', how='left'
                )
                map_df['Intervalo'] = map_df['Ingreso'].apply(
                    lambda t: t.strftime('%H:%M') if pd.notnull(t) else ''
                )
                pivot = pivot.merge(
                    map_df[['Nombre','DNI','SUPERIOR','Intervalo']],
                    on='Nombre', how='left'
                )

                # Calcular breaks (incluso con <3 franjas)
                break_cols = []
                for dnum, dname in DAY_NAMES.items():
                    colb = f'Break_{dname}'
                    break_cols.append(colb)
                    brk = {}
                    day_rows = tmp[tmp['Dia_Num']==dnum]
                    for nm, grp in day_rows.groupby('Nombre'):
                        horas = sorted(grp['Intervalo_dt'])
                        if not horas:
                            continue
                        if len(horas) < 3:
                            # con pocas franjas, tomamos la mediana
                            med = horas[len(horas)//2]
                            brk[nm] = med.strftime('%H:%M')
                        else:
                            inicio = pd.to_datetime(horas[0].strftime('%H:%M')) + timedelta(hours=2)
                            fin    = pd.to_datetime(horas[-1].strftime('%H:%M')) - timedelta(hours=2)
                            poss   = [
                                pd.to_datetime(h.strftime('%H:%M'))
                                for h in horas
                                if inicio <= pd.to_datetime(h.strftime('%H:%M')) <= fin
                            ]
                            if poss:
                                brk[nm] = poss[0].strftime('%H:%M')
                            else:
                                med = horas[len(horas)//2]
                                brk[nm] = med.strftime('%H:%M')
                    pivot[colb] = pivot['Nombre'].map(brk).fillna('')

                # Orden de columnas
                cols = ['DNI','Nombre','SUPERIOR','Intervalo'] + \
                       list(DAY_NAMES.values()) + break_cols

                pivot[cols].to_excel(writer, sheet_name=hoja, index=False)
                ws = writer.sheets[hoja]

                # Colorear la cabecera
                for idx, col in enumerate(cols):
                    cell = ws.cell(row=1, column=idx+1)
                    if col in DAY_NAMES.values():
                        cell.fill = header_yellow
                    else:
                        cell.fill = header_blue
                    cell.font = font_bold

        session['last_file'] = file_name
        download_url = url_for('conversor.download')

    return render_template(
        'conversor.html',
        title='Conversor',
        services=SERVICES,
        download_url=download_url
    )


@conversor_bp.route('/conversor/download')
def download():
    upload_dir = current_app.config.get('UPLOAD_FOLDER', os.getcwd())
    last_file  = session.get('last_file')
    if last_file and os.path.exists(os.path.join(upload_dir, last_file)):
        path = os.path.join(upload_dir, last_file)
    else:
        files = [f for f in os.listdir(upload_dir)
                 if f.startswith("convertido_tabs_") and f.endswith(".xlsx")]
        files = sorted(
            files,
            key=lambda f: os.path.getmtime(os.path.join(upload_dir, f)),
            reverse=True
        )
        if not files:
            flash("No se encontró el archivo para descargar.","danger")
            return redirect(url_for('conversor.conversor'))
        path = os.path.join(upload_dir, files[0])

    return send_file(
        path,
        as_attachment=True,
        download_name=os.path.basename(path)
    )
