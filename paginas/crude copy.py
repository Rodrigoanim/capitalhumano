# Arquivo: crude.py
# Data: 06/03/2025  18:00
# IDE Cursor - claude 3.5 sonnet

import streamlit as st
import pandas as pd
import sqlite3

from config import DB_PATH  # Adicione esta importação

def format_br_number(value):
    """Formata um número para o padrão brasileiro."""
    try:
        if pd.isna(value) or value == '':
            return ''
        return f"{float(str(value).replace(',', '.')):.2f}".replace('.', ',')
    except:
        return ''

def get_table_analysis(cursor, table_name):
    """Analisa a estrutura e dados da tabela."""
    # Análise da estrutura
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    
    # Contagem de registros
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    record_count = cursor.fetchone()[0]
    
    # Data da última atualização (assumindo que existe uma coluna 'data' ou similar)
    try:
        cursor.execute(f"SELECT MAX(data) FROM {table_name}")
        last_update = cursor.fetchone()[0]
    except:
        last_update = "N/A"
    
    # Maior user_id
    try:
        cursor.execute(f"SELECT MAX(user_id) FROM {table_name}")
        max_user_id = cursor.fetchone()[0]
    except:
        max_user_id = "N/A"
    
    return {
        "columns": columns_info,
        "record_count": record_count,
        "last_update": last_update,
        "max_user_id": max_user_id
    }

