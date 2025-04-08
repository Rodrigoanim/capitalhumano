# Arquivo: monitor.py
# Data: 01/03/2025 11:00
# Dashboard de monitoramento de uso
# type: ignore
# pylance: disable=reportMissingModuleSource

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
import io
import tempfile
import matplotlib.pyplot as plt
import traceback
from config import DB_PATH
import os

try:
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
        KeepTogether
    )
except ImportError as e:
    print(f"Erro ao importar ReportLab: {e}")

def criar_conexao():
    """Cria conexão com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    criar_tabelas(conn)
    return conn

def get_timezone_adjusted_datetime():
    """
    Retorna a data e hora atual ajustada com base no ambiente
    """
    current = datetime.now()
    # Se estiver no Render, ajusta 3 horas para trás
    if os.getenv('RENDER'):
        current = current - timedelta(hours=3)
    return current

def carregar_dados_acessos():
    """Carrega dados de acessos do banco de dados"""
    conn = criar_conexao()
    
    # Ajusta a query baseada no ambiente
    timezone_adjust = "'+3 hours'" if os.getenv('RENDER') else "'0 hours'"
    
    # Query para acessos por empresa
    query_empresas = """
    SELECT u.empresa, COUNT(*) as quantidade_acessos 
    FROM log_acessos la
    JOIN usuarios_tab u ON la.user_id = u.user_id
    WHERE u.empresa IS NOT NULL
    AND la.data_acesso >= date('now', '-30 days')
    GROUP BY u.empresa
    ORDER BY quantidade_acessos DESC
    LIMIT 10
    """
    
    # Query para acessos por usuário
    query_usuarios = f"""
    SELECT 
        u.nome, 
        u.empresa, 
        COUNT(*) as quantidade_acessos,
        MAX(la.data_acesso || ' ' || COALESCE(la.hora_acesso, '00:00:00')) as ultimo_acesso
    FROM log_acessos la
    JOIN usuarios_tab u ON la.user_id = u.user_id
    WHERE date(la.data_acesso) >= date('now', '-30 days')
    GROUP BY u.user_id, u.nome, u.empresa
    ORDER BY quantidade_acessos DESC
    LIMIT 10
    """
    
    # Query para frequência de acessos diários
    query_frequencia = """
    WITH RECURSIVE dates(date) AS (
        SELECT date('now', '-30 days')
        UNION ALL
        SELECT date(date, '+1 day')
        FROM dates
        WHERE date < date('now')
    )
    SELECT 
        dates.date as data_acesso,
        COUNT(DISTINCT la.user_id) as usuarios_unicos,
        COUNT(la.id) as total_acessos,
        GROUP_CONCAT(DISTINCT COALESCE(la.hora_acesso, '00:00:00')) as horarios_acesso
    FROM dates
    LEFT JOIN log_acessos la ON date(la.data_acesso) = dates.date
    GROUP BY dates.date
    ORDER BY dates.date
    """
    
    try:
        df_empresas = pd.read_sql_query(query_empresas, conn)
    except Exception as e:
        st.warning(f"Erro ao carregar dados de empresas: {str(e)}")
        df_empresas = pd.DataFrame(columns=['empresa', 'quantidade_acessos'])
    
    try:
        df_usuarios = pd.read_sql_query(query_usuarios, conn)
    except Exception as e:
        st.warning(f"Erro ao carregar dados de usuários: {str(e)}")
        df_usuarios = pd.DataFrame(columns=['nome', 'empresa', 'quantidade_acessos', 'ultimo_acesso'])
    
    try:
        df_frequencia = pd.read_sql_query(query_frequencia, conn)
    except Exception as e:
        st.warning(f"Erro ao carregar dados de frequência: {str(e)}")
        df_frequencia = pd.DataFrame(columns=['data_acesso', 'usuarios_unicos', 'total_acessos', 'horarios_acesso'])
    
    conn.close()
    return df_empresas, df_usuarios, df_frequencia

def registrar_acesso(user_id, programa, acao):
    """
    Registra o acesso do usuário no banco de dados com ajuste de timezone
    """
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Obtém data e hora ajustadas
        dt_adjusted = get_timezone_adjusted_datetime()
        data_acesso = dt_adjusted.strftime('%Y-%m-%d')
        hora_acesso = dt_adjusted.strftime('%H:%M:%S')
        
        cursor.execute("""
        INSERT INTO log_acessos (
            user_id,
            data_acesso,
            hora_acesso,
            programa,
            acao
        )
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, data_acesso, hora_acesso, programa, acao))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        st.error(f"Erro ao registrar acesso: {str(e)}")
        if 'conn' in locals():
            conn.close()

