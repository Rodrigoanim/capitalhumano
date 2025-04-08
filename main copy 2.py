# Arquivo: main.py
# Youtube Analyzer - Agente IA para análise de vídeos do YouTube
# comando: streamlit run main.py
# 04/03/2025 - 09:00 - versão 1.2

import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import time
import sys
import os
from pathlib import Path
import streamlit.components.v1 as components
from paginas.monitor import registrar_acesso  # Importação para registro de atividades

# Definição de caminhos
BASE_DIR = Path(__file__).parent  # Obtém o diretório onde está o main.py
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "you_ana.db"

# Configuração da página - deve ser a primeira chamada do Streamlit
st.set_page_config(
    page_title="Youtube Analyzer - Estude e Analise Vídeos",
    page_icon="🎬",
    layout="wide",
    menu_items={
        'About': """
        ### Sobre o Sistema - Youtube Analyzer
        
        Versão: 1.0.0 Beta
        
        Este sistema foi desenvolvido para ajudar a estudar, internalizar 
        e analisar vídeos do YouTube de forma eficiente.
        
        © 2025 Todos os direitos reservados.
        """,
        'Get Help': None,
        'Report a bug': None
    },
    initial_sidebar_state="expanded"
)

# Atualizar metadados Open Graph
# components.html(
#     """
#     <head>
#         <title>Youtube Analyzer - Estude e Analise Vídeos</title>
#         <meta charset="utf-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1">
#         <meta name="description" content="Ferramenta de IA para análise e estudo de vídeos do YouTube">
#         <!-- Open Graph / Facebook -->                
#         <meta property="og:type" content="website">
#         <meta property="og:url" content="https://youtube-analyzer.render.com/">
#         <meta property="og:title" content="Youtube Analyzer - Estude e Analise Vídeos">
#         <meta property="og:description" content="Ferramenta de IA para análise e estudo de vídeos do YouTube">
#         <meta property="og:image" content="https://example.com/youtube-analyzer.jpg">
#         <meta property="og:site_name" content="Youtube Analyzer">    
#         <!-- Adicional SEO -->
#         <meta name="author" content="Youtube Analyzer">
#         <meta name="keywords" content="youtube, análise de vídeo, transcrição, IA, aprendizado">
#         <link rel="canonical" href="https://youtube-analyzer.render.com/">
#     </head>
#     """,
#     height=0,
#     width=0
# )

def authenticate_user():
    """Autentica o usuário e verifica seu perfil no banco de dados."""
    # Verifica se o banco existe
    if not DB_PATH.exists():
        st.error(f"Banco de dados não encontrado em {DB_PATH}")
        return False, None
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if "user_profile" not in st.session_state:
        st.session_state["user_profile"] = None

    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None

    if not st.session_state["logged_in"]:
        # Criar uma coluna centralizada
        col1, col2, col3 = st.columns([1, 20, 1])
        
        with col2:
            # Imagem de capa
            st.image("webinar_1.jpg", use_container_width=True)
            
        st.markdown("""
            <p style='text-align: center; font-size: 35px;font-weight: bold;'>Youtube Analyzer</p>
            <p style='text-align: center; font-size: 20px;'>Estude, Internalize e Analise Vídeos do YouTube</p>
        """, unsafe_allow_html=True)
        
        # Login na sidebar
        st.sidebar.title("Youtube Analyzer - versão 1.1")
        email = st.sidebar.text_input("E-mail", key="email")
        password = st.sidebar.text_input("Senha", type="password", key="password", on_change=lambda: st.session_state.update({"enter_pressed": True}) if "password" in st.session_state else None)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            login_button = st.button("Entrar") or st.session_state.get("enter_pressed", False)
            if "enter_pressed" in st.session_state:
                st.session_state.enter_pressed = False
        
        if login_button:
            cursor.execute("""
                SELECT id, user_id, perfil, nome FROM usuarios_tab WHERE email = ? AND senha = ?
            """, (email, password))
            user = cursor.fetchone()

            if user:
                st.session_state["logged_in"] = True
                st.session_state["user_profile"] = user[2]
                st.session_state["user_id"] = user[1]
                st.session_state["user_name"] = user[3]
                
                # Registrar o acesso bem-sucedido
                registrar_acesso(
                    user_id=user[1],
                    programa="main.py",
                    acao="login"
                )
                
                st.sidebar.success(f"Login bem-sucedido! Bem-vindo, {user[3]}.")
                st.rerun()
            else:
                st.sidebar.error("E-mail ou senha inválidos.")

    return st.session_state.get("logged_in", False), st.session_state.get("user_profile", None)

def get_timezone_offset():
    """
    Determina se é necessário aplicar offset de timezone baseado no ambiente
    """
    is_production = os.getenv('RENDER') is not None
    
    if is_production:
        # Se estiver no Render, ajusta 3 horas para trás
        return datetime.now() - timedelta(hours=3)
    return datetime.now()  # Se local, usa hora atual

