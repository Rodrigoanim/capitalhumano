import webbrowser
import os
import time

# Caminho do Chrome
chrome_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'

# Configurações das janelas
windows = [
    {
        "urls": ["https://www.youtube.com"],
        "size": "--window-size=800,600",    # Tamanho pequeno
        "position": "--window-position=0,0"
    },
    {
        "urls": [
            "https://calendar.google.com",
            "https://contacts.google.com"
        ],
        "size": "--window-size=1024,768",   # Tamanho médio
        "position": "--window-position=820,0"
    },
    {
        "urls": [
            "https://www.cursor.com",
            "https://chatgpt.com"
        ],
        "size": "--window-size=1280,920",   # Tamanho grande
        "position": "--window-position=200,200"
    }
]

# Abre cada janela com suas configurações
for window in windows:
    # Cria o comando com as configurações da janela
    urls = ' '.join(window['urls'])
    command = f'start "" "{chrome_path}" --new-window {window["size"]} {window["position"]} {urls}'
    
    # Executa o comando
    os.system(command)
    
    # Espera 2 segundos entre cada janela
    time.sleep(2)

print("Todas as janelas foram abertas!")
