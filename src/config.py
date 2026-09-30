# -*- coding: utf-8 -*-
"""
config.py — Configurações globais do projeto Auto-Atas-DOWeb (V1.0)
"""

from pathlib import Path


#
# CAMINHOS DO PROJETO
#
BASE_DIR         = Path(__file__).resolve().parent.parent
OUTPUT_DIR       = BASE_DIR / "output"
CREDENTIALS_FILE = BASE_DIR / "credentials.json"


#
# CATEGORIAS DE BUSCA
#

CATEGORIAS_BUSCA = [
    "INSUMO",
    "MEDICAMENTO",
    "MANDADO JUDICIAL",
    "SERVIÇO",
    "MATERIAL PERMANENTE"
]