def show_welcome():
    """Exibe a tela de boas-vindas com informações do usuário"""
    st.markdown("""
        <p style='text-align: left; font-size: 40px; font-weight: bold;'>Bem-vindo ao Youtube Analyzer!</p>
    """, unsafe_allow_html=True)
    
    # Buscar dados do usuário
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT email, empresa 
        FROM usuarios_tab 
        WHERE user_id = ?
    """, (st.session_state.get('user_id'),))
    user_info = cursor.fetchone()
    conn.close()
    
    empresa = user_info[1] if user_info and user_info[1] is not None else "Não informada"
    
    # Layout em colunas usando st.columns
    col1, col2, col3 = st.columns(3)
    
    # Coluna 1: Dados do Usuário
    with col1:
        st.markdown(f"""
            <div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px;">
                <p style="color: #2c3e50; font-size: 24px;">Seus Dados</p>
                <div style="color: #34495e; font-size: 16px;">
                    <p>ID: {st.session_state.get('user_id')}</p>
                    <p>Nome: {st.session_state.get('user_name')}</p>
                    <p>E-mail: {user_info[0] if user_info else 'N/A'}</p>
                    <p>Empresa: {empresa}</p>
                    <p>Perfil: {st.session_state.get('user_profile')}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Coluna 2: Atividades (atualizada com hora)
    with col2:
        current_time = get_timezone_offset()
        ambiente = "Produção" if os.getenv('RENDER') else "Local"
        
        st.markdown(f"""
            <div style="background-color: #e8f8ef; padding: 20px; border-radius: 8px;">
                <p style="color: #2c3e50; font-size: 24px;">Suas Atividades</p>
                <div style="color: #34495e; font-size: 16px;">
                    <p>Data Atual: {current_time.strftime('%d/%m/%Y')}</p>
                    <p>Hora Atual: {current_time.strftime('%H:%M:%S')}</p>
                    <p>Ambiente: {ambiente}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Coluna 3: Módulos
    with col3:
        modulos_html = """
            <div style="background-color: #fff8e8; padding: 20px; border-radius: 8px;">
                <p style="color: #2c3e50; font-size: 24px;">Módulos Disponíveis</p>
                <div style="color: #34495e; font-size: 16px;">
                    <p>Entrada de Dados - URL e Metadados</p>
                    <p>Captura de Vídeo e Áudio</p>
                    <p>Transcrição de Áudio</p>
                    <p>Analisador de Conteúdo</p>
                </div>
            </div>
        """
        
        st.markdown(modulos_html, unsafe_allow_html=True)

def main():
    """Gerencia a navegação entre as páginas do sistema."""
    # Verifica se o diretório data existe
    if not DATA_DIR.exists():
        st.error(f"Pasta '{DATA_DIR}' não encontrada. O programa não pode continuar.")
        st.stop()
        
    # Verifica se o banco existe
    if not DB_PATH.exists():
        st.error(f"Banco de dados '{DB_PATH}' não encontrado. O programa não pode continuar.")
        st.stop()
        
    logged_in, user_profile = authenticate_user()
    
    if not logged_in:
        st.stop()
    
    # Armazenar página anterior para comparação
    if "previous_page" not in st.session_state:
        st.session_state["previous_page"] = None
    
    # Titulo da página
    st.markdown("""
        <p style='text-align: left; font-size: 44px; font-weight: bold;'>
            Youtube Analyzer - Estude e Analise Vídeos
        </p>
    """, unsafe_allow_html=True)

    # Adicionar informação do usuário logado
    st.sidebar.markdown(f"""
        **Usuário:** {st.session_state.get('user_name')}  
        **ID:** {st.session_state.get('user_id')}  
        **Perfil:** {st.session_state.get('user_profile')}
    """)

    if st.sidebar.button("Logout"):
        # Registrar o logout antes de limpar a sessão
        if "user_id" in st.session_state:
            registrar_acesso(
                user_id=st.session_state["user_id"],
                programa="main.py",
                acao="logout"
            )
        
        for key in ['logged_in', 'user_profile', 'user_id', 'user_name']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.title("Menu de Navegação")
    
    # Criando grupos de menu
    menu_groups = {
        "Principal": ["Bem-vindo"],
        "Ferramentas": [
            "Entrada de Dados - URL e Metadados",
            "Captura de Vídeo",
            "Transcrição de Áudio",
            "Analisador de Conteúdo"
        ],
        "Administração": []  # Iniciando vazio para adicionar itens na ordem correta
    }
    
    # Adicionar opções administrativas na ordem desejada
    if user_profile and user_profile.lower() == "master":
        menu_groups["Administração"].append("Info Tabelas (CRUD)")
    if user_profile and user_profile.lower() == "master":
        menu_groups["Administração"].append("Diagnóstico")
    if user_profile and user_profile.lower() in ["adm", "master"]:
        menu_groups["Administração"].append("Monitor de Uso")
    
    # Se não houver opções de administração, remover o grupo
    if not menu_groups["Administração"]:
        menu_groups.pop("Administração")
    
    # Criar seletor de grupo
    selected_group = st.sidebar.selectbox(
        "Selecione o módulo:",
        options=list(menu_groups.keys()),
        key="group_selection"
    )
    
    # Criar seletor de página dentro do grupo
    section = st.sidebar.radio(
        "Selecione a página:",
        menu_groups[selected_group],
        key="menu_selection"
    )

    # Verificar se houve mudança de página
    if st.session_state.get("previous_page") != section:
        st.session_state["previous_page"] = section

    # Processa a seção selecionada
    if section == "Bem-vindo":
        show_welcome()
    elif section == "Entrada de Dados - URL e Metadados":
        from paginas.url_metadados import show_url_metadados
        show_url_metadados()
    elif section == "Captura de Vídeo":
        from paginas.video_capture import show_video_capture
        show_video_capture()
    elif section == "Transcrição de Áudio":
        from paginas.transcribe_audio import show_transcribe_audio
        show_transcribe_audio()
    elif section == "Analisador de Conteúdo":
        from paginas.analyzer import show_analyzer
        show_analyzer()
    elif section == "Info Tabelas (CRUD)":
        from paginas.crude import show_crud
        show_crud()
    elif section == "Monitor de Uso":
        from paginas.monitor import main as show_monitor
        show_monitor()
    elif section == "Diagnóstico":
        from paginas.diagnostico import show_diagnostics
        show_diagnostics()

if __name__ == "__main__":
    main()
