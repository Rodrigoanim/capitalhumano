# Arquivo: create_forms.py
# Data: 22/02/2025 - 15:12
# Descrição: Script para atualizar atraves de um arquivo .txt
# Tabelas: forms_tab, forms_insumos, forms_resultados, forms_result_sea, forms_setorial, forms_setorial_sea, forms_energetica
# Adaptação para o uso de Discos SSD e a pasta Data para o banco de dados
# Programa roda direto no Python - não usar o streamlit
# Nova coluna - col_len


import sqlite3
import os
import pandas as pd
from tkinter import filedialog, messagebox
import tkinter as tk
import sys


from pathlib import Path
from config import DB_PATH, DATA_DIR  # Adicione esta importação

def clean_string(value):
    """Limpa strings de aspas e apóstrofos extras."""
    if isinstance(value, str):
        return value.replace("'", "").replace('"', "").strip()
    return value

def clean_csv_data(txt_file):
    """Limpa e prepara os dados do TXT tabulado em ANSI."""
    try:
        # Lê o arquivo tabulado em ANSI (cp1252)
        df = pd.read_csv(
            txt_file, 
            index_col=0,
            encoding='cp1252',  # Codificação ANSI/Windows-1252
            sep='\t',          # Separador de tabulação
            quoting=3,         # QUOTE_NONE
            na_filter=False,   # Não converte strings vazias para NaN
            decimal=','        # Define vírgula como separador decimal
        )
        print("Arquivo lido com sucesso usando ANSI e tabulação")
        
        # Remove aspas extras e espaços
        for column in df.columns:
            if df[column].dtype == 'object':
                df[column] = df[column].apply(lambda x: str(x).strip('"\'').strip() if pd.notna(x) else '')
        
        # Debug: mostra as primeiras linhas após limpeza
        print("\nPrimeiras linhas após limpeza:")
        print(df.head())
        
        return df
        
    except Exception as e:
        print(f"Erro ao limpar dados: {str(e)}")
        print(f"Tipo do erro: {type(e)}")
        return None

def format_float_value(value):
    """Converte valor para float, usando padrão brasileiro (vírgula como decimal e ponto como milhar)."""
    try:
        # Se valor for vazio ou None
        if not value and value != 0:
            return 0.0
            
        # Se já for float, retorna diretamente
        if isinstance(value, float):
            return value
            
        # Converte para string e remove espaços
        str_value = str(value).strip()
        
        # Remove pontos de milhar e substitui vírgula por ponto decimal para cálculo
        str_value = str_value.replace('.', '').replace(',', '.')
        
        # Se após limpeza ficar vazio
        if not str_value:
            return 0.0
            
        # Converte para float
        float_value = float(str_value)
        
        return float_value
        
    except Exception as e:
        print(f"Erro ao formatar valor numérico: {value}. Erro: {str(e)}")
        return 0.0

def format_br_number(value):
    """Formata um número float para o padrão brasileiro (vírgula como decimal)."""
    try:
        return f"{float(value)}".replace('.', ',')
    except:
        return '0,0'

def validate_selectbox_data(row):
    """Valida e corrige dados do selectbox."""
    try:
        if row['type_element'] == 'selectbox':
            # Força math_element para '0,0' em selectbox
            row['math_element'] = '0,0'
            
            # Limpa select_element
            if pd.notna(row['select_element']):
                options = row['select_element'].replace('"', '').replace("'", '').strip()
                options_list = [opt.strip() for opt in options.split('|')]
                row['select_element'] = '|'.join(options_list)
            else:
                row['select_element'] = ''
            
            # Limpa str_element
            if pd.notna(row['str_element']):
                str_value = row['str_element'].replace('"', '').replace("'", '').strip()
                row['str_element'] = str_value
            else:
                row['str_element'] = ''
            
            # Força value_element para 0.0
            row['value_element'] = 0.0
            print(f"Valor do selectbox definido como: {format_br_number(row['value_element'])}")
        else:
            # Trata value_element e registra valores problemáticos
            original_value = row['value_element']
            row['value_element'] = format_float_value(original_value)
            
            # Registra conversões para zero que não eram zero originalmente
            if row['value_element'] == 0.0 and str(original_value).strip() not in ['0', '0,0', '']:
                print(f"Aviso: Valor original '{original_value}' foi convertido para '{format_br_number(0.0)}'")
            else:
                print(f"Valor convertido: {format_br_number(row['value_element'])}")
            
        return True, row
    except Exception as e:
        print(f"Erro ao validar selectbox: {str(e)}")
        return False, row

