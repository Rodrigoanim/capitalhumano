# Arquivo: diagnostico.py
# Data: 01/03/2025 - Hora: 11H00
# type: ignore
# pylance: disable=reportMissingModuleSource

import streamlit as st
import sys
import os
import warnings
import logging
import platform
from datetime import datetime
import psutil

def show_diagnostics():
    """Página de diagnóstico do sistema"""
    
    # Verifica se o usuário tem perfil master
    if st.session_state.get("user_profile", "").lower() != "master":
        st.error("Acesso não autorizado. Esta página é restrita para usuários Master.")
        return
    
    st.title("Diagnóstico do Sistema")
    
    # Informações do Sistema
    with st.expander("Informações do Sistema", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Sistema")
            st.write(f"Python Version: {sys.version.split()[0]}")
            st.write(f"Streamlit Version: {st.__version__}")
            st.write(f"OS: {platform.system()} {platform.release()}")
            st.write(f"Ambiente: {'Produção' if os.getenv('RENDER') else 'Local'}")
            
        with col2:
            st.subheader("Recursos")
            st.write(f"CPU Usage: {psutil.cpu_percent()}%")
            st.write(f"Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
            st.write(f"Disk Usage: {psutil.disk_usage('/').percent}%")
    
    # Warnings e Logs
    with st.expander("Warnings e Logs", expanded=True):
        # Inicializar warning_logs na session_state se não existir
        if 'warning_logs' not in st.session_state:
            st.session_state.warning_logs = []
        
        # Configurar captura de warnings
        def warning_callback(message, category, filename, lineno, file=None, line=None):
            st.session_state.warning_logs.append(f"{datetime.now()}: {category.__name__}: {message}")
        
        warnings.showwarning = warning_callback
        
        # Mostrar warnings capturados
        st.subheader("Warnings Ativos")
        if st.session_state.warning_logs:
            for log in st.session_state.warning_logs:
                st.warning(log)
        else:
            st.info("Nenhum warning capturado ainda")
        
        # Status da barra de progresso
        st.subheader("Status da Barra de Progresso")
        progress_color = st.empty()
        
        if st.button("Testar Warning"):
            warnings.warn("Este é um warning de teste")
            st.rerun()
    
    # Variáveis de Ambiente
    with st.expander("Variáveis de Ambiente", expanded=True):
        st.subheader("Variáveis de Ambiente")
        env_vars = {key: value for key, value in os.environ.items() 
                   if not any(secret in key.lower() for secret in ['key', 'pass', 'secret', 'token'])}
        st.json(env_vars)
    
    # Session State
    with st.expander("Session State", expanded=True):
        st.subheader("Session State")
        # Filtra informações sensíveis
        safe_session = {k: v for k, v in st.session_state.items() 
                       if not any(secret in k.lower() for secret in ['key', 'pass', 'secret', 'token'])}
        st.json(safe_session)

def main():
    show_diagnostics()

if __name__ == "__main__":
    main()


