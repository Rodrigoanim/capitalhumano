# transcribe_audio.py
# Data: 09/03/2025 - 15:00
# Descrição: Este script permite transcrever arquivos de áudio MP3 para texto usando a API da AssemblyAI.

import requests
import time
import os
import streamlit as st
import sqlite3

# Chave de API fornecida
API_KEY = "e2d40b7f8dbf43b1b0716d38aa86ff81"

# Definir diretório de trabalho
WORK_DIR = "z:/youtube"
# Caminho do banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "you_ana.db")

# Diretório para salvar a transcrição
OUTPUT_DIR = os.path.join(WORK_DIR, 'transcricoes')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# URL base da API da AssemblyAI
UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"

# Headers para autenticação
HEADERS = {
    "authorization": API_KEY,
}

# Upload do arquivo de áudio
def upload_file(file_path):
    with open(file_path, "rb") as f:
        print("Fazendo upload do arquivo...")
        response = requests.post(UPLOAD_URL, headers=HEADERS, files={"file": f})
        if response.status_code == 200:
            print("Upload concluído!")
            return response.json()["upload_url"]
        else:
            print("Erro no upload:", response.json())
            return None

# Solicitar transcrição
def request_transcription(audio_url):
    payload = {
        "audio_url": audio_url,
        "language_code": "pt",      # Português
        "punctuate": True,          # Pontuação automática
        "format_text": True,        # Formatação do texto
        "speaker_labels": True,     # Ativa identificação de falantes
        "speakers_expected": 2      # Indica que esperamos 2 falantes
    }
    print("Solicitando transcrição...")
    response = requests.post(TRANSCRIPT_URL, json=payload, headers=HEADERS)
    if response.status_code == 200:
        return response.json()["id"]
    else:
        print("Erro ao solicitar transcrição:", response.json())
        return None

# Aguardar a conclusão da transcrição
def wait_for_transcription(transcript_id):
    while True:
        response = requests.get(f"{TRANSCRIPT_URL}/{transcript_id}", headers=HEADERS)
        if response.status_code == 200:
            status = response.json()["status"]
            if status == "completed":
                return response.json()
            elif status == "failed":
                print("Erro na transcrição:", response.json()["error"])
                return None
            else:
                print("Transcrição em andamento, aguardando...")
                time.sleep(5)
        else:
            print("Erro ao verificar status:", response.json())
            return None