def show_crud():
    """Exibe registros administrativos em formato de tabela."""
    
    # Definição dos tamanhos de coluna por tabela
    COLUMN_WIDTHS = {
        'usuarios_tab': {
            'id': 'small',
            'user_id': 'small',
            'nome': 'medium',
            'email': 'medium',
            'senha': 'small',
            'perfil': 'small',
            'empresa': 'medium'
        },
        'log_acessos': {
            'id': 'small',
            'user_id': 'small',
            'data_acesso': 'small',
            'programa': 'medium',
            'acao': 'medium',
            'hora_acesso': 'small'
        },
        'youtube_tab': {
            'you_id': 'small',
            'titulo': 'medium',
            'url': 'medium',
            'autor': 'small',
            'user_id': 'small',
            'resumo': 'medium',
            'insights': 'medium',
            'contraintuitivo': 'medium',
            'word_key': 'medium',
            'tools': 'medium'
        }
    }

    st.title("Lista de Registros ADM")
    
    # Botão para mostrar/esconder debug
    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False
    
    if st.button("Toggle Debug Info"):
        st.session_state.show_debug = not st.session_state.show_debug
    
    if st.button("Atualizar Dados"):
        st.rerun()
    
    # Busca as tabelas do banco de dados
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    db_tables = [table[0] for table in cursor.fetchall()]
    conn.close()
    
    # Adiciona uma opção vazia no início
    tables = [""] + db_tables
    
    # Mostra debug info apenas se o botão estiver ativado
    if st.session_state.show_debug:
        with st.expander("Debug Information", expanded=True):
            st.write("Tabelas disponíveis:", db_tables)
            st.write("Estado atual do debug:", st.session_state.show_debug)
            st.write("Tabelas na lista de seleção:", tables)

    # Cria três colunas, com a do meio tendo 30% da largura
    col1, col2, col3 = st.columns([3.5, 3, 3.5])
    
    # Coloca o selectbox na coluna do meio
    with col2:
        selected_table = st.selectbox("Selecione a tabela", tables, key="table_selector")
    
    if selected_table:
        # Add debug information
        st.write(f"Conectando ao banco de dados: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Add debug query to check table existence
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (selected_table,))
            if not cursor.fetchone():
                st.error(f"Tabela '{selected_table}' não encontrada no banco de dados!")
                return

            # Test query to verify data
            cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
            count = cursor.fetchone()[0]
            st.write(f"Número de registros encontrados: {count}")
            
            # For usuarios_tab specifically, let's verify the data directly
            if selected_table == "usuarios_tab":
                cursor.execute("SELECT * FROM usuarios_tab LIMIT 1")
                sample = cursor.fetchone()
                if sample:
                    st.write("Exemplo de registro encontrado:", sample)
                
            # Análise da tabela
            analysis = get_table_analysis(cursor, selected_table)
            
            # Obtém informações das colunas aqui, antes de usar
            cursor.execute(f"PRAGMA table_info({selected_table})")
            columns_info = cursor.fetchall()  # Define columns_info aqui
            
            # Exibe informações da tabela em um expander
            with st.expander("Informações da Tabela", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Registros", analysis["record_count"])
                with col2:
                    if selected_table == "log_acessos":
                        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM log_acessos")
                        unique_users = cursor.fetchone()[0]
                        st.metric("Usuários Únicos", unique_users)
                    else:
                        st.metric("Última Atualização", analysis["last_update"])
                with col3:
                    if selected_table == "log_acessos":
                        cursor.execute("SELECT COUNT(DISTINCT data_acesso) FROM log_acessos")
                        unique_dates = cursor.fetchone()[0]
                        st.metric("Dias com Registros", unique_dates)
                    else:
                        st.metric("Maior User ID", analysis["max_user_id"])
                
                # Exibe estrutura da tabela
                st.write("### Estrutura da Tabela")
                structure_df = pd.DataFrame(
                    analysis["columns"],
                    columns=["cid", "name", "type", "notnull", "dflt_value", "pk"]
                )
                st.dataframe(
                    structure_df[["name", "type", "notnull", "pk"]],
                    hide_index=True,
                    use_container_width=True
                )
            
            # Busca dados
            if selected_table == "log_acessos":
                # Ordenação específica para log_acessos
                cursor.execute("""
                    SELECT 
                        id as 'id',
                        user_id as 'user_id',
                        data_acesso as 'data_acesso',
                        programa as 'programa',
                        acao as 'acao',
                        time(hora_acesso) as 'hora_acesso'
                    FROM log_acessos 
                    ORDER BY data_acesso DESC, hora_acesso DESC, id DESC
                """)
            elif selected_table == "usuarios_tab":
                # Adiciona filtro por user_id para usuarios_tab
                user_id_filter = st.number_input("Filtrar por User ID (0 para mostrar todos)", min_value=0, value=0)
                
                # Adiciona seleção de ordenação com as colunas corretas
                sort_column = st.selectbox(
                    "Ordenar por coluna",
                    ["id", "user_id", "nome", "email", "senha", "perfil", "empresa"],
                    index=0
                )
                sort_order = st.selectbox("Ordem", ["ASC", "DESC"], index=0)
                
                # Query com filtro e ordenação
                query = f"""
                    SELECT * FROM usuarios_tab
                    {f"WHERE user_id = {user_id_filter}" if user_id_filter > 0 else ""}
                    ORDER BY {sort_column} {sort_order}
                """
                cursor.execute(query)
            else:
                cursor.execute(f"SELECT * FROM {selected_table}")
            
            data = cursor.fetchall()
            
            # Busca nomes das colunas
            cursor.execute(f"PRAGMA table_info({selected_table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Cria DataFrame
            df = pd.DataFrame(data, columns=columns)
            
            # Configuração específica para log_acessos
            if selected_table == "log_acessos":
                column_config = {
                    "id": st.column_config.NumberColumn(
                        "id",
                        width="small",
                        required=True,
                    ),
                    "user_id": st.column_config.NumberColumn(
                        "user_id",
                        width="small",
                        required=True,
                    ),
                    "data_acesso": st.column_config.TextColumn(
                        "data_acesso",
                        width="medium",
                        required=True,
                        help="Formato: YYYY-MM-DD"
                    ),
                    "programa": st.column_config.TextColumn(
                        "programa",
                        width="medium",
                        required=True,
                    ),
                    "acao": st.column_config.TextColumn(
                        "acao",
                        width="medium",
                        required=True,
                    ),
                    "hora_acesso": st.column_config.TextColumn(
                        "hora_acesso",
                        width="small",
                        required=False,
                        help="Formato: HH:MM:SS"
                    )
                }
                
                # Busca dados com ordenação por data e hora
                cursor.execute("""
                    SELECT 
                        id as 'id',
                        user_id as 'user_id',
                        data_acesso as 'data_acesso',
                        programa as 'programa',
                        acao as 'acao',
                        time(hora_acesso) as 'hora_acesso'
                    FROM log_acessos 
                    ORDER BY data_acesso DESC, hora_acesso DESC, id DESC
                """)
                
                # Define explicitamente os nomes das colunas
                columns = ['id', 'user_id', 'data_acesso', 'programa', 'acao', 'hora_acesso']
                
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=columns)
                
                # Converte apenas a data_acesso para string se necessário
                if 'data_acesso' in df.columns:
                    df['data_acesso'] = df['data_acesso'].astype(str)
            else:
                # Configura o tipo de cada coluna baseado no tipo do SQLite
                column_config = {}
                for col_info in columns_info:
                    col_name = col_info[1]
                    col_type = col_info[2].upper()
                    
                    # Define a largura da coluna baseada no dicionário COLUMN_WIDTHS
                    column_width = COLUMN_WIDTHS.get(selected_table, {}).get(col_name, 'medium')
                    
                    # Configuração especial para a tabela de usuários
                    if selected_table == "usuarios_tab":
                        if col_name in ["id", "user_id"]:  # Tratamento para colunas numéricas
                            column_config[col_name] = st.column_config.NumberColumn(
                                col_name,
                                width=column_width,
                                required=True,
                                step=1,  # Força números inteiros
                                format="%d"  # Formato de número inteiro
                            )
                        elif col_name == "perfil":
                            column_config[col_name] = st.column_config.SelectboxColumn(
                                "perfil",
                                width=column_width,
                                required=True,
                                options=["adm", "usuario", "Gestor", "master"]
                            )
                        elif col_name == "email":
                            column_config[col_name] = st.column_config.TextColumn(
                                "email",
                                width=column_width,
                                required=True
                            )
                        else:
                            if 'INTEGER' in col_type:
                                column_config[col_name] = st.column_config.NumberColumn(
                                    col_name,
                                    width=column_width,
                                    required=True,
                                )
                            else:
                                column_config[col_name] = st.column_config.TextColumn(
                                    col_name,
                                    width=column_width,
                                    required=True
                                )
                    else:
                        # Configuração padrão para outras tabelas
                        if 'INTEGER' in col_type:
                            column_config[col_name] = st.column_config.NumberColumn(
                                col_name,
                                width=column_width,
                                required=True,
                            )
                        elif 'REAL' in col_type:
                            column_config[col_name] = st.column_config.NumberColumn(
                                col_name,
                                width=column_width,
                                required=True,
                            )
                        else:
                            column_config[col_name] = st.column_config.TextColumn(
                                col_name,
                                width=column_width,
                                required=True
                            )
            
            # Converte para formato editável
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                column_config=column_config,
                hide_index=False,
                key=f"editor_{selected_table}"
            )
            
            # Botão para salvar alterações
            if st.button("Salvar Alterações"):
                try:
                    # Detecta registros novos comparando o tamanho dos DataFrames
                    if len(edited_df) > len(df):
                        # Processa novos registros
                        new_records = edited_df.iloc[len(df):]
                        for _, row in new_records.iterrows():
                            # Remove o índice da linha que é automaticamente adicionado
                            row_values = [row[col] for col in columns]
                            insert_query = f"""
                            INSERT INTO {selected_table} ({', '.join(columns)})
                            VALUES ({', '.join(['?' for _ in columns])})
                            """
                            cursor.execute(insert_query, tuple(row_values))

                    # Atualiza registros existentes
                    for index, row in edited_df.iloc[:len(df)].iterrows():
                        # Obtém o valor da coluna de ID primária (geralmente 'id' ou a primeira coluna)
                        id_column = columns[0]  # Assume que a primeira coluna é o ID
                        if 'id' in columns:
                            id_column = 'id'
                        elif 'you_id' in columns and selected_table == 'youtube_tab':
                            id_column = 'you_id'
                            
                        id_value = row[id_column]
                        
                        # Constrói a query de atualização usando o ID em vez do rowid
                        update_query = f"""
                        UPDATE {selected_table}
                        SET {', '.join(f'{col} = ?' for col in columns if col != id_column)}
                        WHERE {id_column} = ?
                        """
                        
                        # Prepara os valores para a atualização (todos exceto o ID, e depois o ID para o WHERE)
                        update_values = [row[col] for col in columns if col != id_column]
                        update_values.append(id_value)
                        
                        cursor.execute(update_query, tuple(update_values))
                    
                    conn.commit()
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao salvar alterações: {str(e)}")
                    # Adiciona mais detalhes para debug
                    import traceback
                    st.error(f"Detalhes do erro: {traceback.format_exc()}")
            
            # Botão de download - convertendo ponto para vírgula na coluna value
            if not df.empty:
                export_df = edited_df.copy()
                
                # Procura pela coluna que contém 'value' no nome
                value_columns = [col for col in export_df.columns if 'value' in col.lower()]
                
                # Converte os números para string e substitui ponto por vírgula
                for value_col in value_columns:
                    export_df[value_col] = export_df[value_col].apply(lambda x: str(x).replace('.', ',') if pd.notnull(x) else '')
                
                # Alterado para usar UTF-8 em vez de cp1252 para suportar caracteres Unicode
                txt_data = export_df.to_csv(sep='\t', index=False, encoding='utf-8', float_format=None)
                st.download_button(
                    label="Download TXT",
                    data=txt_data.encode('utf-8'),
                    file_name=f"{selected_table}.txt",
                    mime="text/plain"
                )
        
        except Exception as e:
            st.error(f"Erro ao processar dados: {str(e)}")
        
        finally:
            conn.close()

