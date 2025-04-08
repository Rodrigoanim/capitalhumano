# transcribe_audio.py
# Data: 27/03/2025 - 12:00
# Descrição: Este script permite transcrever arquivos de áudio MP3 para texto usando a API da AssemblyAI.
# formato vtt com legendas - Ok

import requests
import time
import os
import streamlit as st
import sqlite3
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Chave de API fornecida
API_KEY = os.getenv('ASSEMBLYAI_API_KEY')

if not API_KEY:
    st.error("Chave da API AssemblyAI não encontrada. Verifique o arquivo .env")
    raise ValueError("ASSEMBLYAI_API_KEY não está definida no arquivo .env")

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

# Salvar transcrição em formatos txt e vtt
def save_transcription(result, filename):
    base_filename = os.path.splitext(filename)[0]
    
    # Salvar em formato TXT
    txt_path = os.path.join(OUTPUT_DIR, f"{base_filename}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    
    # Salvar em formato VTT
    vtt_path = os.path.join(OUTPUT_DIR, f"{base_filename}.vtt")
    with open(vtt_path, "w", encoding="utf-8") as f:
        # Cabeçalho WebVTT
        f.write("WEBVTT\n\n")
        
        # Processar cada palavra com timestamp
        words = result.get("words", [])
        current_line = []
        current_start = None
        current_char_count = 0
        
        # Configurações para legendas
        MAX_CHARS_PER_LINE = 42    # Máximo de caracteres por linha
        MAX_DURATION = 5000        # Duração máxima em ms (5 segundos)
        MIN_DURATION = 1000        # Duração mínima em ms (1 segundo)
        PONTUACAO = '.!?'          # Pontuação forte para quebra de frases
        PONTUACAO_FRACA = ',;:'    # Pontuação que sugere quebra se necessário
        
        for i, word in enumerate(words):
            if current_start is None:
                current_start = word["start"]
            
            word_text = word["text"]
            word_len = len(word_text)
            current_duration = word["end"] - current_start
            
            # Verificar condições para quebra de linha
            is_last_word = i == len(words) - 1
            has_strong_punct = any(p in word_text for p in PONTUACAO)
            has_weak_punct = any(p in word_text for p in PONTUACAO_FRACA)
            would_exceed_chars = current_char_count + word_len + 1 > MAX_CHARS_PER_LINE
            would_exceed_duration = current_duration > MAX_DURATION
            
            # Decidir se quebra a linha
            should_break = (
                is_last_word or
                would_exceed_chars or
                would_exceed_duration or
                (has_strong_punct and current_duration > MIN_DURATION) or
                (has_weak_punct and would_exceed_chars)
            )
            
            # Adicionar palavra à linha atual
            current_line.append(word_text)
            current_char_count += word_len + 1  # +1 para o espaço
            
            # Processar quebra de linha se necessário
            if should_break and current_line:
                # Determinar tempo final
                end_time = word["end"]
                
                # Ajustar duração mínima se necessário
                if end_time - current_start < MIN_DURATION:
                    end_time = current_start + MIN_DURATION
                
                # Converter timestamps
                start = format_timestamp(current_start)
                end = format_timestamp(end_time)
                
                # Escrever entrada VTT
                f.write(f"{start} --> {end}\n")
                f.write(" ".join(current_line) + "\n\n")
                
                # Resetar para próxima linha
                current_line = []
                current_char_count = 0
                current_start = None  # Será definido na próxima iteração
    
    print(f"Transcrições salvas em:\nTXT: {txt_path}\nVTT: {vtt_path}")
    return txt_path, vtt_path

def format_timestamp(ms):
    """Converte milissegundos para formato VTT (HH:MM:SS.mmm)"""
    seconds = int(ms / 1000)
    milliseconds = int(ms % 1000)
    minutes = int(seconds / 60)
    hours = int(minutes / 60)
    
    return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}.{milliseconds:03d}"

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
    
    output_filename = f"{video_title}"
    txt_path, vtt_path = save_transcription(result, output_filename)
    
    # 5. Marcar como transcrito (apenas se video_id não for None)
    if video_id:
        if mark_as_transcribed(video_id):
            status.text("Transcrição concluída com sucesso!")
            progress.progress(1.0)
    else:
        status.text("Transcrição concluída com sucesso!")
        progress.progress(1.0)
    
    # Criar abas para mostrar os diferentes formatos
    txt_tab, vtt_tab = st.tabs(["Texto", "VTT"])
    
    with txt_tab:
        st.text_area("Texto transcrito:", result["text"], height=300)
    
    with vtt_tab:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        st.text_area("Formato VTT:", vtt_content, height=300)
    
    return True

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
        
        # Listar arquivos MP3 do diretório
        mp3_files = [f for f in os.listdir(WORK_DIR) if f.endswith('.mp3')]
        
        if not mp3_files:
            st.info("Nenhum arquivo MP3 encontrado no diretório de trabalho.")
            return
        
        # Criar selectbox com os arquivos MP3
        selected_mp3 = st.selectbox(
            "Selecione um arquivo MP3 para transcrever:",
            mp3_files,
            format_func=lambda x: x.replace('.mp3', '')
        )
        
        if selected_mp3:
            # Extrair título do vídeo (removendo extensão .mp3)
            video_title = selected_mp3.replace('.mp3', '')
            
            # Mostrar nome do arquivo selecionado
            st.write(f"**Arquivo selecionado:** {selected_mp3}")
            
            # Botão para iniciar transcrição
            if st.button("Transcrever Áudio"):
                # Processar transcrição sem interação com o banco de dados
                process_audio_transcription(None, video_title)

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
        save_transcription(result, output_filename)