# Salvar transcrição em um arquivo .txt
def save_transcription(text, filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Transcrição salva em: {file_path}")
    return file_path

def list_mp3_files():
    """Lista todos os arquivos MP3 no diretório atual"""
    mp3_files = [f for f in os.listdir(WORK_DIR) if f.endswith('.mp3')]
    if not mp3_files:
        print("Nenhum arquivo MP3 encontrado no diretório.")
        return []
    
    print("\nArquivos MP3 disponíveis:")
    for i, file in enumerate(mp3_files, 1):
        print(f"{i}. {file}")
    
    return mp3_files

def get_user_id():
    """Obtém o ID do usuário logado da sessão"""
    if 'user_id' in st.session_state:
        return st.session_state.user_id
    else:
        st.error("Usuário não autenticado. Por favor, faça login primeiro.")
        return None

def get_videos_to_transcribe(user_id):
    """Obtém vídeos que precisam ser transcritos (word_key = 'mp4_mp3_frames')"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar vídeos com word_key = 'mp4_mp3_frames' para o usuário específico
        cursor.execute(
            "SELECT you_id, titulo, url, autor, sumario FROM youtube_tab WHERE user_id = ? AND word_key = 'mp4_mp3_frames'",
            (user_id,)
        )
        videos = cursor.fetchall()
        conn.close()
        
        return videos
    except Exception as e:
        st.error(f"Erro ao buscar vídeos para transcrição: {str(e)}")
        return []

def mark_as_transcribed(video_id):
    """Marca o vídeo como transcrito no banco de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Atualiza a coluna word_key para o vídeo específico
        cursor.execute(
            "UPDATE youtube_tab SET word_key = 'transcrito' WHERE you_id = ?", 
            (video_id,)
        )
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Erro ao marcar vídeo como transcrito: {str(e)}")
        return False

def process_audio_transcription(video_id, video_title):
    """Processa a transcrição de um arquivo de áudio"""
    st.subheader(f"Transcrevendo: {video_title}")
    
    # Criar placeholders para status e progresso
    status = st.empty()
    progress = st.progress(0)
    
    # Verificar se o arquivo MP3 existe
    mp3_filename = f"{video_title}.mp3"
    mp3_path = os.path.join(WORK_DIR, mp3_filename)
    
    if not os.path.exists(mp3_path):
        st.error(f"Arquivo MP3 não encontrado: {mp3_filename}")
        return False
    
    # 1. Upload do arquivo
    status.text("Fazendo upload do arquivo...")
    progress.progress(0.1)
    audio_url = upload_file(mp3_path)
    
    if not audio_url:
        st.error("Falha no upload do arquivo de áudio.")
        return False
    
    # 2. Solicitar transcrição
    status.text("Solicitando transcrição...")
    progress.progress(0.3)
    transcript_id = request_transcription(audio_url)
    
    if not transcript_id:
        st.error("Falha ao solicitar transcrição.")
        return False
    
    # 3. Aguardar resultado
    status.text("Transcrição em andamento, aguardando...")
    
    # Iniciar com 40% de progresso e ir aumentando gradualmente
    progress_value = 0.4
    while True:
        response = requests.get(f"{TRANSCRIPT_URL}/{transcript_id}", headers=HEADERS)
        if response.status_code == 200:
            status_resp = response.json()["status"]
            if status_resp == "completed":
                result = response.json()
                break
            elif status_resp == "failed":
                st.error("Erro na transcrição: " + response.json()["error"])
                return False
            else:
                status.text(f"Transcrição em andamento, aguardando... ({status_resp})")
                # Aumentar progresso gradualmente até 90%
                progress_value = min(0.9, progress_value + 0.05)
                progress.progress(progress_value)
                time.sleep(5)
        else:
            st.error("Erro ao verificar status: " + str(response.status_code))
            return False
    
    # 4. Salvar transcrição
    status.text("Salvando transcrição...")
    progress.progress(0.95)
    
    output_filename = f"{video_title}.txt"
    saved_path = save_transcription(result["text"], output_filename)
    
    # 5. Marcar como transcrito
    if mark_as_transcribed(video_id):
        status.text("Transcrição concluída com sucesso!")
        progress.progress(1.0)
        
        # Mostrar resultado
        st.success(f"Transcrição concluída e salva em: {saved_path}")
        st.text_area("Texto transcrito:", result["text"], height=300)
        return True
    else:
        st.warning("Transcrição concluída, mas houve erro ao atualizar o banco de dados.")
        return False

def show_transcribe_audio():
    """Interface principal do programa de transcrição"""
    st.title("Transcrição de Áudio")
    
    # Verificar se o usuário está logado
    user_id = get_user_id()
    if not user_id:
        st.warning("Você precisa estar logado para usar esta funcionalidade.")
        return
    
    # Verificar se o diretório de trabalho existe
    if not os.path.exists(WORK_DIR):
        st.error(f"Diretório {WORK_DIR} não encontrado!")
        return
    
    # Escolher modo de operação
    st.subheader("Escolha o modo de operação:")
    mode = st.radio("Modo", ["Manual", "Automático"])
    
    if mode == "Manual":
        st.subheader("Modo Manual")
        
        # Buscar vídeos do usuário que precisam ser transcritos
        videos = get_videos_to_transcribe(user_id)
        
        if not videos:
            st.info("Nenhum vídeo encontrado para transcrição.")
            return
        
        # Criar opções para o selectbox
        video_options = [f"{v[1]} - {v[3]}" for v in videos]  # titulo - autor
        selected_index = st.selectbox("Selecione um áudio para transcrever:", 
                                     range(len(video_options)), 
                                     format_func=lambda i: video_options[i])
        
        selected_video = videos[selected_index]
        video_id, video_title, video_url, video_author, video_summary = selected_video
        
        # Mostrar detalhes do vídeo selecionado
        st.write(f"**Título:** {video_title}")
        st.write(f"**Autor:** {video_author}")
        st.write(f"**Resumo:** {video_summary}")
        
        # Botão para iniciar transcrição
        if st.button("Transcrever Áudio"):
            process_audio_transcription(video_id, video_title)
    
    else:  # Modo Automático
        st.subheader("Modo Automático")
        
        # Buscar vídeos para transcrição
        videos_to_transcribe = get_videos_to_transcribe(user_id)
        
        if not videos_to_transcribe:
            st.info("Não há vídeos pendentes para transcrição.")
            return
        
        st.info(f"Encontrados {len(videos_to_transcribe)} áudios pendentes para transcrição.")
        
        # Listar vídeos pendentes
        for i, (vid, title, url, author, summary) in enumerate(videos_to_transcribe):
            st.write(f"{i+1}. **{title}** - {author}")
        
        # Confirmar processamento automático
        if st.button("Transcrever Todos os Áudios Pendentes"):
            st.warning("Iniciando transcrição automática. Isso pode levar algum tempo.")
            
            success_count = 0
            for video in videos_to_transcribe:
                video_id, video_title, video_url, _, _ = video
                
                # Processar cada áudio
                if process_audio_transcription(video_id, video_title):
                    success_count += 1
                
                # Pequena pausa entre processamentos
                time.sleep(1)
            
            st.success(f"Processamento concluído! {success_count} de {len(videos_to_transcribe)} áudios transcritos com sucesso.")

# Fluxo principal
if __name__ == "__main__":
    # Listar arquivos MP3 e permitir escolha
    selected_file = list_mp3_files()
    if selected_file:
        file_path = os.path.join(os.getcwd(), selected_file)
        
        # Extrair nome do arquivo para usar na saída
        output_filename = os.path.splitext(selected_file)[0] + "_transcricao.txt"
        
        print(f"\nArquivo selecionado: {selected_file}")

        # Fazer upload do arquivo
        audio_url = upload_file(file_path)

        # Solicitar transcrição
        transcript_id = request_transcription(audio_url)

        # Aguardar resultado
        result = wait_for_transcription(transcript_id)

        # Exibir resultado
        print("\nTranscrição completa:")
        print(result["text"])

        # Salvar transcrição em um arquivo
        save_transcription(result["text"], output_filename)
