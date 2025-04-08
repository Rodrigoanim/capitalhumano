# url_metadados.py
# Este script é responsável por coletar metadados de vídeos do YouTube e armazená-los em um banco de dados SQLite.
# Versão 1.0.2 - 06/03/2025 - 18h00

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
        """Coleta título, autor, descrição, duração e idioma do vídeo usando requests e BeautifulSoup"""
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
            
            # Tenta encontrar o idioma do vídeo
            language = None
            meta_language = soup.find('meta', {'itemprop': 'inLanguage'})
            if meta_language:
                language = meta_language.get('content')
            
            if not language:
                # Tenta encontrar na tag html
                html_tag = soup.find('html')
                if html_tag and html_tag.get('lang'):
                    language = html_tag.get('lang').split('-')[0]  # Pega apenas a parte principal do código de idioma
            
            if not language:
                language = 'und'  # 'und' é usado para indefinido/desconhecido
            
            metadados = {
                'titulo': titulo if titulo else 'Título não disponível',
                'autor': autor,
                'url': url,
                'sumario': descricao if descricao else '',
                'duration': duracao_minutos,
                'language': language
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
                    sumario, insights, contraintuitivo, word_key, tools, duration, language
                ) VALUES (?, ?, ?, ?, ?, '', '', '', '', ?, ?)
            ''', (
                titulo_filtrado,
                url,
                metadados['autor'],
                user_id,
                metadados['sumario'],
                metadados['duration'],
                metadados['language']
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
    
    # Criar uma única conexão para toda a função
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verifica se a tabela existe
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name='youtube_tab'
        """)
        if cursor.fetchone()[0] == 0:
            st.error("Tabela 'youtube_tab' não encontrada no banco de dados")
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
            SELECT you_id, user_id, titulo, autor, url, sumario, duration, language, word_key
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

        # Debug da query inicial
        print(f"# Debug - Query inicial: {query}")
        print(f"# Debug - Parâmetros: {params}")

        # Carregar dados usando a mesma conexão
        df = pd.read_sql_query(query, conn, params=params)
        
        # Debug dos dados carregados
        print(f"# Debug - Total de registros carregados: {len(df)}")
        print(f"# Debug - Primeiros registros:")
        print(df[['you_id', 'user_id', 'language']].head())

        if not df.empty:
            # Ajustar a exibição das colunas e formatar duration
            df['duration'] = df['duration'].round(2)
            
            # Define as colunas a serem exibidas na tabela
            # Importante: incluir user_id para referência
            df_display = df[['titulo', 'autor', 'url', 'sumario', 'duration', 'language', 'word_key', 'you_id', 'user_id']]
            
            # Criar editor de dados com configurações de coluna
            edited_df = st.data_editor(
                # Remove as colunas you_id e user_id da visualização, mas mantém no DataFrame
                df_display[['titulo', 'autor', 'url', 'sumario', 'duration', 'language', 'word_key']],
                key="youtube_editor",
                column_config={
                    "titulo": st.column_config.TextColumn(
                        "Título do Vídeo",  # Cabeçalho personalizado
                        width="medium",
                        required=True
                    ),
                    "autor": st.column_config.TextColumn(
                        "Canal/Autor",  # Cabeçalho personalizado
                        width="medium",
                        required=True
                    ),
                    "url": st.column_config.LinkColumn(
                        "Link do Vídeo"  # Cabeçalho personalizado
                    ),
                    "sumario": st.column_config.TextColumn(
                        "Descrição",  # Cabeçalho personalizado
                        width="medium"
                    ),
                    "duration": st.column_config.NumberColumn(
                        "Duração (min)",
                        min_value=0,
                        format="%.2f"
                    ),
                    "language": st.column_config.SelectboxColumn(
                        "Idioma do Vídeo",  # Cabeçalho personalizado
                        options=["pt", "en", "es", "fr", "de", "und"],
                        default="und"
                    ),
                    "word_key": st.column_config.TextColumn(
                        "Palavras-chave",
                        help="Separe as palavras-chave por vírgula",
                        width="medium"
                    )
                },
                hide_index=True,
                num_rows="dynamic"
            )

            # Botão para salvar alterações
            if st.button("Salvar Alterações"):
                try:
                    for index, row in edited_df.iterrows():
                        original_row = df_display.iloc[index]
                        you_id = int(original_row['you_id'])  # Garantir que é inteiro
                        current_user_id = int(original_row['user_id'])  # Garantir que é inteiro
                        
                        print(f"\n# Debug - Tentando atualizar registro:")
                        print(f"# Debug - you_id: {you_id} (tipo: {type(you_id)})")
                        print(f"# Debug - user_id: {current_user_id} (tipo: {type(current_user_id)})")
                        print(f"# Debug - Novo valor language: {row['language']} (tipo: {type(row['language'])})")
                        
                        # Primeiro verifica se o registro existe
                        cursor.execute("""
                            SELECT * FROM youtube_tab 
                            WHERE you_id = ? AND user_id = ?
                        """, (you_id, current_user_id))
                        
                        existing = cursor.fetchone()
                        print(f"# Debug - Registro existe? {'Sim' if existing else 'Não'}")
                        
                        if existing:
                            # Tenta o UPDATE com valores explicitamente convertidos
                            cursor.execute("""
                                UPDATE youtube_tab 
                                SET language = ?,
                                    titulo = ?,
                                    autor = ?,
                                    sumario = ?,
                                    duration = ?,
                                    word_key = ?
                                WHERE you_id = ? AND user_id = ?
                            """, (
                                str(row['language']) if row['language'] is not None else None,
                                str(row['titulo']),
                                str(row['autor']),
                                str(row['sumario']),
                                float(row['duration']),
                                str(row['word_key']),
                                you_id,
                                current_user_id
                            ))
                            
                            print(f"# Debug - Query executada - Linhas afetadas: {cursor.rowcount}")
                            
                            # Verifica o valor após a atualização
                            cursor.execute("""
                                SELECT language FROM youtube_tab 
                                WHERE you_id = ? AND user_id = ?
                            """, (you_id, current_user_id))
                            
                            result = cursor.fetchone()
                            print(f"# Debug - Valor após tentativa de update: {result[0] if result else 'Não encontrado'}")
                        
                        conn.commit()  # Commit após cada atualização
                        
                    st.success("Alterações salvas com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar alterações: {str(e)}")
                    print(f"# Debug - Erro detalhado: {str(e)}")
                    print(f"# Debug - Tipo do erro: {type(e)}")
                    conn.rollback()
        else:
            st.info("Nenhum vídeo encontrado para os filtros aplicados.")

    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        print(f"# Debug - Erro detalhado: {str(e)}")
    
    finally:
        # Garantir que a conexão seja fechada mesmo se houver erro
        cursor.close()
        conn.close()

