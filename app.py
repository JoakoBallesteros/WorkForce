import os
import re
from flask import Flask, redirect, url_for, render_template, request, session, flash
from werkzeug.utils import secure_filename
from services import SERVICES, SERVICE_LABELS


# Blueprints
from blueprints.conversor import conversor_bp
from blueprints.personal_prog import personal_bp
from blueprints.sancristobal_prog import sancristobal_bp
from blueprints.curvas import curvas_bp
# TODO: importar e insertar aquí otros blueprints (e.g. lacaja_bp, sancor_bp, ...)

default_blueprints = [
    conversor_bp,
    personal_bp,
    sancristobal_bp,
    curvas_bp
    # agregar otros blueprints aquí...
]

# Servicios disponibles para selector
from services import SERVICES as SERVICE_MAP

# Inicializar la app de Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "clave_insegura_dev")
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.dirname(__file__))

# Registrar blueprints dinámicamente (después de crear app)
for bp in default_blueprints:
    app.register_blueprint(bp)

# Credenciales válidas (usuarios permitidos)
default_credentials = {
    "joaquin.ballesteros@konecta.com": "Konecta+478",
    "enrique.juarez@konecta.com":    "Limon2026+-",
    "maria.gomez@konecta.com":       "Passwd123",
}

# Regex para validar formato de usuario
USERNAME_REGEX = re.compile(r'^[a-zA-Z]+\.[a-zA-Z]+@konecta\.com$')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        pwd  = request.form.get('password', '')

        # Validar formato de usuario
        if not USERNAME_REGEX.match(user):
            flash('El usuario debe ser nombre.apellido@konecta.com', 'warning')
            return render_template('login.html', title='Login')

        # Validar credenciales
        if default_credentials.get(user) == pwd:
            session.clear()
            session['logged_in'] = True
            return redirect(url_for('selector'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html', title='Login')

from services import SERVICES, SERVICE_LABELS

@app.route('/selector', methods=['GET', 'POST'])
def selector():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        servicio = request.form['servicio'].lower()
        if servicio not in SERVICES:
            flash('Debes seleccionar un servicio válido.', 'warning')
        else:
            session['servicio'] = servicio
            return redirect(url_for('upload_nomina'))

    # pasamos lista de tuplas (clave, etiqueta) al template
    opciones = [(k, SERVICE_LABELS[k]) for k in SERVICES.keys()]
    return render_template(
        'selector.html',
        title='Selecciona Servicio',
        opciones=opciones
    )
@app.route('/nomina', methods=['GET', 'POST'])
def upload_nomina():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if 'servicio' not in session:
        return redirect(url_for('selector'))

    if request.method == 'POST':
        nomina_file = request.files.get('nomina')
        if not nomina_file:
            flash('Selecciona un archivo de nómina (.xlsx)', 'warning')
        elif not nomina_file.filename.lower().endswith('.xlsx'):
            flash('El archivo debe tener formato .xlsx', 'warning')
        else:
            filename = secure_filename('nomina.xlsx')
            path     = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            nomina_file.save(path)
            session['nomina_path'] = path
            return redirect(url_for('menu'))

    return render_template('nomina.html', title='Carga de Nómina')

@app.route('/menu')
def menu():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if 'servicio' not in session:
        return redirect(url_for('selector'))
    if 'nomina_path' not in session:
        return redirect(url_for('upload_nomina'))

    # Normalizamos a minúsculas para el blueprint de programación
    provider = session['servicio'].lower()
    programacion_url = url_for(f"{provider}.programacion")
    conversor_url     = url_for("conversor.conversor")
    curvas_url       = url_for("curvas.index")

    return render_template(
        'index.html',
        title='Menú Principal',
        programacion_url=programacion_url,
        conversor_url=conversor_url,
        curvas_url=curvas_url
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
