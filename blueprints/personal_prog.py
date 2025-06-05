from flask import (
    Blueprint, render_template, request,
    session, flash, send_file, url_for, redirect
)
from services.personal_service import PersonalService
import os
from datetime import date, timedelta
import calendar

personal_bp = Blueprint(
    'personal',                  # nombre interno del blueprint
    __name__,
    url_prefix='/personal',      # todas las rutas van bajo /personal
    template_folder='../templates'
)

svc = PersonalService()

@personal_bp.route('/programacion', methods=['GET', 'POST'])
def programacion():
    # 1) Verificar que ya exista la nómina en sesión
    if not session.get('nomina_path'):
        flash('Subí antes la nómina.', 'warning')
        return redirect(url_for('upload_nomina'))

    download_url = None

    # 2) Definimos las opciones de “Servicio” (clave, etiqueta) para el <select>
    opciones = [
        ("ALL", "Todos los servicios"),
        ("Sop_Conectividad", "Sop Conectividad"),
        ("Sop_Flow",       "Sop Flow"),
        ("Esp_CATV",       "Esp CATV"),
        ("Esp_Movil",      "Esp Móvil"),
        ("Esp_XDSL",       "Esp XDSL"),
        ("Digital",        "Digital"),
        ("CBS",            "CBS"),
    ]
    # Y también las opciones para “Periodo”
    periodos = [
        ("mes",  "Mes completo"),
        ("sem1", "Semana 1"),
        ("sem2", "Semana 2"),
        ("sem3", "Semana 3"),
        ("sem4", "Semana 4"),
    ]

    # Extraemos solo las claves válidas de servicios y de periodos
    keys_servicios = [clave for clave, _ in opciones]
    keys_periodos  = [clave for clave, _ in periodos]

    if request.method == 'POST':
        hoja    = request.form.get('servicio')    # e.g. "ALL" o "Sop_Conectividad"
        periodo = request.form.get('periodo')     # e.g. "mes", "sem1", ...
        req_file = request.files.get('requeridos')

        # 3) Validaciones
        if not hoja or hoja not in keys_servicios:
            flash('Selecciona un servicio válido para programación.', 'warning')
        elif not periodo or periodo not in keys_periodos:
            flash('Selecciona un periodo válido.', 'warning')
        elif not req_file:
            flash('Selecciona el archivo de requeridos (.xlsx).', 'warning')
        else:
            try:
                # 4) Invocamos PersonalService.procesar pasándole “servicio” y “periodo”
                out_xlsx = svc.procesar(
                    nomina_path = session['nomina_path'],
                    req_file    = req_file,
                    servicio    = hoja,
                    periodo     = periodo
                )
            except Exception as e:
                flash(f"Error al generar la programación: {e}", "danger")
                return render_template(
                    'programacion.html',
                    title='Programación Personal',
                    servicios=opciones,
                    periodos=periodos,
                    download_url=None
                )

            # 5) Si se generó bien, construimos la URL para descarga
            download_url = url_for(
                'personal.download',
                filename=os.path.basename(out_xlsx)
            )

    return render_template(
        'programacion.html',
        title='Programación Personal',
        servicios=opciones,
        periodos=periodos,
        download_url=download_url
    )


@personal_bp.route('/programacion/download/<filename>')
def download(filename):
    """
    Entrega el archivo .xlsx generado que está guardado en la carpeta 'services'.
    """
    services_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'services'))
    ruta_completa = os.path.join(services_dir, filename)

    if not os.path.isfile(ruta_completa):
        flash("El archivo solicitado no existe.", "danger")
        return redirect(url_for('personal.programacion'))

    return send_file(
        ruta_completa,
        as_attachment=True
    )
