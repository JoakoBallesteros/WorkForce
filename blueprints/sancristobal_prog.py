from flask import Blueprint, render_template, request, session, flash, send_file, url_for, redirect
from services.sancristobal_service import SanCristobalService
import os

# Blueprint para el módulo "San Cristóbal"
sancristobal_bp = Blueprint(
    'sancristobal',               # coincide con provider='sancristobal'
    __name__,
    url_prefix='/sancristobal',    # rutas bajo /sancristobal
    template_folder='../templates'
)

svc = SanCristobalService()

@sancristobal_bp.route('/programacion', methods=['GET', 'POST'])
def programacion():
    # Verificar nómina cargada
    if not session.get('nomina_path'):
        flash('Subí antes la nómina.', 'warning')
        return redirect(url_for('upload_nomina'))

    # Opciones de hojas según SERVICE_KEY_MAP
    opciones = list(svc.SERVICE_KEY_MAP.keys())
    download_url = None

    if request.method == 'POST':
        hoja = request.form.get('servicio')
        req_file = request.files.get('requeridos')
        if not hoja or hoja not in opciones:
            flash('Selecciona un servicio válido.', 'warning')
        elif not req_file:
            flash('Selecciona el archivo de requeridos.', 'warning')
        else:
            # Procesar la programación
            out_xlsx = svc.procesar(
                nomina_path=session['nomina_path'],
                req_file=req_file,
                servicio=hoja
            )
            download_url = url_for(
                'sancristobal.download',
                filename=os.path.basename(out_xlsx)
            )

    return render_template(
        'programacion.html',
        title='Programación San Cristóbal',
        servicios=opciones,
        download_url=download_url
    )

@sancristobal_bp.route('/programacion/download/<filename>')
def download(filename):
    services_dir = os.path.abspath(os.path.join(__file__, '..', '..', 'services'))
    return send_file(
        os.path.join(services_dir, filename),
        as_attachment=True
    )
