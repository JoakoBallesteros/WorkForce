import os
import pandas as pd

class AndreaniService:

    SHEET_MAP = {
        'andreani': 'Andreani'
    }
    def procesar(self, nomina_path, req_file, servicio):
        base = os.path.dirname(__file__)
        out_path = os.path.join(base, f"{servicio}_reporte.xlsx")
        # ... tu lógica aquí ...
        return out_path