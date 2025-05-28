import os
import pandas as pd

class LacajaService:

    SHEET_MAP = {
        'la caja': 'La Caja'
    }
    def procesar(self, nomina_path, req_file, servicio):
        base = os.path.dirname(__file__)
        out_path = os.path.join(base, f"{servicio}_reporte.xlsx")
        # ... tu lógica aquí ...
        return out_path