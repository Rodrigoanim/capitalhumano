# url_metadados.py
# Este script é responsável por coletar metadados de vídeos do YouTube e armazená-los em um banco de dados SQLite.
# Versão 1.0.2 - 04/03/2025 - 09h00

import sqlite3
import re
from urllib.parse import urlparse, parse_qs
import tkinter as tk
from tkinter import ttk, messagebox
from pytube import YouTube
import pandas as pd
import streamlit as st
from pathlib import Path
import time
from urllib.request import urlopen
import json
import requests
from bs4 import BeautifulSoup

class YouTubeMetadados:
    def __init__(self, user_id):
        """Inicializa a conexão com o banco de dados correto"""
        try:
            # Verifica se o banco existe
            db_path = Path('data/you_ana.db').resolve()
            if not db_path.exists():
                st.error("Banco de dados não encontrado em: data/you_ana.db")
                raise FileNotFoundError("Banco de dados não encontrado")
                
            self.conn = sqlite3.connect(db_path)
            self.cursor = self.conn.cursor()
            self.user_id = user_id
            
            # Verifica se a tabela existe
            self.cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='youtube_tab'
            """)
            if self.cursor.fetchone()[0] == 0:
                st.error("Tabela 'youtube_tab' não encontrada no banco de dados")
                raise ValueError("Tabela não encontrada")
            
        except Exception as e:
            st.error(f"Erro ao conectar ao banco de dados: {str(e)}")
            raise

    def validar_url_youtube(self, url):
        """Valida se a URL é do YouTube"""
        try:
            # Padrões de URL do YouTube mais comuns
            patterns = [
                r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
                r'^https?://(?:www\.)?youtube\.com/v/[\w-]+',
                r'^https?://youtu\.be/[\w-]+',
                r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',
                r'^https?://(?:www\.)?youtube\.com/shorts/[\w-]+'
            ]
            
            # Verifica se a URL corresponde a algum dos padrões
            is_valid = any(re.match(pattern, url.strip()) for pattern in patterns)
            
            if is_valid:
                st.write("URL válida:", url)
                return True
            
            st.write("URL não corresponde aos padrões:", url)
            return False
            
        except Exception as e:
            st.error(f"Erro ao validar URL: {str(e)}")
            return False
    
    def coletar_metadados(self, url):
        """Coleta título, autor, descrição e duração do vídeo usando requests e BeautifulSoup"""
        try:
            # Faz a requisição HTTP
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse do HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tenta encontrar o título
            titulo = None
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                titulo = meta_title['content']
            else:
                titulo = soup.find('title').text.replace(' - YouTube', '')
            
            # Tenta encontrar a descrição
            descricao = None
            meta_desc = soup.find('meta', {'itemprop': 'description'})
            if meta_desc:
                descricao = meta_desc.get('content')
            
            # Tenta encontrar o autor
            autor = None
            meta_author = soup.find('span', {'itemprop': 'author'})
            if meta_author:
                author_name = meta_author.find('link', {'itemprop': 'name'})
                if author_name:
                    autor = author_name.get('content')
            
            if not autor:
                author_link = soup.find('link', {'itemprop': 'name'})
                if author_link:
                    autor = author_link.get('content')
            
            if not autor:
                autor = 'Autor não disponível'
            
            # Tenta encontrar a duração do vídeo
            duracao_minutos = None
            meta_duration = soup.find('meta', {'itemprop': 'duration'})
            if meta_duration:
                # Formato esperado: PT#M#S ou PT#H#M#S
                duration_str = meta_duration.get('content', '')
                if duration_str:
                    # Converte ISO 8601 para minutos
                    hours = re.search(r'(\d+)H', duration_str)
                    minutes = re.search(r'(\d+)M', duration_str)
                    seconds = re.search(r'(\d+)S', duration_str)
                    
                    total_minutes = 0
                    if hours:
                        total_minutes += int(hours.group(1)) * 60
                    if minutes:
                        total_minutes += int(minutes.group(1))
                    if seconds:
                        total_minutes += int(seconds.group(1)) / 60
                    
                    duracao_minutos = round(total_minutes, 2)
            
            metadados = {
                'titulo': titulo if titulo else 'Título não disponível',
                'autor': autor,
                'url': url,
                'sumario': descricao if descricao else '',
                'duration': duracao_minutos
            }
            
            return metadados
            
        except Exception as e:
            st.error(f"Erro ao coletar metadados: {str(e)}")
            return None

    def adicionar_video(self, url, user_id):
        """Adiciona novo vídeo ao banco de dados"""
        if not self.validar_url_youtube(url):
            raise ValueError("URL inválida. Por favor, insira uma URL do YouTube válida.")
        
        # Verifica se o vídeo já existe
        self.cursor.execute("SELECT you_id FROM youtube_tab WHERE url = ? AND user_id = ?", (url, user_id))
        if self.cursor.fetchone():
            raise ValueError("Este vídeo já está registrado no banco de dados.")
        
        try:
            metadados = self.coletar_metadados(url)
            if not metadados:
                raise ValueError("Não foi possível coletar os metadados do vídeo.")
            
            # Filtrar caracteres proibidos em nomes de arquivo do título
            titulo_filtrado = self.filtrar_caracteres_proibidos(metadados['titulo'])
            
            # Insere com o campo duration
            self.cursor.execute('''
                INSERT INTO youtube_tab (
                    titulo, url, autor, user_id, 
                    sumario, insights, contraintuitivo, word_key, tools, duration
                ) VALUES (?, ?, ?, ?, ?, '', '', '', '', ?)
            ''', (
                titulo_filtrado,
                url,
                metadados['autor'],
                user_id,
                metadados['sumario'],
                metadados['duration']
            ))
            
            self.conn.commit()
            return metadados
            
        except Exception as e:
            st.error(f"Erro ao adicionar vídeo: {str(e)}")
            raise
            
    def filtrar_caracteres_proibidos(self, texto):
        """Remove caracteres proibidos em nomes de arquivo e emojis"""
        if not texto:
            return ""
            
        # Substituir caracteres proibidos: < > \ / * ? | " :
        caracteres_proibidos = r'[<>\\/*?|":"]'
        texto_filtrado = re.sub(caracteres_proibidos, '_', texto)
        
        # Filtrar emojis - usando uma abordagem que remove caracteres não-ASCII e não-imprimíveis
        # Isso captura a maioria dos emojis que são caracteres Unicode fora do intervalo ASCII
        texto_filtrado = ''.join(c if c.isascii() and c.isprintable() else '_' for c in texto_filtrado)
        
        return texto_filtrado

def show_url_metadados():
    # Verificar se usuário está logado
    if "user_id" not in st.session_state:
        st.error("Usuário não autenticado!")
        return

    # Obter user_id da sessão
    user_id = st.session_state["user_id"]
    
    # Verifica e conecta ao banco de dados
    db_path = Path('data/you_ana.db').resolve()
    if not db_path.exists():
        st.error("Banco de dados não encontrado em: data/you_ana.db")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verifica se a tabela existe
    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master 
        WHERE type='table' AND name='youtube_tab'
    """)
    if cursor.fetchone()[0] == 0:
        st.error("Tabela 'youtube_tab' não encontrada no banco de dados")
        conn.close()
        return

    # Interface principal
    st.title("Gerenciador de Vídeos YouTube")
    
    # Adicionar novo vídeo
    with st.expander("Adicionar Novo Vídeo"):
        # Inicializar o estado se não existir
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False
            
        # Se o formulário foi submetido, limpar na próxima renderização
        if st.session_state.form_submitted:
            st.session_state.youtube_url = ""
            st.session_state.form_submitted = False
            
        nova_url = st.text_input("URL do Vídeo YouTube:", key='youtube_url')
        if st.button("Adicionar Vídeo"):
            try:
                yt_meta = YouTubeMetadados(user_id)
                metadados = yt_meta.adicionar_video(nova_url, user_id)
                if metadados:
                    st.success("Vídeo adicionado com sucesso!")
                    # Marcar para limpar na próxima renderização
                    st.session_state.form_submitted = True
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao adicionar vídeo: {str(e)}")

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        filtro_titulo = st.text_input("Filtrar por Título:")
    with col2:
        filtro_autor = st.text_input("Filtrar por Autor:")

    # Construir query com filtros
    query = """
        SELECT you_id, user_id, titulo, autor, url, sumario, duration
        FROM youtube_tab 
        WHERE user_id = ?
    """
    params = [user_id]

    if filtro_titulo:
        query += " AND titulo LIKE ?"
        params.append(f"%{filtro_titulo}%")
    if filtro_autor:
        query += " AND autor LIKE ?"
        params.append(f"%{filtro_autor}%")

    # Carregar dados
    df = pd.read_sql_query(query, conn, params=params)
    
    if not df.empty:
        # Ajustar a exibição das colunas e formatar duration
        df['duration'] = df['duration'].round(2)  # Arredonda para 2 casas decimais
        df_display = df[['titulo', 'autor', 'url', 'sumario', 'duration']]
        st.dataframe(df_display)
        
        # Seleção de vídeo
        selected_video = st.selectbox(
            "Selecione um vídeo:",
            df['titulo'].tolist()
        )
        
        if selected_video:
            video_data = df[df['titulo'] == selected_video].iloc[0]
            
            if st.button("Excluir Vídeo"):
                try:
                    cursor.execute("""
                        DELETE FROM youtube_tab 
                        WHERE you_id = ? AND user_id = ?
                    """, (int(video_data['you_id']), int(user_id)))
                    
                    conn.commit()
                    st.success("Vídeo excluído com sucesso!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao excluir vídeo: {str(e)}")
                    conn.rollback()
    else:
        st.info("Nenhum vídeo encontrado para os filtros aplicados.")

    # Fechar conexão
    conn.close()