def select_table():
    """Permite ao usuário selecionar a tabela para importação."""
    root = tk.Tk()
    root.title("Seleção de Tabela")
    root.geometry("400x200")
    
    selected_table = tk.StringVar(value=None)
    
    def on_select():
        if selected_table.get():  # Only close if a selection was made
            root.quit()
        else:
            messagebox.showwarning("Aviso", "Por favor, selecione uma tabela")
    
    tk.Label(root, text="Selecione a tabela para importação:", pady=20).pack()
    
    tables = [
        ("Forms Principal", "forms_tab"),
        ("Forms Insumos", "forms_insumos"),
        ("Forms Resultados", "forms_resultados"),
        ("Forms Resultados SEA", "forms_result_sea")
    ]
    
    for text, value in tables:
        tk.Radiobutton(root, text=text, variable=selected_table, value=value).pack()
    
    tk.Button(root, text="Confirmar", command=on_select, pady=10).pack(pady=20)
    
    root.mainloop()
    selected = selected_table.get()
    root.destroy()
    
    return selected if selected else "forms_tab"  # Retorna forms_tab como padrão se nada for selecionado

def confirm_file_selection(txt_file, table_name):
    """Confirma com o usuário se o arquivo selecionado está correto."""
    root = tk.Tk()
    root.withdraw()
    
    # Extrai apenas o nome do arquivo do caminho completo
    file_name = os.path.basename(txt_file)
    
    message = f"""
    ATENÇÃO! Confirme os dados da importação:

    Tabela de destino: {table_name}
    Arquivo selecionado: {file_name}
    Caminho completo: {txt_file}

    Deseja prosseguir com a importação?
    """
    
    return messagebox.askyesno("Confirmação de Importação", message)

