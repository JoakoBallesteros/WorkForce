import os
from flask import Blueprint, render_template

# Calculamos la ruta al directorio raíz del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

curvas_bp = Blueprint(
    'curvas',
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static', 'curvas'),
    url_prefix='/graficador'
)

@curvas_bp.route('/')
def index():
    # Ahora renderizamos directamente curvas.html
    return render_template('curvas.html', title='Graficador')