import os
import re
import tempfile
from dotenv import load_dotenv
from flask import (
    Flask, redirect, url_for, render_template,
    request, session, flash, send_file
)
from werkzeug.utils import secure_filename

# Carga variables de entorno desde .env
load_dotenv()

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

# SECRET_KEY ahora se lee desde variable de entorno ‘SECRET_KEY’.
# Si no está definida, se usa un fallback de desarrollo, pero en producción
# deberías definir SECRET_KEY en tu .env o en la configuración del servidor.
app.secret_key = os.getenv("SECRET_KEY", "clave_insegura_dev")

# Carpeta donde se guardan archivos subidos
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.dirname(__file__))

# Registramos todos los blueprints automáticamente
for bp in default_blueprints:
    app.register_blueprint(bp)

# ——————————————————————————————————————————————————————————————
# En lugar de “hardcodear” usuario&contraseña aquí, los leemos desde el .env.
# Por ejemplo, en tu .env debes tener:
#   CRED_USER1=joaquin.ballesteros@konecta.com
#   CRED_PWD1=Konecta+478
#   CRED_USER2=enrique.juarez@konecta.com
#   CRED_PWD2=Limon2026+-
#   CRED_USER3=maria.gomez@konecta.com
#   CRED_PWD3=Passwd123
#
# De esta forma, nunca aparacen en el repo ni en el código.
# ——————————————————————————————————————————————————————————————
default_credentials = {
    os.getenv("CRED_USER1"): os.getenv("CRED_PWD1"),
    os.getenv("CRED_USER2"): os.getenv("CRED_PWD2"),
    os.getenv("CRED_USER3"): os.getenv("CRED_PWD3"),
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

        # Validar credenciales contra el diccionario leído de entorno
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
    # Agregamos "all" (si lo necesitamos) o podemos omitirlo según tu lógica:
    # opciones.append(("all", "Todos los servicios"))

    # Luego agregamos (clave, SERVICE_LABELS[clave]) para cada servicio individual
    for key in SERVICES.keys():
        opciones.append((key, SERVICE_LABELS.get(key, key.capitalize())))

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
    #Ejemplo: si servicio == "sop_conectividad", se asume que existe blueprint sop_conectividad.programacion
    programacion_url = url_for(f"{provider}.programacion")
    conversor_url     = url_for("conversor.conversor")
    curvas_url        = url_for("curvas.index")

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