def subtitulo():
    """
    Exibe um subtítulo centralizado com estilo personalizado
    """
    st.markdown("""
        <p style='
            text-align: Left;
            font-size: 36px;
            color: #000000;
            margin-top: 10px;
            margin-bottom: 30px;
            font-family: sans-serif;
            font-weight: 500;
        '>Dashboard de Monitoramento de Uso</p>
    """, unsafe_allow_html=True)

def verificar_dados():
    """Verifica se há dados nas tabelas"""
    conn = criar_conexao()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM log_acessos")
    count_log = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM usuarios_tab")
    count_usuarios = cursor.fetchone()[0]
    
    conn.close()
    
    return count_log > 0 and count_usuarios > 0

def criar_tabelas(conn):
    """Cria as tabelas necessárias se não existirem"""
    cursor = conn.cursor()
    
    # Criar tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios_tab (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        nome TEXT NOT NULL,
        email TEXT NOT NULL,
        senha TEXT NOT NULL,
        perfil TEXT NOT NULL,
        empresa TEXT
    )
    """)
    
    # Criar tabela de log de acessos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_acessos (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        data_acesso DATE NOT NULL,
        programa TEXT NOT NULL,
        acao TEXT NOT NULL,
        hora_acesso TIME
    )
    """)
    
    conn.commit()

def main():
    subtitulo()
    
    try:
        # Verificar se há dados
        if not verificar_dados():
            st.warning("Não há dados suficientes nas tabelas. Adicione alguns registros para visualizar os gráficos.")
            if st.button("Adicionar Dados de Exemplo"):
                adicionar_dados_exemplo()
        
        df_empresas, df_usuarios, df_frequencia = carregar_dados_acessos()
        
        # Container para reduzir largura
        col1, col2, col3 = st.columns([1, 8, 1])  # 80% da largura
        with col2:
            # Gráfico de acessos por empresa
            st.subheader("Top 10 Empresas por Quantidade de Acessos")
            fig_empresas = px.bar(df_empresas, 
                                x='empresa', 
                                y='quantidade_acessos',
                                title="Acessos por Empresa")
            st.plotly_chart(fig_empresas, use_container_width=True)
            
            # 1 linha de espaço
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Tabela de empresas logo abaixo do seu gráfico
            st.dataframe(df_empresas, use_container_width=True)
            
            # 3 linhas de espaço entre grupos
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            
            # Gráfico de acessos por usuário
            st.subheader("Top 10 Usuários por Quantidade de Acessos")
            fig_usuarios = px.bar(df_usuarios, 
                                x='nome', 
                                y='quantidade_acessos',
                                title="Acessos por Usuário",
                                hover_data=['empresa'])
            st.plotly_chart(fig_usuarios, use_container_width=True)
            
            # 1 linha de espaço
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Tabela de usuários logo abaixo do seu gráfico
            st.dataframe(
                df_usuarios.rename(columns={
                    'ultimo_acesso': 'Último Acesso',
                    'nome': 'Nome',
                    'empresa': 'Empresa',
                    'quantidade_acessos': 'Quantidade de Acessos'
                }),
                use_container_width=True
            )
            
            # 3 linhas de espaço entre grupos
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            
            # Gráfico de linha do tempo
            st.subheader("Evolução de Usuários Únicos nos Últimos 30 dias")
            fig_timeline = px.line(df_frequencia, 
                                 x='data_acesso', 
                                 y='usuarios_unicos',
                                 title="Evolução do Uso ao Longo do Tempo")
            st.plotly_chart(fig_timeline, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {str(e)}")
        st.error(traceback.format_exc())

def clear_log_flags():
    """Limpa as flags de registro de log quando o usuário faz logout"""
    for key in list(st.session_state.keys()):
        if key.startswith('log_registered_'):
            del st.session_state[key]

if __name__ == "__main__":
    main()
