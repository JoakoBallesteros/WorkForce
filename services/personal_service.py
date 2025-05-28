import os
import math
import pandas as pd
from datetime import datetime, timedelta, time
from openpyxl.styles import PatternFill


class PersonalService:
    """
    Servicio para procesar la nómina y generar el reporte de programación para Personal.
    """
    CONTRACT_HOURS = {'24HS': 6, '30HS': 6, '35HS': 7, '36HS': 6}
    SERVICE_KEY_MAP = {
        'Sop_Conectividad': 'Internet',
        'Sop_Flow': 'Flow',
        'Esp_CATV': 'CATV',
        'Esp_Movil': 'Movil',
        'Esp_XDSL': 'XDSL',
        'Digital': 'Digital',
        'CBS': 'PTF',
        'SMB_TecnicaIN': 'TecnicaIN',
        'SMB_Digital': 'Digital'
    }
    INGRESOS_VALIDOS = [8, 9, 10, 11, 14, 15, 18, 19]

    def procesar(self, nomina_path: str, req_file, servicio: str) -> str:
        """
        Lee la nómina (nomina_path) y el archivo de requeridos (req_file),
        calcula asignaciones, off days, movimientos, y exporta un Excel coloreado.
        Devuelve la ruta al archivo generado.
        """
        base = os.path.abspath(os.path.dirname(__file__))
        out_path = os.path.join(base, f"{servicio}_reporte.xlsx")

        # Guardar temporalmente el archivo de requeridos
        req_path = os.path.join(base, f"{servicio}_requeridos.xlsx")
        req_file.save(req_path)

        # 1) Leer nómina
        df_nom = pd.read_excel(nomina_path)
        df_nom.columns = df_nom.columns.str.strip()

        # 2) Long format de requeridos
        df_d = pd.read_excel(req_path, sheet_name=servicio, skiprows=[0, 2], header=0)
        df_d.rename(columns={df_d.columns[0]: 'Intervalo'}, inplace=True)
        df_d['Intervalo'] = pd.to_datetime(
            df_d['Intervalo'], format='%H:%M:%S', errors='coerce'
        ).dt.time
        df_d.dropna(subset=['Intervalo'], inplace=True)
        date_cols = [
            c for c in df_d.columns[1:]
            if not pd.isna(pd.to_datetime(str(c), errors='coerce'))
        ]
        df_long = (
            df_d.melt(
                id_vars=['Intervalo'], value_vars=date_cols,
                var_name='Fecha', value_name='Requeridos'
            )
            .dropna(subset=['Requeridos'])
        )
        df_long['Fecha'] = pd.to_datetime(df_long['Fecha']).dt.date
        df_long['Requeridos'] = df_long['Requeridos'].astype(int)

        # 3) Filtrar activos y calcular INGRESO/EGRESO
        key = self.SERVICE_KEY_MAP.get(servicio, servicio)
        df_x = df_nom[
            df_nom['SERVICIO'].str.contains(key, case=False, na=False) &
            (df_nom['ACTIVO'].str.upper() == 'ACTIVO')
        ].copy()
        df_x['INGRESO'] = pd.to_datetime(
            df_x['INGRESO'].astype(str),
            errors='coerce', infer_datetime_format=True
        ).dt.time
        df_x['EGRESO'] = [
            (datetime.combine(datetime.today(), ing) +
             timedelta(hours=self.CONTRACT_HOURS.get(str(con).strip().upper(), 24))
            ).time()
            for ing, con in zip(df_x['INGRESO'], df_x['CONTRATO'])
        ]
        df_x = df_x.sort_values('NOMBRE').reset_index(drop=True)

        # 4) Días de franco dinámicos
        def assign_off_days(df):
            offs = []
            weekend_idxs = [
                i for i, r in df.iterrows()
                if str(r['CONTRATO']).strip().upper() in ('30HS', '35HS')
            ]
            half = len(weekend_idxs) // 2
            for i, row in df.iterrows():
                c = str(row['CONTRATO']).strip().upper()
                if c == '24HS':
                    offs.append([(i + k) % 7 for k in range(3)])
                elif c in ('30HS', '35HS'):
                    wd = i % 5
                    we = 5 if weekend_idxs.index(i) < half else 6
                    offs.append([wd, we])
                elif c == '36HS':
                    offs.append([5 if i % 2 == 0 else 6])
                else:
                    offs.append([])
            return offs

        df_x['OFF_DAYS'] = assign_off_days(df_x)
        def is_off(row, f): return f.weekday() in row['OFF_DAYS']

        rows, simulacion, movimientos = [], [], []

        # 5) Asignación principal
        for _, r in df_long.iterrows():
            f, i, req = r['Fecha'], r['Intervalo'], r['Requeridos']
            # Límites dinámicos
            if req < 10:
                li, up = max(req - 1, 0), req + 1
            elif req < 20:
                li, up = max(req - 2, 0), req + 2
            else:
                li, up = math.floor(req * 0.9), math.ceil(req * 1.1)
            prime = 'Prime' if time(9, 0) <= i < time(21, 0) else 'No prime'

            df_av = df_x[~df_x.apply(lambda row: is_off(row, f), axis=1)]
            norm = (df_av['INGRESO'] <= i) & (i < df_av['EGRESO'])
            wrap = (df_av['EGRESO'] < df_av['INGRESO']) & (
                (df_av['INGRESO'] <= i) | (i < df_av['EGRESO'])
            )
            pres = df_av[norm | wrap].copy()
            cnt = len(pres)

            if f.weekday() == 6:
                sab = f - timedelta(days=1)
                hora = i.strftime('%H:%M')
                used = { nm for rec in rows for nm in rec['Nombres_Presentes'].split(';') if rec['Fecha']==sab and rec['Intervalo']==hora }
                pres = pres[~pres['NOMBRE'].isin(used)]
                p36 = pres[pres['CONTRATO'].str.upper() == '36HS']
                oth = pres.drop(p36.index)
                need = max(li - len(p36), 0)
                pres = pd.concat([p36, oth.head(need)])
                cnt = len(pres)

            falt, sobr = max(li - cnt, 0), max(cnt - up, 0)
            if falt > 0:
                movimientos.append({'Fecha': f, 'Intervalo': i.strftime('%H:%M'), 'Mover': falt, 'Desde': '', 'Hacia': ''})

            leader_col = next((c for c in pres.columns if c.strip().lower() in ('superior', 'jefe', 'lider')), None)
            lideres = pres[leader_col].dropna().unique().tolist() if leader_col else []
            estado = 'UNDER' if cnt < li else 'OVER' if cnt > up else 'LIMITE' if cnt == li else 'OK'

            rec = {'Fecha': f, 'Intervalo': i.strftime('%H:%M'), 'Prime': prime,
                   'Requeridos': req, 'Limite Inferior': li, 'Limite Superior': up,
                   'Faltante': falt, 'Sobrantes': sobr, 'Asignados': cnt,
                   'Estado': estado, 'Lider': ';'.join(lideres),
                   'Movimientos': '', 'Nombres_Presentes': ';'.join(pres['NOMBRE'].astype(str).unique())}
            rows.append(rec)
            simulacion.append(rec.copy())

        #'Desde' y 'Hacia'
        updated = []
        for mov in movimientos:
            date0 = mov['Fecha']
            int_tm = datetime.strptime(mov['Intervalo'], '%H:%M').time()
            search_date = date0 - timedelta(days=1) if int_tm < time(1, 0) else date0
            base_dt = datetime.combine(search_date, int_tm)

            donors = []
            for r in rows:
                if r['Estado'] == 'OVER' and r['Fecha'] == search_date:
                    cand_dt = datetime.combine(search_date, datetime.strptime(r['Intervalo'], '%H:%M').time())
                    delta = (cand_dt - base_dt).total_seconds()
                    if -2*3600 <= delta <= 2*3600 and delta != 0:
                        donors.append((abs(delta), r['Intervalo']))
            if donors:
                raw_desde = min(donors, key=lambda x: x[0])[1]
            else:
                eve = []
                for r in rows:
                    if r['Estado'] == 'OVER' and r['Fecha'] == search_date:
                        ct = datetime.strptime(r['Intervalo'], '%H:%M').time()
                        cd = datetime.combine(search_date, ct)
                        if cd <= datetime.combine(search_date, time(18, 30)):
                            dist = abs((datetime.combine(search_date, time(19, 0)) - cd).total_seconds())
                            eve.append((dist, r['Intervalo']))
                raw_desde = min(eve, key=lambda x: x[0])[1] if eve else '19:00 (extraordinario)'

            if '(' in raw_desde:
                mov['Desde'] = raw_desde
            else:
                hh = int(raw_desde.split(':')[0])
                cands = [h for h in self.INGRESOS_VALIDOS if h <= hh]
                sel = max(cands) if cands else min(self.INGRESOS_VALIDOS)
                mov['Desde'] = f"{sel:02d}:00"

            if int_tm < time(1, 0):
                mov['Hacia'] = '19:00'
            else:
                hh = int(int_tm.hour + (1 if int_tm.minute > 0 else 0))
                cands = [h for h in self.INGRESOS_VALIDOS if h >= hh]
                sel = min(cands) if cands else max(self.INGRESOS_VALIDOS)
                mov['Hacia'] = f"{sel:02d}:00"

            updated.append(mov)
        movimientos = updated

        # 7) Aplicar movimientos en simulación
        for mov in movimientos:
            for rec in simulacion:
                if rec['Fecha'] == mov['Fecha'] and rec['Intervalo'] == mov['Intervalo']:
                    rec['Asignados'] += mov['Mover']
                    rec['Estado'] = 'LIMITE'
                    rec['Movimientos'] = f"{mov['Mover']} desde {mov['Desde']} → {mov['Hacia']}"

        # 8) Exportar a Excel
        df_out = pd.DataFrame(rows)
        df_sim = pd.DataFrame(simulacion)
        df_out['Fecha'] = pd.to_datetime(df_out['Fecha'])
        df_sim['Fecha'] = pd.to_datetime(df_sim['Fecha'])

        fills = {
            'red': PatternFill('solid', fgColor='FF0000'),
            'yellow': PatternFill('solid', fgColor='FFFF00'),
            'orange': PatternFill('solid', fgColor='FFA500'),
            'green': PatternFill('solid', fgColor='00FF00')
        }
        with pd.ExcelWriter(out_path, engine='openpyxl') as w:
            nom = df_out.copy()
            nom.drop(columns=['Movimientos'], inplace=True)
            nom.to_excel(w, sheet_name='Nomina', index=False)
            ws = w.sheets['Nomina']
            cols = nom.columns.tolist()
            li_idx = cols.index('Limite Inferior') + 1
            up_idx = cols.index('Limite Superior') + 1
            asig_idx = cols.index('Asignados') + 1
            est_idx = cols.index('Estado') + 1
            for i in range(2, ws.max_row + 1):
                v = ws.cell(i, asig_idx).value
                l = ws.cell(i, li_idx).value
                u = ws.cell(i, up_idx).value
                c = ws.cell(i, est_idx)
                c.fill = (
                    fills['red'] if v < l else
                    fills['yellow'] if v > u else
                    fills['orange'] if v == l else
                    fills['green']
                )
            sim = df_sim.copy()
            sim.to_excel(w, sheet_name='Simulacion', index=False)
            ws = w.sheets['Simulacion']
            cols = sim.columns.tolist()
            li_idx = cols.index('Limite Inferior') + 1
            up_idx = cols.index('Limite Superior') + 1
            asig_idx = cols.index('Asignados') + 1
            est_idx = cols.index('Estado') + 1
            for i in range(2, ws.max_row + 1):
                v = ws.cell(i, asig_idx).value
                l = ws.cell(i, li_idx).value
                u = ws.cell(i, up_idx).value
                c = ws.cell(i, est_idx)
                c.fill = (
                    fills['red'] if v < l else
                    fills['yellow'] if v > u else
                    fills['orange'] if v == l else
                    fills['green']
                )
            if movimientos:
                mov_df = pd.DataFrame(movimientos)[['Fecha', 'Intervalo', 'Mover', 'Desde', 'Hacia']]
                mov_df.to_excel(w, sheet_name='Movimientos', index=False)

        return out_path
