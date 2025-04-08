# analyzer.py
# 03/03/2025 - 16:00 - versão 1.3


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

# Prompts específicos para cada tipo de análise
PROMPTS = {
    "resumo": """
    Analise o texto fornecido e crie um resumo em tópicos, destacando os principais pontos.
    O resumo deve ser claro, conciso e bem organizado.
    Formato: Lista com bullets dos pontos relevantes.
    """,
    
    "insights": """
    Analise o texto e identifique insights valiosos e sacadas importantes.
    Considere:
    - Ideias inovadoras
    - Conexões não óbvias
    - Aprendizados principais
    - Melhores práticas mencionadas
    Formato: Lista numerada de insights.
    """,
    
    "ferramentas": """
    Identifique todas as ferramentas, produtos, serviços ou recursos mencionados no texto.
    Para cada item, forneça:
    - Nome da ferramenta/produto
    - Breve descrição do uso/finalidade
    - Contexto em que foi mencionado
    Formato: Lista estruturada com nome e descrição de cada item.
    """,
    
    "contraintuitivo": """
    Identifique pontos contraintuitivos ou descobertas inesperadas mencionadas no texto.
    Procure por:
    - Ideias que desafiam o senso comum
    - Descobertas surpreendentes
    - Métodos não convencionais
    - Resultados inesperados
    Formato: Lista de pontos contraintuitivos encontrados.
    """
}

def test_openai_connection():
    """Função para testar a conexão com a OpenAI"""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,  # Usando a constante
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": "Diga 'Conexão estabelecida com sucesso!' em português"}
            ]
        )
        return True, response.choices[0].message.content
    except Exception as e:
        return False, str(e)

# Função para conectar ao banco de dados
def get_db_connection():
    """Estabelece conexão com o banco de dados SQLite"""
    conn = sqlite3.connect('data/you_ana.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para salvar análise no banco de dados
def save_analysis_to_db(user_id, video_title, analysis_type, content):
    """Salva o resultado da análise no banco de dados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se o vídeo já existe para este usuário e obter a URL
    cursor.execute(
        "SELECT url FROM youtube_tab WHERE user_id = ? AND titulo = ?", 
        (user_id, video_title)
    )
    video = cursor.fetchone()
    
    if video:
        # Atualizar o registro existente
        update_query = f"UPDATE youtube_tab SET {analysis_type} = ? WHERE user_id = ? AND titulo = ?"
        cursor.execute(update_query, (content, user_id, video_title))
    else:
        # Se não encontrou o vídeo, algo está errado pois deveria existir
        raise Exception(f"Vídeo '{video_title}' não encontrado na base de dados")
    
    conn.commit()
    conn.close()
    return True

# Função para obter vídeos sem análise
def get_videos_without_analysis(user_id):
    """Retorna vídeos que não possuem resumo"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT titulo FROM youtube_tab WHERE user_id = ? AND (resumo IS NULL OR resumo = '')",
        (user_id,)
    )
    
    videos = [row['titulo'] for row in cursor.fetchall()]
    conn.close()
    return videos

# Função para exportar análise para arquivo de texto
def export_analysis_to_txt(video_title, analyses):
    """Exporta as análises para um arquivo de texto"""
    output_dir = "Z:/youtube/analises"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{video_title}_analise_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"ANÁLISE DO VÍDEO: {video_title}\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
        
        for analysis_type, content in analyses.items():
            f.write(f"=== {analysis_type.upper()} ===\n\n")
            f.write(content)
            f.write("\n\n")
    
    return filename

def analyze_text(text, analysis_type):
    """Realiza a análise do texto usando a OpenAI"""
    try:
        # Dividir o texto em chunks de aproximadamente 12000 tokens
        # (deixando margem para o prompt e a resposta)
        max_chunk_length = 12000
        chunks = [text[i:i + max_chunk_length] for i in range(0, len(text), max_chunk_length)]
        
        all_responses = []
        for i, chunk in enumerate(chunks, 1):
            chunk_prompt = PROMPTS[analysis_type]
            if len(chunks) > 1:
                chunk_prompt += f"\n\nEsta é a parte {i} de {len(chunks)} do texto completo."
            
            response = client.chat.completions.create(
                model=LLM_MODEL,  # Usando a constante
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em análise de conteúdo."},
                    {"role": "user", "content": chunk_prompt + "\n\nTEXTO PARA ANÁLISE:\n" + chunk}
                ],
                temperature=0.7
            )
            all_responses.append(response.choices[0].message.content)
        
        # Combinar as respostas se houver múltiplos chunks
        if len(all_responses) > 1:
            combined_response = "\n\n=== ANÁLISE COMBINADA ===\n\n" + "\n\n".join(all_responses)
        else:
            combined_response = all_responses[0]
            
        return True, combined_response
    except Exception as e:
        return False, str(e)