def verify_filename(selected_file, table_name):
    """Verifica se o arquivo selecionado corresponde ao padrão esperado para a tabela."""
    # Mapeamento de tabelas para seus arquivos esperados
    expected_files = {
        "forms_tab": "forms_tab.txt",
        "forms_insumos": "forms_insumos.txt",
        "forms_resultados": "forms_resultados.txt",
        "forms_result_sea": "forms_result_sea.txt",
        "usuarios": "usuarios.txt"
    }
    
    # Obtém apenas o nome do arquivo do caminho completo
    filename = os.path.basename(selected_file)
    expected_filename = expected_files.get(table_name)
    
    # Se o arquivo for o padrão, retorna True direto
    if filename.lower() == expected_filename.lower():
        return True
        
    # Se for diferente, mostra mensagem de confirmação com destaque em vermelho
    message = f"""
    ATENÇÃO! O arquivo selecionado não corresponde ao padrão esperado.
    
    \u001b[31mArquivo esperado: {expected_filename}
    Arquivo selecionado: {filename}\u001b[0m
    
    Tem certeza que deseja prosseguir com este arquivo?
    """
    
    # Cria uma janela personalizada para o aviso
    dialog = tk.Toplevel()
    dialog.title("Verificação de Arquivo")
    dialog.geometry("600x400")  # Aumentado para acomodar fontes maiores
    dialog.configure(bg='#ffcccc')  # Fundo vermelho claro
    
    # Centraliza a janela
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    # Adiciona o ícone de aviso e a mensagem com texto em vermelho e fonte maior
    tk.Label(dialog, text="ATENÇÃO!", font=("Arial", 24, "bold"), fg="red", bg='#ffcccc').pack(pady=20)
    tk.Label(dialog, text="O arquivo selecionado não corresponde ao padrão esperado.", 
             wraplength=500, font=("Arial", 16), bg='#ffcccc').pack(pady=10)
    tk.Label(dialog, text=f"Arquivo esperado: {expected_filename}", 
             fg="red", font=("Arial", 20, "bold"), bg='#ffcccc').pack()
    tk.Label(dialog, text=f"Arquivo selecionado: {filename}", 
             fg="red", font=("Arial", 20, "bold"), bg='#ffcccc').pack()
    tk.Label(dialog, text="Tem certeza que deseja prosseguir com este arquivo?", 
             wraplength=500, font=("Arial", 16), bg='#ffcccc').pack(pady=20)
    
    # Botões com fonte maior
    button_frame = tk.Frame(dialog, bg='#ffcccc')
    button_frame.pack(pady=20)
    tk.Button(button_frame, text="Sim", command=lambda: on_yes(), width=10, font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    tk.Button(button_frame, text="Não", command=lambda: on_no(), width=10, font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    
    result = [False]
    
    def on_yes():
        result[0] = True
        dialog.destroy()
        
    def on_no():
        result[0] = False
        dialog.destroy()
    
    # Torna a janela modal
    dialog.transient(dialog.master)
    dialog.grab_set()
    dialog.wait_window()
    
    return result[0]

def select_import_file(table_name):
    """Seleciona e confirma o arquivo para importação."""
    root = tk.Tk()
    root.withdraw()
    
    # Seleção do arquivo
    txt_file = filedialog.askopenfilename(
        title=f"Selecione o arquivo TXT para importar em {table_name}",
        filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")]
    )
    
    if not txt_file:
        root.quit()
        root.destroy()
        return None
    
    # Obtém apenas o nome do arquivo do caminho completo
    filename = os.path.basename(txt_file)
    expected_filename = f"{table_name}.txt"
    
    # Se o arquivo for o padrão, retorna direto sem confirmação
    if filename.lower() == expected_filename.lower():
        root.quit()
        root.destroy()
        return txt_file
        
    # Se for diferente, mostra mensagem de confirmação
    root.deiconify()
    dialog = tk.Toplevel(root)
    dialog.title("Verificação de Arquivo")
    dialog.geometry("600x400")
    dialog.configure(bg='#ffcccc')
    
    # Centraliza a janela
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    
    # Adiciona o ícone de aviso e a mensagem com texto em vermelho e fonte maior
    tk.Label(dialog, text="ATENÇÃO!", font=("Arial", 24, "bold"), fg="red", bg='#ffcccc').pack(pady=20)
    tk.Label(dialog, text="O arquivo selecionado não corresponde ao PADRÃO.", 
             wraplength=500, font=("Arial", 16), bg='#ffcccc').pack(pady=10)
    tk.Label(dialog, text=f"Arquivo esperado: {expected_filename}", 
             fg="red", font=("Arial", 20, "bold"), bg='#ffcccc').pack()
    tk.Label(dialog, text=f"Arquivo selecionado: {filename}", 
             fg="red", font=("Arial", 20, "bold"), bg='#ffcccc').pack()
    tk.Label(dialog, text="Tem certeza que deseja prosseguir com este arquivo?", 
             wraplength=500, font=("Arial", 16), bg='#ffcccc').pack(pady=20)
    
    result = [False]
    dialog_active = True
    
    def on_yes():
        nonlocal dialog_active
        result[0] = True
        dialog_active = False
        root.quit()
        
    def on_no():
        nonlocal dialog_active
        result[0] = False
        dialog_active = False
        root.quit()
    
    # Botões com fonte maior
    button_frame = tk.Frame(dialog, bg='#ffcccc')
    button_frame.pack(pady=20)
    tk.Button(button_frame, text="Sim", command=on_yes, width=10, font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    tk.Button(button_frame, text="Não", command=on_no, width=10, font=("Arial", 14)).pack(side=tk.LEFT, padx=10)
    
    dialog.protocol("WM_DELETE_WINDOW", on_no)  # Tratamento do botão fechar da janela
    dialog.transient(root)
    dialog.grab_set()
    
    root.mainloop()
    
    dialog.destroy()
    root.destroy()
    
    if result[0]:
        return txt_file
    return None

def check_database():
    """Verifica se a pasta data e o banco de dados existem."""
    root = tk.Tk()
    root.withdraw()
    
    # Verifica se o diretório data existe
    if not DATA_DIR.exists():
        messagebox.showerror(
            "Erro",
            "Pasta 'data' não encontrada. O programa não pode continuar.\n"
            "Por favor, crie a pasta 'data' e coloque o arquivo calcpc.db nela."
        )
        sys.exit(1)
        
    # Verifica se o banco existe
    if not DB_PATH.exists():
        messagebox.showerror(
            "Erro",
            "Banco de dados não encontrado.\n"
            "Por favor, verifique se o arquivo calcpc.db está na pasta data."
        )
        sys.exit(1)

def create_database():
    """Cria o banco de dados e a tabela forms_resultados."""
    check_database()  # Verifica pasta data e banco
    
    table_name = "forms_resultados"
    conn = None
    try:
        # Garante que o diretório de dados existe
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ID_element INTEGER PRIMARY KEY AUTOINCREMENT,
                name_element TEXT NOT NULL,
                type_element TEXT NOT NULL,
                math_element TEXT,
                msg_element TEXT,
                value_element REAL,
                select_element TEXT,
                str_element TEXT,
                e_col INTEGER,
                e_row INTEGER,
                user_id INTEGER,
                section TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Resto do processo de importação
        df = clean_csv_data(txt_file)
        if df is None:
            messagebox.showerror("Erro", "Não foi possível ler o arquivo selecionado.")
            return

        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None
                    ))
                    print(f"Inserido value_element: {format_br_number(row_dict['value_element'])}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_insumos():
    """Cria o banco de dados e a tabela forms_insumos."""
    check_database()  # Verifica pasta data e banco
    
    table_name = "forms_insumos"
    conn = None
    try:
        # Garante que o diretório de dados existe
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ID_element INTEGER PRIMARY KEY AUTOINCREMENT,
                name_element TEXT NOT NULL,
                type_element TEXT NOT NULL,
                math_element TEXT,
                msg_element TEXT,
                value_element REAL,
                select_element TEXT,
                str_element TEXT,
                e_col INTEGER,
                e_row INTEGER,
                user_id INTEGER,
                section TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Resto do processo de importação
        df = clean_csv_data(txt_file)
        if df is None:
            messagebox.showerror("Erro", "Não foi possível ler o arquivo selecionado.")
            return

        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None
                    ))
                    print(f"Inserido value_element: {format_br_number(row_dict['value_element'])}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_forms():
    """Cria o banco de dados e a tabela forms_tab."""
    check_database()
    table_name = "forms_tab"
    
    conn = None
    try:
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        
        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela com a coluna col_len
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ID_element INTEGER PRIMARY KEY AUTOINCREMENT,
                name_element TEXT NOT NULL,
                type_element TEXT NOT NULL,
                math_element TEXT,
                msg_element TEXT,
                value_element REAL,
                select_element TEXT,
                str_element TEXT,
                e_col INTEGER,
                e_row INTEGER,
                user_id INTEGER,
                section TEXT,
                col_len TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Lê o arquivo com configurações específicas para incluir col_len
        try:
            df = pd.read_csv(
                txt_file,
                encoding='cp1252',
                sep='\t',
                quoting=3,
                na_filter=False,
                decimal=','
            )
            print("\nColunas encontradas no arquivo:")
            print(df.columns.tolist())
            
            print("\nPrimeiras 10 linhas do arquivo com todas as colunas:")
            pd.set_option('display.max_columns', None)  # Mostra todas as colunas
            pd.set_option('display.width', None)        # Não limita a largura da exibição
            pd.set_option('display.max_colwidth', None) # Mostra conteúdo completo das células
            print(df.head(10))
            
            # Verifica se a coluna col_len existe
            if 'col_len' not in df.columns:
                print("\nAviso: Coluna 'col_len' não encontrada no arquivo.")
                df['col_len'] = ''  # Adiciona coluna vazia se não existir
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler arquivo:\n{str(e)}")
            return

        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section,
                            col_len
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None,
                        str(row_dict.get('col_len', ''))  # Inclui col_len, vazio se não existir
                    ))
                    print(f"Inserido registro com name_element: {row_dict['name_element']}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_usuarios():
    """Cria o banco de dados e a tabela usuarios."""
    check_database()
    table_name = "usuarios"
    conn = None
    try:
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela usuarios com estrutura atualizada incluindo user_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                perfil TEXT NOT NULL,
                empresa TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Lê o arquivo com configurações específicas para usuários
        try:
            df = pd.read_csv(
                txt_file,
                encoding='cp1252',
                sep='\t',
                quoting=3,
                na_filter=False
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler arquivo de usuários:\n{str(e)}")
            return

        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO usuarios (user_id, nome, email, senha, perfil, empresa)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        int(row['user_id']),
                        str(row['nome']).strip(),
                        str(row['email']).strip(),
                        str(row['senha']).strip(),
                        str(row['perfil']).strip(),
                        str(row['empresa']).strip() if 'empresa' in row else None
                    ))
                    print(f"Usuário inserido: {row['nome']}")
                except Exception as e:
                    print(f"Erro ao inserir usuário: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de usuários processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_result_sea():
    """Importa dados para a tabela forms_result_sea."""
    check_database()
    table_name = "forms_result_sea"
    
    conn = None
    try:
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja limpar os dados existentes?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {table_name}")
                conn.commit()
                print(f"Dados da tabela {table_name} removidos.")
            else:
                print("Importação será realizada mantendo dados existentes.")
        
        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Resto do processo de importação
        df = clean_csv_data(txt_file)
        if df is None:
            messagebox.showerror("Erro", "Não foi possível ler o arquivo selecionado.")
            return

        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None
                    ))
                    print(f"Inserido value_element: {format_br_number(row_dict['value_element'])}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_setorial():
    """Cria o banco de dados e a tabela forms_setorial."""
    check_database()
    table_name = "forms_setorial"
    
    conn = None
    try:
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ID_element INTEGER PRIMARY KEY AUTOINCREMENT,
                name_element TEXT NOT NULL,
                type_element TEXT NOT NULL,
                math_element TEXT,
                msg_element TEXT,
                value_element REAL,
                select_element TEXT,
                str_element TEXT,
                e_col INTEGER,
                e_row INTEGER,
                user_id INTEGER,
                section TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Resto do processo de importação
        df = clean_csv_data(txt_file)
        if df is None:
            messagebox.showerror("Erro", "Não foi possível ler o arquivo selecionado.")
            return

        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None
                    ))
                    print(f"Inserido value_element: {format_br_number(row_dict['value_element'])}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_setorial_sea():
    """Cria o banco de dados e a tabela forms_setorial_sea."""
    check_database()
    table_name = "forms_setorial_sea"
    
    print(f"\nIniciando importação para tabela: {table_name}")  # Debug
    
    conn = None
    try:
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ID_element INTEGER PRIMARY KEY AUTOINCREMENT,
                name_element TEXT NOT NULL,
                type_element TEXT NOT NULL,
                math_element TEXT,
                msg_element TEXT,
                value_element REAL,
                select_element TEXT,
                str_element TEXT,
                e_col INTEGER,
                e_row INTEGER,
                user_id INTEGER,
                section TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Resto do processo de importação
        df = clean_csv_data(txt_file)
        if df is None:
            messagebox.showerror("Erro", "Não foi possível ler o arquivo selecionado.")
            return

        print("\nPrimeiras 5 linhas do arquivo:")  # Debug
        print(df.head())
        print("\nColunas do arquivo:")  # Debug
        print(df.columns.tolist())
        
        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                print(f"\nProcessando linha {index}:")  # Debug
                print(f"name_element: {row_dict.get('name_element')}")
                print(f"type_element: {row_dict.get('type_element')}")
                print(f"value_element: {row_dict.get('value_element')}")
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None
                    ))
                    print(f"Inserido value_element: {format_br_number(row_dict['value_element'])}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

def create_database_energetica():
    """Cria o banco de dados e a tabela forms_energetica."""
    check_database()
    table_name = "forms_energetica"
    
    print(f"\nIniciando importação para tabela: {table_name}")  # Debug
    
    conn = None
    try:
        # Verifica banco existente
        if DB_PATH.exists():
            root = tk.Tk()
            root.withdraw()
            if messagebox.askyesno("Confirmação", 
                f"A tabela {table_name} já existe. Deseja apagá-la e criar uma nova?"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.commit()
                print(f"Tabela {table_name} removida para recriação.")
            else:
                print("Operação cancelada pelo usuário.")
                return
        else:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        if not conn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

        # Cria tabela
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ID_element INTEGER PRIMARY KEY AUTOINCREMENT,
                name_element TEXT NOT NULL,
                type_element TEXT NOT NULL,
                math_element TEXT,
                msg_element TEXT,
                value_element REAL,
                select_element TEXT,
                str_element TEXT,
                e_col INTEGER,
                e_row INTEGER,
                user_id INTEGER,
                section TEXT
            );
        """)

        # Usa a nova função de seleção de arquivo
        txt_file = select_import_file(table_name)
        if not txt_file:
            return

        # Resto do processo de importação
        df = clean_csv_data(txt_file)
        if df is None:
            messagebox.showerror("Erro", "Não foi possível ler o arquivo selecionado.")
            return

        print("\nPrimeiras 5 linhas do arquivo:")  # Debug
        print(df.head())
        print("\nColunas do arquivo:")  # Debug
        print(df.columns.tolist())
        
        # Confirmação final antes de iniciar a importação
        if messagebox.askyesno("Confirmação Final",
            f"Foram encontradas {len(df)} linhas para importar.\n"
            "Deseja iniciar a importação?"):
            
            # Processa cada linha
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                print(f"\nProcessando linha {index}:")  # Debug
                print(f"name_element: {row_dict.get('name_element')}")
                print(f"type_element: {row_dict.get('type_element')}")
                print(f"value_element: {row_dict.get('value_element')}")
                
                # Valida dados do selectbox
                is_valid, row_dict = validate_selectbox_data(row_dict)
                if not is_valid:
                    continue
                
                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (
                            name_element, type_element, math_element, 
                            msg_element, value_element, select_element,
                            str_element, e_col, e_row, user_id, section
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row_dict['name_element']),
                        str(row_dict['type_element']),
                        str(row_dict['math_element']),
                        str(row_dict['msg_element']),
                        row_dict['value_element'],
                        str(row_dict['select_element']),
                        str(row_dict['str_element']),
                        int(float(format_float_value(row_dict['e_col']))),
                        int(float(format_float_value(row_dict['e_row']))),
                        int(row_dict['user_id']) if pd.notna(row_dict.get('user_id')) else None,
                        str(row_dict['section']) if pd.notna(row_dict.get('section')) else None
                    ))
                    print(f"Inserido value_element: {format_br_number(row_dict['value_element'])}")
                except Exception as e:
                    print(f"Erro ao inserir linha na tabela {table_name}: {str(e)}")
                    continue

            conn.commit()
            messagebox.showinfo("Sucesso", 
                f"Dados importados com sucesso para a tabela '{table_name}'\n"
                f"Total de registros processados: {len(df)}")
        else:
            print("Importação cancelada pelo usuário.")

    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro durante a importação:\n{str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Verifica pasta data e banco antes de mostrar o menu
    check_database()
    
    while True:
        print("\nMENU DE OPÇÕES:")
        print("1 - Criar Tabela forms_resultados")
        print("2 - Criar Tabela forms_insumos")
        print("3 - Criar Tabela forms_tab")
        print("4 - Criar Tabela usuarios")
        print("5 - Criar Tabela forms_result_sea")
        print("6 - Criar Tabela forms_setorial")
        print("7 - Criar Tabela forms_setorial_sea")
        print("8 - Criar Tabela forms_energetica")
        print("0 - Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == "1":
            create_database()
        elif opcao == "2":
            create_database_insumos()
        elif opcao == "3":
            create_database_forms()
        elif opcao == "4":
            create_database_usuarios()
        elif opcao == "5":
            create_database_result_sea()
        elif opcao == "6":
            create_database_setorial()
        elif opcao == "7":
            create_database_setorial_sea()
        elif opcao == "8":
            create_database_energetica()
        elif opcao == "0":
            print("Programa encerrado.")
            break
        else:
            print("Opção inválida!")
