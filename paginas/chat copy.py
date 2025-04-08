# chat.py
# 06/03/2025 - 16:00 - Ok v1


from dotenv import load_dotenv
import os
import openai
from openai import OpenAI
import streamlit as st
import sqlite3
import json
from datetime import datetime

# Configurações globais
# Opções de modelos OpenAI:
# GPT-4 Models:
#   - gpt-4-turbo-preview    (128k context, mais recente e mais capaz)
#   - gpt-4                  (8k context)
#   - gpt-4-32k             (32k context)
# GPT-3.5 Models:
#   - gpt-3.5-turbo         (4k context, bom custo-benefício)
#   - gpt-3.5-turbo-16k     (16k context)
# Modelos Legados (não recomendados para novos projetos):
#   - gpt-3.5-turbo-0613
#   - gpt-4-0613
#   - gpt-4-32k-0613
LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')  # Permite override via variável de ambiente

# Carregar variáveis de ambiente
load_dotenv()

# Configurar cliente OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_user_videos(user_id):
    """Recupera os vídeos disponíveis para o usuário."""
    try:
        conn = sqlite3.connect('data/you_ana.db')
        cursor = conn.cursor()
        
        query = """
            SELECT you_id, titulo, url, autor, duration 
            FROM youtube_tab 
            WHERE user_id = ?
            ORDER BY titulo
        """
        cursor.execute(query, (user_id,))
        videos = cursor.fetchall()
        conn.close()
        return videos
    except sqlite3.Error as e:
        st.error(f"Erro ao acessar banco de dados: {e}")
        return []

def load_transcription(video_title):
    """Carrega a transcrição do vídeo da pasta de transcrições."""
    try:
        # Debug
        print(f"# Debug - Procurando transcrição para: {video_title}")
        
        # Corrigindo o path com separador correto
        base_path = 'Z:\\youtube\\transcricoes'  # Usando double backslash
        # Alternativa: base_path = r'Z:\youtube\transcricoes'  # Usando raw string
        
        # Debug
        print(f"# Debug - Tentando acessar pasta: {base_path}")
        
        # Lista todos os arquivos na pasta de transcrições
        available_files = os.listdir(base_path)
        
        # Debug
        print(f"# Debug - Arquivos disponíveis: {available_files}")
        
        # Procura por arquivo que contenha o título (ignorando case e caracteres especiais)
        for file in available_files:
            if file.endswith('.txt'):
                # Normaliza os nomes para comparação
                normalized_file = file.lower().replace(' ', '').replace('_', '').replace('-', '')
                normalized_title = video_title.lower().replace(' ', '').replace('_', '').replace('-', '')
                
                if normalized_title in normalized_file:
                    file_path = os.path.join(base_path, file)
                    # Debug
                    print(f"# Debug - Arquivo encontrado: {file_path}")
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
        
        # Se não encontrar o arquivo
        st.warning(f"Transcrição não encontrada para: {video_title}")
        # Debug
        print(f"# Debug - Nenhum arquivo correspondente encontrado para: {video_title}")
        return None
            
    except Exception as e:
        st.error(f"Erro ao carregar transcrição: {e}")
        print(f"# Debug - Erro: {str(e)}")
        return None

def get_chat_response(prompt, transcription, mode="qa", temperature=0.7):
    """Obtém resposta do modelo baseado no modo selecionado."""
    try:
        # Debug - Início da função
        print(f"# Debug - Iniciando get_chat_response")
        print(f"# Debug - Modo: {mode}")
        print(f"# Debug - Modelo: {LLM_MODEL}")
        
        system_prompts = {
            "resumo": "Gere um resumo conciso do conteúdo da transcrição.",
            "qa": "Responda perguntas sobre o conteúdo da transcrição de forma precisa.",
            "analise": """Analise o conteúdo fornecendo:
                        1. Principais insights
                        2. Pontos contraintuitivos
                        3. Palavras-chave relevantes
                        4. Ferramentas ou metodologias mencionadas"""
        }

        messages = [
            {"role": "system", "content": system_prompts[mode]},
            {"role": "user", "content": f"Transcrição: {transcription}\n\nPrompt: {prompt}"}
        ]

        # Debug - Antes da chamada API
        print(f"# Debug - Enviando requisição para OpenAI")
        print(f"# Debug - System prompt: {system_prompts[mode]}")
        print(f"# Debug - User prompt: {prompt[:100]}...")  # Primeiros 100 caracteres

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature
        )

        # Debug - Após chamada API
        print(f"# Debug - Resposta recebida da API")
        content = response.choices[0].message.content
        print(f"# Debug - Conteúdo da resposta: {content[:100]}...")  # Primeiros 100 caracteres

        return content
    except Exception as e:
        print(f"# Debug - ERRO: {str(e)}")
        st.error(f"Erro ao obter resposta: {e}")
        return None

