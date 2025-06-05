import os
import re
import tempfile
from flask import (
    Flask, redirect, url_for, render_template,
    request, session, flash, send_file
)
from werkzeug.utils import secure_filename

# Importamos tu clase PersonalService y los mapas de servicios
from services.personal_service import PersonalService
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

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "clave_insegura_dev")
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.dirname(__file__))

# Registramos todos los blueprints automáticamente
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


@app.route('/selector', methods=['GET', 'POST'])
def selector():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Bajamos a minúsculas para comparar con la clave de SERVICES
        servicio = request.form.get('servicio', '').strip().lower()

        # Validamos que el valor sea uno de los keys de SERVICES **o "all"**
        if servicio not in (list(SERVICES.keys()) + ["all"]):
            flash('Debes seleccionar un servicio válido.', 'warning')
            return render_template(
                'selector.html',
                title='Selecciona Servicio',
                opciones=_build_opciones()  # reconstruimos la lista al volver
            )

        # Si llega aquí, valor válido → lo guardamos en session y redirigimos
        session['servicio'] = servicio
        return redirect(url_for('upload_nomina'))

    # Si es GET, mostramos la página con el select de servicios
    return render_template(
        'selector.html',
        title='Selecciona Servicio',
        opciones=_build_opciones()
    )


def _build_opciones():
    """
    Construye la lista de tuplas (clave, etiqueta) para rellenar el <select>.
    Fuerza a que “all” (Todos los servicios) sea la primera opción.
    El resto se toma de SERVICES + SERVICE_LABELS para mostrar la etiqueta.
    """
    opciones = []
    

    # 2) Luego agregamos (clave, SERVICE_LABELS[clave]) para cada servicio individual
    #    SERVICES es un dict que en tu proyecto mapea lowercase → algo, y SERVICE_LABELS
    #    mapea lowercase → “Etiqueta a mostrar en el select”. 
    for key in SERVICES.keys():
        # Ejemplo: key == "sop_conectividad", SERVICE_LABELS[key] == "Sop Conectividad"
        opciones.append((key, SERVICE_LABELS[key]))

    return opciones


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
            return render_template('nomina.html', title='Carga de Nómina')

        if not nomina_file.filename.lower().endswith('.xlsx'):
            flash('El archivo debe tener formato .xlsx', 'warning')
            return render_template('nomina.html', title='Carga de Nómina')

        # Guardamos siempre con el mismo nombre “nomina.xlsx” en la carpeta UPLOAD_FOLDER
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

    provider = session['servicio']  # Ya viene en minúsculas
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
    # Debug durante desarrollo; en producción quita debug=True
    app.run(debug=True)
