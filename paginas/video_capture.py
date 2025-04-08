# video_capture.py
# Data: 02/03/2025 - 17:00
# Descrição: Este script permite ao usuário baixar um vídeo MP4, extrair o áudio e as imagens (frames) de um vídeo do YouTube.

import streamlit as st
import os
import cv2
import yt_dlp
import subprocess
import re
import sqlite3
import time
from datetime import datetime

# Diretório fixo para downloads
YOUTUBE_DIR = r"Z:\youtube"
# Caminho do banco de dados - Corrigindo o caminho
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "you_ana.db")

def ensure_dir(directory):
    """Garante que o diretório existe"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def sanitize_filename(filename):
    """Remove caracteres inválidos do nome do arquivo"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

def extract_audio_ffmpeg(input_path, output_path, status_placeholder, progress_bar):
    """Extrai áudio usando FFmpeg com mais feedback"""
    try:
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
        
        # Comando simplificado para extração
        command = [
            ffmpeg_path,
            '-i', input_path,
            '-vn',           # Sem vídeo
            '-acodec', 'libmp3lame',  # Usar codec MP3
            '-q:a', '2',     # Qualidade alta (0-9, menor = melhor)
            '-y',            # Sobrescrever arquivo se existir
            output_path
        ]
        
        status_placeholder.text("Iniciando extração do áudio...")
        progress_bar.progress(0)
        
        # Executar FFmpeg
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Aguardar com timeout
        try:
            stdout, stderr = process.communicate(timeout=300)  # 5 minutos de timeout
            
            if process.returncode == 0:
                if os.path.exists(output_path):
                    status_placeholder.text("Extração concluída!")
                    progress_bar.progress(1.0)
                    return True
                else:
                    st.error("Arquivo de saída não foi criado")
                    return False
            else:
                st.error(f"Erro FFmpeg: {stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            process.kill()
            st.error("Tempo limite excedido na extração do áudio")
            return False
            
    except Exception as e:
        st.error(f"Erro ao extrair áudio: {str(e)}")
        return False

def extract_frames(video_path, output_dir, status_placeholder, progress_bar, frames_per_minute=2):
    """Extrai frames do vídeo na frequência especificada"""
    try:
        ensure_dir(output_dir)
        
        # Abrir o vídeo
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            st.error("Não foi possível abrir o vídeo")
            return False
            
        # Obter informações do vídeo
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_secs = total_frames / fps if fps > 0 else 0
        
        # Calcular intervalo entre frames
        frames_to_extract = int(duration_secs / 60 * frames_per_minute)
        interval = total_frames / frames_to_extract if frames_to_extract > 0 else 0
        
        status_placeholder.text(f"Extraindo {frames_to_extract} frames do vídeo...")
        
        count = 0
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Salvar frame no intervalo especificado
            if count % max(1, int(interval)) == 0:
                frame_filename = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
                cv2.imwrite(frame_filename, frame)
                saved_count += 1
                
                # Atualizar progresso
                progress = min(1.0, frame_count / total_frames)
                progress_bar.progress(progress)
                
            count += 1
            frame_count += 1
            
        cap.release()
        status_placeholder.text(f"Extração concluída! {saved_count} frames extraídos.")
        progress_bar.progress(1.0)
        return True
        
    except Exception as e:
        st.error(f"Erro ao extrair frames: {str(e)}")
        return False

def get_video_path(video_title):
    """Retorna o caminho do vídeo MP4 se existir"""
    sanitized_title = sanitize_filename(video_title)
    return os.path.join(YOUTUBE_DIR, f"{sanitized_title}.mp4")

def download_video(url, video_title, status_placeholder, progress_bar):
    """Download do vídeo em MP4"""
    try:
        ensure_dir(YOUTUBE_DIR)
        sanitized_title = sanitize_filename(video_title)
        output_template = os.path.join(YOUTUBE_DIR, f"{sanitized_title}.mp4")
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%')
                p = p.replace('%', '')
                try:
                    progress = float(p) / 100
                    progress_bar.progress(progress)
                    status_placeholder.text(f"Baixando: {p}% concluído")
                except:
                    pass
            elif d['status'] == 'finished':
                status_placeholder.text("Download concluído! Processando...")
                progress_bar.progress(1.0)
        
        ydl_opts = {
            'format': 'best[ext=mp4]',  # Melhor qualidade em MP4
            'outtmpl': output_template,
            'progress_hooks': [progress_hook],
            'restrictfilenames': True,
            'ffmpeg_location': r"C:\ffmpeg\bin",
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            status_placeholder.text("Iniciando download...")
            progress_bar.progress(0)
            ydl.extract_info(url, download=True)
            
            if os.path.exists(output_template):
                return output_template
            return None
            
    except Exception as e:
        st.error(f"Erro no download: {str(e)}")
        return None

def select_mp4_file():
    """Permite ao usuário selecionar um arquivo MP4"""
    st.info("Selecione um arquivo MP4:")
    uploaded_file = st.file_uploader("Escolha um arquivo MP4", type=['mp4'])
    if uploaded_file is not None:
        # Salvar o arquivo temporariamente
        temp_path = os.path.join(YOUTUBE_DIR, "temp_upload.mp4")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        return temp_path
    return None

def get_user_id():
    """Obtém o ID do usuário logado da sessão"""
    if 'user_id' in st.session_state:
        return st.session_state.user_id
    else:
        st.error("Usuário não autenticado. Por favor, faça login primeiro.")
        return None

def get_pending_videos(user_id):
    """Obtém vídeos pendentes de processamento para o usuário"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar vídeos com word_key vazia para o usuário específico
        cursor.execute(
            "SELECT you_id, titulo, url, autor, sumario FROM youtube_tab WHERE user_id = ? AND (word_key IS NULL OR word_key = '')",
            (user_id,)
        )
        videos = cursor.fetchall()
        conn.close()
        
        return videos
    except Exception as e:
        st.error(f"Erro ao buscar vídeos pendentes: {str(e)}")
        return []

def get_all_videos(user_id):
    """Obtém todos os vídeos do usuário para seleção manual"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar todos os vídeos do usuário
        cursor.execute(
            "SELECT you_id, titulo, url, autor, sumario FROM youtube_tab WHERE user_id = ?",
            (user_id,)
        )
        videos = cursor.fetchall()
        conn.close()
        
        return videos
    except Exception as e:
        st.error(f"Erro ao buscar vídeos: {str(e)}")
        return []

def mark_as_processed(video_id):
    """Marca o vídeo como processado no banco de dados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Atualiza a coluna word_key para o vídeo específico
        cursor.execute(
            "UPDATE youtube_tab SET word_key = 'mp4_mp3_frames' WHERE you_id = ?", 
            (video_id,)
        )
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Erro ao marcar vídeo como processado: {str(e)}")
        return False

def process_video(video_id, video_title, video_url):
    """Processa um vídeo: download, extração de áudio e frames"""
    st.subheader(f"Processando: {video_title}")
    
    # Criar placeholders para status e progresso
    status = st.empty()
    progress = st.progress(0)
    
    # 1. Download do vídeo
    status.text("Iniciando download do vídeo...")
    video_path = download_video(video_url, video_title, status, progress)
    
    if not video_path:
        st.error("Falha no download do vídeo.")
        return False
    
    # 2. Extrair áudio MP3
    status.text("Preparando para extrair áudio...")
    progress.progress(0)
    
    mp3_path = os.path.join(YOUTUBE_DIR, f"{sanitize_filename(video_title)}.mp3")
    audio_success = extract_audio_ffmpeg(video_path, mp3_path, status, progress)
    
    if not audio_success:
        st.error("Falha na extração do áudio.")
        return False
    
    # 3. Extrair frames
    status.text("Preparando para extrair frames...")
    progress.progress(0)
    
    frames_dir = os.path.join(YOUTUBE_DIR, f"{sanitize_filename(video_title)}_frames")
    frames_success = extract_frames(video_path, frames_dir, status, progress, frames_per_minute=2)
    
    if not frames_success:
        st.error("Falha na extração dos frames.")
        return False
    
    # 4. Marcar como processado
    if mark_as_processed(video_id):
        status.text("Vídeo processado com sucesso!")
        st.success(f"Vídeo '{video_title}' processado com sucesso!")
        return True
    else:
        st.warning("Vídeo processado, mas houve erro ao atualizar o banco de dados.")
        return False

def show_video_capture():
    """Interface principal do programa"""
    st.title("Processador de Vídeos do YouTube")
    
    # Verificar se o usuário está logado
    user_id = get_user_id()
    if not user_id:
        st.warning("Você precisa estar logado para usar esta funcionalidade.")
        return
    
    # Escolher modo de operação
    st.subheader("Escolha o modo de operação:")
    mode = st.radio("Modo", ["Manual", "Automático"])
    
    if mode == "Manual":
        st.subheader("Modo Manual")
        
        # Buscar vídeos do usuário
        videos = get_all_videos(user_id)
        
        if not videos:
            st.info("Nenhum vídeo encontrado para este usuário.")
            return
        
        # Criar opções para o selectbox
        video_options = [f"{v[1]} - {v[3]}" for v in videos]  # titulo - autor
        selected_index = st.selectbox("Selecione um vídeo para processar:", 
                                     range(len(video_options)), 
                                     format_func=lambda i: video_options[i])
        
        selected_video = videos[selected_index]
        video_id, video_title, video_url, video_author, video_summary = selected_video
        
        # Mostrar detalhes do vídeo selecionado
        st.write(f"**Título:** {video_title}")
        st.write(f"**Autor:** {video_author}")
        st.write(f"**Resumo:** {video_summary}")
        
        # Botão para iniciar processamento
        if st.button("Processar Vídeo"):
            process_video(video_id, video_title, video_url)
    
    else:  # Modo Automático
        st.subheader("Modo Automático")
        
        # Buscar vídeos pendentes
        pending_videos = get_pending_videos(user_id)
        
        if not pending_videos:
            st.info("Não há vídeos pendentes para processamento.")
            return
        
        st.info(f"Encontrados {len(pending_videos)} vídeos pendentes para processamento.")
        
        # Listar vídeos pendentes
        for i, (vid, title, url, author, summary) in enumerate(pending_videos):
            st.write(f"{i+1}. **{title}** - {author}")
        
        # Confirmar processamento automático
        if st.button("Processar Todos os Vídeos Pendentes"):
            st.warning("Iniciando processamento automático. Isso pode levar algum tempo.")
            
            success_count = 0
            for video in pending_videos:
                video_id, video_title, video_url, _, _ = video
                
                # Processar cada vídeo
                if process_video(video_id, video_title, video_url):
                    success_count += 1
                
                # Pequena pausa entre processamentos
                time.sleep(1)
            
            st.success(f"Processamento concluído! {success_count} de {len(pending_videos)} vídeos processados com sucesso.")

if __name__ == "__main__":
    show_video_capture()