def save_chat_history(user_id, you_id, chat_history):
    """Salva o histórico do chat no banco de dados."""
    try:
        conn = sqlite3.connect('data/you_ana.db')
        cursor = conn.cursor()
        
        # Convertendo o histórico para JSON
        chat_json = json.dumps(chat_history)
        
        # Atualizando ou inserindo na tabela youtube_tab
        cursor.execute("""
            UPDATE youtube_tab 
            SET chat_history = ? 
            WHERE user_id = ? AND you_id = ?
        """, (chat_json, user_id, you_id))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Erro ao salvar histórico: {e}")
        return False

def main():
    st.markdown("""
        <p style='
            text-align: center;
            font-size: 40px;
            font-weight: bold;
        '>Assistente de Vídeo</p>
    """, unsafe_allow_html=True)

    # Verificar se usuário está logado
    if 'user_id' not in st.session_state:
        st.warning("Por favor, faça login para acessar o chat.")
        return

    user_id = st.session_state.user_id
    
    # Carregar vídeos do usuário
    videos = get_user_videos(user_id)
    
    if not videos:
        st.warning("Nenhum vídeo encontrado para este usuário.")
        return

    # Criar seletor de vídeos
    video_options = {f"{title} ({autor})": (you_id, title) 
                    for you_id, title, _, autor, _ in videos}
    
    selected_video = st.selectbox(
        "Selecione um vídeo para análise:",
        options=list(video_options.keys())
    )

    # Botão para confirmar a seleção e carregar a transcrição
    if st.button("Carregar Vídeo"):
        if selected_video:
            you_id, title = video_options[selected_video]
            
            # Exibir metadados do vídeo selecionado
            video_info = next(v for v in videos if v[0] == you_id)
            _, titulo, url, autor, duration = video_info
            
            st.markdown("### Informações do Vídeo")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Título:** {titulo}")
                st.write(f"**Autor:** {autor}")
            with col2:
                st.write(f"**Duração:** {duration:.2f} minutos")
                st.write(f"**URL:** {url}")

            # Carregar transcrição
            transcription = load_transcription(titulo)
            if transcription:
                st.session_state['current_transcription'] = transcription
                st.session_state['current_video_id'] = you_id
                st.success("Transcrição carregada com sucesso!")

                # Interface do chat
                st.markdown("### Chat Assistente")

                # Inicializar histórico do chat se necessário
                if 'chat_history' not in st.session_state:
                    st.session_state.chat_history = []

                # Seletor de modo
                chat_mode = st.selectbox(
                    "Selecione o modo de interação:",
                    options=["Q&A", "Resumo", "Análise Profunda"],
                    key="chat_mode"
                )

                # Área do chat
                st.markdown("#### Histórico do Chat")
                chat_container = st.container()
                with chat_container:
                    for msg in st.session_state.chat_history:
                        if msg["role"] == "user":
                            st.markdown("**Você:** " + msg["content"])
                        else:
                            st.markdown("**Assistente:** " + msg["content"])

                # Input do usuário
                user_input = st.text_area("Digite sua mensagem:", key="user_input")
                col1, col2, col3 = st.columns([1,1,1])
                
                with col1:
                    if st.button("Enviar"):
                        if user_input:
                            # Adicionar mensagem do usuário ao histórico
                            st.session_state.chat_history.append(
                                {"role": "user", "content": user_input}
                            )
                            
                            # Obter resposta baseada no modo
                            mode_map = {
                                "Q&A": "qa",
                                "Resumo": "resumo",
                                "Análise Profunda": "analise"
                            }
                            
                            response = get_chat_response(
                                user_input,
                                st.session_state.current_transcription,
                                mode=mode_map[chat_mode]
                            )
                            
                            if response:
                                st.session_state.chat_history.append(
                                    {"role": "assistant", "content": response}
                                )
                            
                            # Limpar input
                            st.session_state.user_input = ""
                
                with col2:
                    if st.button("Limpar Chat"):
                        st.session_state.chat_history = []
                
                with col3:
                    if st.button("Salvar Histórico"):
                        if save_chat_history(
                            st.session_state.user_id,
                            st.session_state.current_video_id,
                            st.session_state.chat_history
                        ):
                            st.success("Histórico salvo com sucesso!")

if __name__ == "__main__":
    main()