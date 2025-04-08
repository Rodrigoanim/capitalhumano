# Programa: config.py
# Data: 01/03/2025
# Hora: 11:00


import os
from pathlib import Path

# Verifica se está em ambiente de produção (Render.com)
IS_PRODUCTION = os.getenv('RENDER') == 'true'

# Define o caminho base dependendo do ambiente
if IS_PRODUCTION:
    # Verifica se /var/data existe e é gravável
    var_data = Path('/var/data')
    if var_data.exists() and os.access(var_data, os.W_OK):
        DATA_DIR = var_data
    else:
        DATA_DIR = Path('/tmp/data')
else:
    # Caminho local para desenvolvimento
    DATA_DIR = Path(__file__).parent / 'data'

# Cria o diretório de dados se não existir
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Definir o caminho do banco de dados
DB_PATH = DATA_DIR / 'you_ana.db'
