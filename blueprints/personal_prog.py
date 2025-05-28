from flask import Blueprint, render_template, request, session, flash, send_file, url_for, redirect
from services.personal_service import PersonalService
import os

# Blueprint para el módulo "Personal"
personal_bp = Blueprint(
    'personal',                  # coincide con provider='personal'
    __name__,
    url_prefix='/personal',      # rutas bajo /personal
    template_folder='../templates'  # usa la carpeta global de templates
)

svc = PersonalService()

@personal_bp.route('/programacion', methods=['GET', 'POST'])
def programacion():
    # Verificamos que exista la nómina cargada
    if not session.get('nomina_path'):
        flash('Subí antes la nómina.', 'warning')
        return redirect(url_for('upload_nomina'))

    download_url = None
    # Opciones de hojas disponibles
    opciones = list(svc.SERVICE_KEY_MAP.keys())

    if request.method == 'POST':
        # Hoja seleccionada del archivo de requeridos
        hoja = request.form.get('servicio')
        req_file = request.files.get('requeridos')

        if not hoja or hoja not in opciones:
            flash('Selecciona un servicio válido para programación.', 'warning')
        elif not req_file:
            flash('Selecciona el archivo de requeridos.', 'warning')
        else:
            # Procesar usando la hoja correcta
            out_xlsx = svc.procesar(
                nomina_path=session['nomina_path'],
                req_file=req_file,
                servicio=hoja
            )
            download_url = url_for(
                'personal.download',
                filename=os.path.basename(out_xlsx)
            )

    return render_template(
        'programacion.html',    # plantilla genérica
        title='Programación Personal',
        servicios=opciones,
        download_url=download_url
    )

@personal_bp.route('/programacion/download/<filename>')
def download(filename):
    services_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'services'))
    return send_file(
        os.path.join(services_dir, filename),
        as_attachment=True
    )
