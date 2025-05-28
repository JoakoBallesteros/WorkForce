
from .personal_service import PersonalService
from .sancristobal_service import SanCristobalService
from .lacaja_service import LacajaService
from .modo_service import ModoService
from .sancor_service import SancorService
from .andreani_service import AndreaniService


# Mapeo de servicios: las claves deben coincidir con los valores que uses en el selector
SERVICES = {
    'personal':       PersonalService(),
    'sancristobal':   SanCristobalService(),
    'lacaja':         LacajaService(),
    'modo':           ModoService(),
    'sancor':         SancorService(),
    'andreani':       AndreaniService(),
    
    
}

SERVICE_LABELS = {
    'personal':      'Personal',
    'sancristobal':  'San Cristóbal',
    'lacaja':        'La Caja',
    'sancor':        'Sancor',
    'andreani':      'Andreani',
    'modo':          'Modo',
}