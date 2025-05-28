from flask import Blueprint, render_template, request, session, flash, send_file, url_for, redirect, current_app
from werkzeug.utils import secure_filename
from services.personal_service import PersonalService
import os

# Blueprint para el conversor de Personal
conversor_personal_bp = Blueprint(
    'personal_conversor',         # endpoint unique
    __name__,
    url_prefix='/personal/conversor',  # rutas bajo /personal/conversor
    template_folder='../templates'     # usa carpeta de templates global
)

svc = PersonalService()

@conversor_personal_bp.route('/', methods=['GET', 'POST'])
def conversor_personal():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if 'servicio' not in session or session['servicio'] != 'personal':
        flash('Servicio Personal no seleccionado.', 'warning')
        return redirect(url_for('selector'))

    download_url = None
    if request.method == 'POST':
        archivo = request.files.get('archivo')
        if not archivo:
            flash('Selecciona un archivo para convertir.', 'warning')
        else:
            # Guardar archivo de entrada
            filename = secure_filename(archivo.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            input_path = os.path.join(upload_folder, filename)
            archivo.save(input_path)

            # Llamar método convertir() de PersonalService
            out_path = svc.convertir(input_path)
            download_url = url_for(
                'personal_conversor.download',
                filename=os.path.basename(out_path)
            )

    return render_template(
        'conversor.html',
        title='Conversor Personal',
        download_url=download_url
    )

@conversor_personal_bp.route('/download/<filename>')
def download(filename):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_file(
        os.path.join(upload_folder, filename),
        as_attachment=True
    )