def process_video(user_id, video_title, content):
    """Processa um vídeo e salva os resultados no banco de dados"""
    results = {}
    success = True
    error_msg = ""
    
    # Mapeamento dos tipos de análise para as colunas corretas do banco de dados
    column_mapping = {
        "resumo": "resumo",
        "insights": "insights",
        "ferramentas": "tools",  # Alterado para corresponder ao nome da coluna no banco
        "contraintuitivo": "contraintuitivo"
    }
    
    for analysis_type in ["resumo", "insights", "ferramentas", "contraintuitivo"]:
        success, result = analyze_text(content, analysis_type)
        if success:
            results[analysis_type] = result
            # Usar o nome correto da coluna ao salvar no banco
            db_column = column_mapping[analysis_type]
            save_analysis_to_db(user_id, video_title, db_column, result)
        else:
            success = False
            error_msg = result
            break
    
    return success, results, error_msg

def show_analyzer():
    st.title("Analisador de Conteúdo")
    
    # Verificar autenticação
    if "user_id" not in st.session_state:
        st.error("Usuário não autenticado. Faça login para continuar.")
        return
    
    user_id = st.session_state["user_id"]
    
    # Diretório das transcrições
    TRANS_DIR = "z:/youtube/transcricoes"
    if not os.path.exists(TRANS_DIR):
        st.error(f"Diretório {TRANS_DIR} não encontrado!")
        return
    
    # Selecionar modo de operação
    mode = st.radio("Selecione o modo de operação:", ["Manual", "Automático"])
    
    if mode == "Manual":
        # Listar arquivos de transcrição
        txt_files = [f for f in os.listdir(TRANS_DIR) if f.endswith('.txt')]
        if not txt_files:
            st.warning("Nenhum arquivo de transcrição encontrado.")
            return
            
        # Seleção do arquivo
        selected_file = st.selectbox("Selecione a transcrição para análise:", txt_files)
        
        if selected_file:
            # Extrair o título do vídeo (nome do arquivo sem extensão)
            video_title = os.path.splitext(selected_file)[0]
            
            # Ler o conteúdo do arquivo
            with open(os.path.join(TRANS_DIR, selected_file), 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Criar tabs para diferentes tipos de análise
            tab1, tab2, tab3, tab4, tab5 = st.tabs(["Resumo", "Insights", "Ferramentas", "Contraintuitivo", "Processar Tudo"])
            
            with tab5:
                if st.button("Processar Todas as Análises", key="process_all"):
                    with st.spinner("Processando todas as análises..."):
                        success, results, error_msg = process_video(user_id, video_title, content)
                        
                        if success:
                            st.success("Todas as análises foram processadas e salvas com sucesso!")
                            
                            # Exportar como arquivo de texto
                            filename = export_analysis_to_txt(video_title, results)
                            st.success(f"Análises exportadas para: {filename}")
                            
                            # Exibir resultados
                            for analysis_type, result in results.items():
                                with st.expander(f"{analysis_type.capitalize()}"):
                                    st.write(result)
                        else:
                            st.error(f"Erro ao processar análises: {error_msg}")
            
            # Processamento individual por tab
            results_dict = {}
            
            with tab1:
                if st.button("Gerar Resumo", key="btn_resumo"):
                    with st.spinner("Gerando resumo..."):
                        success, result = analyze_text(content, "resumo")
                        if success:
                            st.write(result)
                            results_dict["resumo"] = result
                            if st.button("Salvar no Banco de Dados", key="save_resumo"):
                                save_analysis_to_db(user_id, video_title, "resumo", result)
                                # Exportar arquivo após salvar
                                export_analysis_to_txt(video_title, results_dict)
                                st.success("Resumo salvo e exportado com sucesso!")
                        else:
                            st.error(f"Erro: {result}")
            
            with tab2:
                if st.button("Identificar Insights", key="btn_insights"):
                    with st.spinner("Identificando insights..."):
                        success, result = analyze_text(content, "insights")
                        if success:
                            st.write(result)
                            results_dict["insights"] = result
                            if st.button("Salvar no Banco de Dados", key="save_insights"):
                                save_analysis_to_db(user_id, video_title, "insights", result)
                                # Exportar arquivo após salvar
                                export_analysis_to_txt(video_title, results_dict)
                                st.success("Insights salvos e exportados com sucesso!")
                        else:
                            st.error(f"Erro: {result}")
            
            with tab3:
                if st.button("Listar Ferramentas", key="btn_ferramentas"):
                    with st.spinner("Listando ferramentas..."):
                        success, result = analyze_text(content, "ferramentas")
                        if success:
                            st.write(result)
                            results_dict["ferramentas"] = result
                            if st.button("Salvar no Banco de Dados", key="save_ferramentas"):
                                save_analysis_to_db(user_id, video_title, "tools", result)
                                # Exportar arquivo após salvar
                                export_analysis_to_txt(video_title, results_dict)
                                st.success("Ferramentas salvas e exportadas com sucesso!")
                        else:
                            st.error(f"Erro: {result}")
            
            with tab4:
                if st.button("Pontos Contraintuitivos", key="btn_contraintuitivo"):
                    with st.spinner("Identificando pontos contraintuitivos..."):
                        success, result = analyze_text(content, "contraintuitivo")
                        if success:
                            st.write(result)
                            results_dict["contraintuitivo"] = result
                            if st.button("Salvar no Banco de Dados", key="save_contraintuitivo"):
                                save_analysis_to_db(user_id, video_title, "contraintuitivo", result)
                                # Exportar arquivo após salvar
                                export_analysis_to_txt(video_title, results_dict)
                                st.success("Pontos contraintuitivos salvos e exportados com sucesso!")
                        else:
                            st.error(f"Erro: {result}")
    
    else:  # Modo Automático
        # Buscar vídeos sem análise
        videos_without_analysis = get_videos_without_analysis(user_id)
        
        if not videos_without_analysis:
            st.info("Não há vídeos pendentes de análise.")
            return
        
        st.write(f"Encontrados {len(videos_without_analysis)} vídeos sem análise:")
        
        # Mostrar a lista de vídeos para o usuário
        for video in videos_without_analysis:
            st.write(f"- {video}")
        
        # Pedir confirmação ao usuário
        if st.button("Confirmar e Processar Automaticamente"):
            progress_bar = st.progress(0)
            status_container = st.empty()
            results_container = st.container()
            
            for i, video_title in enumerate(videos_without_analysis, 1):
                with status_container:
                    st.write(f"Processando vídeo {i} de {len(videos_without_analysis)}: {video_title}")
                
                file_path = os.path.join(TRANS_DIR, f"{video_title}.txt")
                
                if not os.path.exists(file_path):
                    with results_container:
                        st.error(f"ERRO: Arquivo de transcrição não encontrado para: {video_title}")
                    continue
                
                try:
                    # Ler o conteúdo do arquivo
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    if not content.strip():
                        with results_container:
                            st.error(f"ERRO: Arquivo vazio para: {video_title}")
                        continue
                    
                    # Processar o vídeo
                    success, results, error_msg = process_video(user_id, video_title, content)
                    
                    with results_container:
                        if success:
                            st.success(f"Vídeo processado com sucesso: {video_title}")
                            # Exportar resultados
                            filename = export_analysis_to_txt(video_title, results)
                            st.info(f"Resultados exportados para: {filename}")
                        else:
                            st.error(f"Falha ao processar {video_title}: {error_msg}")
                    
                except Exception as e:
                    with results_container:
                        st.error(f"Erro inesperado ao processar {video_title}: {str(e)}")
                
                # Atualizar barra de progresso
                progress_bar.progress(i / len(videos_without_analysis))
            
            with status_container:
                st.success("Processamento automático finalizado!")

if __name__ == "__main__":
    show_analyzer()
