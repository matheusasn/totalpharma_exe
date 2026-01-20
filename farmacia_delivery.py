import customtkinter as ctk
import sqlite3
from tkinter import messagebox, filedialog
from datetime import datetime, timedelta
import os
import sys
import textwrap
import csv 
import webbrowser 
import urllib.parse 
import shutil
import unicodedata

# Bibliotecas de impressão do Windows
try:
    import win32print
    import win32ui 
    import win32con
    import ctypes
    WINDOWS_PRINT_AVAILABLE = True
except ImportError:
    WINDOWS_PRINT_AVAILABLE = False
    print("AVISO: Bibliotecas de impressão Windows não disponíveis")

# -------------- CONFIGURAÇÕES --------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
DDD_PADRAO = "83" 
LARGURA_PAPEL = 42 

def configurar_identidade_windows():
    try:
        myappid = 'totalpharma.delivery.pdv.v10' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except: 
        pass

if WINDOWS_PRINT_AVAILABLE:
    configurar_identidade_windows()

def get_app_path():
    """Retorna o caminho do banco - verifica se há config de rede"""
    # Verifica se existe arquivo de configuração apontando para rede
    try:
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        config_file = os.path.join(app_dir, "config_rede.txt")
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                caminho_rede = f.read().strip()
                if caminho_rede and os.path.exists(caminho_rede):
                    print(f"[REDE] Usando banco em: {caminho_rede}")
                    return caminho_rede
                else:
                    print(f"[AVISO] Caminho de rede não acessível: {caminho_rede}")
    except Exception as e:
        print(f"[ERRO] Ao ler config de rede: {e}")
    
    # Fallback: usa pasta local
    app_data = os.getenv('APPDATA')
    pasta_app = os.path.join(app_data, "TotalPharma")
    if not os.path.exists(pasta_app):
        try: 
            os.makedirs(pasta_app)
        except: 
            pass
    print(f"[LOCAL] Usando banco em: {pasta_app}")
    return pasta_app

def init_db():
    try:
        pasta_app = get_app_path()
        db_path = os.path.join(pasta_app, "dados_farmacia.db")
        
        # Conexão com timeout maior para suportar rede
        conn = sqlite3.connect(db_path, timeout=30)
        cursor = conn.cursor()
        
        # Habilita WAL mode para melhor performance em rede
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                telefone TEXT PRIMARY KEY,
                nome TEXT,
                rua TEXT,
                numero TEXT,
                bairro TEXT,
                referencia TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico_enderecos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefone_cliente TEXT,
                rua TEXT,
                numero TEXT,
                bairro TEXT,
                referencia TEXT,
                ultimo_uso DATE,
                FOREIGN KEY(telefone_cliente) REFERENCES clientes(telefone)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                cliente_tel TEXT,
                entregador TEXT,
                valor_total REAL,
                metodo_pagamento TEXT, 
                detalhes_pagamento TEXT,
                FOREIGN KEY(cliente_tel) REFERENCES clientes(telefone)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lembretes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_tel TEXT,
                medicamento TEXT,
                data_aviso TEXT,
                status TEXT,
                FOREIGN KEY(cliente_tel) REFERENCES clientes(telefone)
            )
        """)
        
        # Migrações de colunas
        cols_cli = ["rua", "numero", "bairro", "referencia"]
        for c in cols_cli:
            try: 
                cursor.execute(f"ALTER TABLE clientes ADD COLUMN {c} TEXT")
            except: 
                pass
            
        try: 
            cursor.execute("ALTER TABLE pedidos ADD COLUMN metodo_pagamento TEXT")
        except: 
            pass
        
        try: 
            cursor.execute("ALTER TABLE pedidos ADD COLUMN detalhes_pagamento TEXT")
        except: 
            pass

        conn.commit()
        conn.close()
        return db_path
    except Exception as e:
        print(f"[ERRO] Inicialização do banco: {e}")
        return "dados_farmacia.db"

DB_PATH = init_db()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TotalPharma - PDV Profissional V10")
        self.geometry("1000x920")
        
        # Ícone
        try:
            if getattr(sys, 'frozen', False):
                app_path = os.path.dirname(sys.executable)
            else:
                app_path = os.path.dirname(os.path.abspath(__file__))
            caminho_icone = os.path.join(app_path, "farmacia.ico")
            if os.path.exists(caminho_icone):
                self.iconbitmap(caminho_icone)
                self.wm_iconbitmap(caminho_icone)
        except: 
            pass 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.criar_coluna_cliente()
        self.criar_coluna_pagamento()
        
        self.limpar_tela()
        self.verificar_conexao_rede()
        self.after(1000, self.verificar_avisos_hoje_silencioso)
        self.atualizar_painel_status()

    def verificar_conexao_rede(self):
        """Atualiza o título indicando se está em rede ou local"""
        if "\\\\" in DB_PATH or DB_PATH.startswith("//"):
            self.title("TotalPharma - PDV V10 [🌐 REDE]")
            self.modo_rede = True
        else:
            self.title("TotalPharma - PDV V10 [💻 LOCAL]")
            self.modo_rede = False

    def criar_coluna_cliente(self):
        frame_cli = ctk.CTkFrame(self)
        frame_cli.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(frame_cli, text="DADOS DO CLIENTE", font=("Arial", 16, "bold"), text_color="#3B8ED0").pack(pady=(15,10))

        ctk.CTkLabel(frame_cli, text="Telefone (Tab para buscar):").pack(anchor="w", padx=15)
        
        frame_tel = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_tel.pack(fill="x", padx=15, pady=(0, 10))
        
        self.entry_tel = ctk.CTkEntry(frame_tel, placeholder_text="Somente números")
        self.entry_tel.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_tel.bind("<FocusOut>", self.buscar_cliente) 
        self.entry_tel.bind("<Return>", self.buscar_cliente)
        
        btn_lupa = ctk.CTkButton(frame_tel, text="🔍", width=40, command=self.buscar_cliente, fg_color="#333", text_color="white")
        btn_lupa.pack(side="right")

        ctk.CTkLabel(frame_cli, text="Nome do Cliente:").pack(anchor="w", padx=15)
        self.entry_nome = ctk.CTkEntry(frame_cli)
        self.entry_nome.pack(fill="x", padx=15, pady=(0, 10))

        # --- Botão Histórico ---
        frame_lbl_end = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_lbl_end.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkLabel(frame_lbl_end, text="Endereço de Entrega:", text_color="#3B8ED0", font=("Arial", 13, "bold")).pack(side="left")
        
        self.btn_historico = ctk.CTkButton(frame_lbl_end, text="📍 Histórico", width=80, height=20, 
                                           fg_color="#F39C12", text_color="white", font=("Arial", 10, "bold"), command=self.abrir_historico_enderecos)
        self.btn_historico.pack(side="right")
        
        frame_end_1 = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_end_1.pack(fill="x", padx=15)
        self.entry_rua = ctk.CTkEntry(frame_end_1, placeholder_text="Nome da Rua")
        self.entry_rua.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_num = ctk.CTkEntry(frame_end_1, placeholder_text="Nº", width=60)
        self.entry_num.pack(side="right")

        ctk.CTkLabel(frame_cli, text="Bairro:").pack(anchor="w", padx=15, pady=(5,0))
        self.entry_bairro = ctk.CTkEntry(frame_cli, placeholder_text="Bairro")
        self.entry_bairro.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(frame_cli, text="Ponto de Referência:").pack(anchor="w", padx=15, pady=(5,0))
        self.entry_ref = ctk.CTkEntry(frame_cli, placeholder_text="Ex: Ao lado da padaria")
        self.entry_ref.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(frame_cli, text="Selecione o Entregador:").pack(anchor="w", padx=15, pady=(5,0))
        
        self.var_entregador = ctk.StringVar(value="Entregador A")
        frame_radio = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_radio.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkRadioButton(frame_radio, text="Entregador A", variable=self.var_entregador, value="Entregador A").pack(anchor="w", pady=2)
        ctk.CTkRadioButton(frame_radio, text="Entregador B", variable=self.var_entregador, value="Entregador B").pack(anchor="w", pady=2)
        ctk.CTkRadioButton(frame_radio, text="Moto Extra", variable=self.var_entregador, value="Moto Extra/App").pack(anchor="w", pady=2)

        frame_botoes_cli = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_botoes_cli.pack(fill="x", padx=15, pady=(20, 10))
        
        self.btn_salvar_cli = ctk.CTkButton(frame_botoes_cli, text="💾 SALVAR", command=self.salvar_apenas_cliente, fg_color="#2980B9", text_color="white", width=100)
        self.btn_salvar_cli.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.btn_print_end = ctk.CTkButton(frame_botoes_cli, text="🖨️ ETIQUETA", command=self.imprimir_apenas_endereco, fg_color="#E67E22", text_color="white", width=100)
        self.btn_print_end.pack(side="right", expand=True, fill="x", padx=(5, 0))

    def criar_coluna_pagamento(self):
        frame_pag = ctk.CTkFrame(self)
        frame_pag.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame_pag, text="PAGAMENTO", font=("Arial", 16, "bold"), text_color="#2CC985").pack(pady=(15,10))

        # --- Valores do Pedido ---
        frame_vals = ctk.CTkFrame(frame_pag, fg_color="transparent")
        frame_vals.pack(fill="x", padx=20)
        
        ctk.CTkLabel(frame_vals, text="Produtos (R$):").grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkLabel(frame_vals, text="Taxa (R$):").grid(row=0, column=1, padx=5, sticky="w")
        
        self.entry_val = ctk.CTkEntry(frame_vals, placeholder_text="0.00", font=("Arial", 14))
        self.entry_val.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="ew")
        self.entry_val.bind("<FocusOut>", self.atualizar_totais)
        
        self.entry_taxa = ctk.CTkEntry(frame_vals, placeholder_text="0.00")
        self.entry_taxa.grid(row=1, column=1, padx=5, pady=(0, 10), sticky="ew")
        self.entry_taxa.bind("<FocusOut>", self.atualizar_totais)
        
        frame_vals.grid_columnconfigure(0, weight=1)
        frame_vals.grid_columnconfigure(1, weight=1)

        self.lbl_total = ctk.CTkLabel(frame_pag, text="TOTAL: R$ 0.00", font=("Arial", 28, "bold"))
        self.lbl_total.pack(pady=5)
        
        ctk.CTkFrame(frame_pag, height=2, fg_color="gray").pack(fill="x", padx=20, pady=5)

        # ==========================================================
        # CAIXA DE PAGAMENTO
        # ==========================================================
        self.frame_container_pagamentos = ctk.CTkFrame(frame_pag, fg_color="transparent")
        self.frame_container_pagamentos.pack(fill="x", padx=10, pady=5)

        self.chk_pagamento_duplo = ctk.CTkCheckBox(self.frame_container_pagamentos, text="Pagamento Misto (2 Formas)", command=self.toggle_pagamento_duplo)
        self.chk_pagamento_duplo.pack(pady=5)

        # Pagamento 1
        self.frame_pag1 = ctk.CTkFrame(self.frame_container_pagamentos, fg_color="transparent")
        self.frame_pag1.pack(fill="x", padx=10)
        
        self.combo_pag1 = ctk.CTkComboBox(self.frame_pag1, values=["Dinheiro", "Pix", "Cartão"], command=self.mudou_forma_pag1, width=110)
        self.combo_pag1.pack(side="left", padx=(0,5))
        self.combo_pag1.set("Dinheiro")
        
        self.combo_parcelas1 = ctk.CTkComboBox(self.frame_pag1, values=[f"{x}x" for x in range(1, 13)], width=60)
        
        self.entry_val_pag1 = ctk.CTkEntry(self.frame_pag1, placeholder_text="Valor 1", width=90)
        self.entry_val_pag1.pack(side="right")
        self.entry_val_pag1.bind("<KeyRelease>", self.calcular_troco_dinamico)

        # Pagamento 2
        self.frame_pag2 = ctk.CTkFrame(self.frame_container_pagamentos, fg_color="transparent")

        self.combo_pag2 = ctk.CTkComboBox(self.frame_pag2, values=["Dinheiro", "Pix", "Cartão"], command=self.mudou_forma_pag2, width=110)
        self.combo_pag2.pack(side="left", padx=(0,5))
        self.combo_pag2.set("Cartão")
        
        self.combo_parcelas2 = ctk.CTkComboBox(self.frame_pag2, values=[f"{x}x" for x in range(1, 13)], width=60)
        
        self.entry_val_pag2 = ctk.CTkEntry(self.frame_pag2, placeholder_text="Valor 2", width=90)
        self.entry_val_pag2.pack(side="right")
        self.entry_val_pag2.bind("<FocusIn>", self.auto_completar_restante)

        # Troco
        self.frame_troco = ctk.CTkFrame(self.frame_container_pagamentos, fg_color="transparent")
        self.frame_troco.pack(fill="x", padx=10, pady=(10,0))
        
        ctk.CTkLabel(self.frame_troco, text="Valor Entregue (Troco):").pack(anchor="w")
        self.entry_troco = ctk.CTkEntry(self.frame_troco, placeholder_text="Dinheiro entregue")
        self.entry_troco.pack(fill="x")
        self.entry_troco.bind("<KeyRelease>", self.calcular_troco_dinamico)

        self.lbl_troco = ctk.CTkLabel(self.frame_container_pagamentos, text="Troco: R$ 0.00", text_color="#F1C40F", font=("Arial", 18, "bold"))
        self.lbl_troco.pack(pady=5)

        # --- ITENS FIXOS ---
        self.frame_fidelidade = ctk.CTkFrame(frame_pag, fg_color="#333333")
        self.frame_fidelidade.pack(fill="x", padx=20, pady=5)
        self.chk_lembrete = ctk.CTkCheckBox(self.frame_fidelidade, text="Agendar Lembrete (Remédio Controlado)", command=self.toggle_lembrete)
        self.chk_lembrete.pack(pady=5, padx=10, anchor="w")
        self.entry_med_nome = ctk.CTkEntry(self.frame_fidelidade, placeholder_text="Nome do Remédio")
        self.entry_dias_duracao = ctk.CTkEntry(self.frame_fidelidade, placeholder_text="Dura quantos dias?", width=120)

        # Botão IMPRIMIR
        self.btn_imprimir = ctk.CTkButton(frame_pag, text="✅ SALVAR E IMPRIMIR", command=self.finalizar, height=50, fg_color="#2CC985", text_color="black", font=("Arial", 15, "bold"))
        self.btn_imprimir.pack(fill="x", padx=20, pady=(15, 10))
        
        # --- BOTÕES DE AÇÃO ---
        frame_botoes = ctk.CTkFrame(frame_pag, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20)
        
        self.btn_limpar = ctk.CTkButton(frame_botoes, text="LIMPAR", command=self.limpar_tela, fg_color="#C0392B", text_color="white", width=70)
        self.btn_limpar.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_relatorio = ctk.CTkButton(frame_botoes, text="📊 HISTÓRICO", command=self.consultar_historico_entregas, fg_color="#555", text_color="white", width=70)
        self.btn_relatorio.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        self.btn_alertas = ctk.CTkButton(frame_botoes, text="🔔 HOJE", command=self.ver_alertas_recompra, fg_color="#555", text_color="white", width=70)
        self.btn_alertas.pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        self.btn_futuros = ctk.CTkButton(frame_botoes, text="📅 FUTUROS", command=self.listar_todos_agendamentos, fg_color="#34495E", text_color="white", width=70)
        self.btn_futuros.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # --- GESTÃO ---
        frame_gestao = ctk.CTkFrame(frame_pag, fg_color="transparent")
        frame_gestao.pack(fill="x", padx=20, pady=(10, 5))
        
        self.btn_backup = ctk.CTkButton(frame_gestao, text="💾 BACKUP", command=self.fazer_backup_seguranca, fg_color="#8E44AD", text_color="white", width=80)
        self.btn_backup.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        self.btn_clientes = ctk.CTkButton(frame_gestao, text="👥 CLIENTES", command=self.abrir_gestao_clientes, fg_color="#16A085", text_color="white", width=80)
        self.btn_clientes.pack(side="left", expand=True, fill="x", padx=(5, 5))
        
        self.btn_diagnostico = ctk.CTkButton(frame_gestao, text="🔧 DIAGNÓSTICO", command=self.diagnosticar_banco, fg_color="#E74C3C", text_color="white", width=80)
        self.btn_diagnostico.pack(side="right", expand=True, fill="x", padx=(5, 0))

        # --- PAINEL DE STATUS DO DIA ---
        self.frame_status = ctk.CTkFrame(frame_pag, fg_color="#1a1a2e")
        self.frame_status.pack(fill="x", padx=20, pady=(10, 20))

        ctk.CTkLabel(self.frame_status, text="📊 ENTREGAS HOJE", font=("Arial", 12, "bold"), 
                     text_color="#3B8ED0").pack(pady=(10,5))

        self.lbl_status_total = ctk.CTkLabel(self.frame_status, text="Total: 0 entregas | R$ 0.00", 
                                              font=("Arial", 11))
        self.lbl_status_total.pack()

        self.lbl_status_entregadores = ctk.CTkLabel(self.frame_status, text="", 
                                                     font=("Arial", 10), text_color="#BDC3C7")
        self.lbl_status_entregadores.pack(pady=(0,10))

    # ================== DIAGNÓSTICO DO BANCO ==================
    def diagnosticar_banco(self):
        """Verifica integridade do banco e mostra estatísticas"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            # Verifica integridade
            cursor.execute("PRAGMA integrity_check")
            integridade = cursor.fetchone()[0]
            
            # Conta registros
            cursor.execute("SELECT COUNT(*) FROM clientes")
            qtd_clientes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM pedidos")
            qtd_pedidos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM lembretes")
            qtd_lembretes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM historico_enderecos")
            qtd_enderecos = cursor.fetchone()[0]
            
            conn.close()
            
            # Tamanho do arquivo
            tamanho_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
            
            # Verifica modo de conexão
            modo = "🌐 REDE" if ("\\\\" in DB_PATH or DB_PATH.startswith("//")) else "💻 LOCAL"
            
            msg = f"""
═══════════════════════════════
   DIAGNÓSTICO DO BANCO V10
═══════════════════════════════

📁 Caminho:
{DB_PATH}

📊 Tamanho: {tamanho_mb:.2f} MB
🔌 Modo: {modo}

═══════════════════════════════
         REGISTROS
═══════════════════════════════
👥 Clientes: {qtd_clientes}
📦 Pedidos: {qtd_pedidos}
🔔 Lembretes: {qtd_lembretes}
📍 Endereços: {qtd_enderecos}

═══════════════════════════════
      INTEGRIDADE
═══════════════════════════════
🔍 Status: {integridade.upper()}
"""
            
            if integridade != "ok":
                msg += "\n\n⚠️ BANCO CORROMPIDO!\nFaça backup e execute VACUUM."
                messagebox.showwarning("Diagnóstico - ATENÇÃO", msg)
            else:
                msg += "\n✅ Banco saudável!"
                messagebox.showinfo("Diagnóstico", msg)
                
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no diagnóstico:\n{e}")

    # ================== PAINEL DE STATUS ==================
    def atualizar_painel_status(self):
        """Atualiza o painel de status com entregas do dia"""
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            # Total do dia
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(valor_total), 0) FROM pedidos WHERE data = ?", (hoje,))
            total_entregas, faturamento = cursor.fetchone()
            
            # Por entregador
            cursor.execute("""
                SELECT entregador, COUNT(*) 
                FROM pedidos 
                WHERE data = ? 
                GROUP BY entregador 
                ORDER BY COUNT(*) DESC
            """, (hoje,))
            por_entregador = cursor.fetchall()
            conn.close()
            
            # Atualiza labels
            self.lbl_status_total.configure(
                text=f"Total: {total_entregas} entregas | R$ {faturamento:.2f}"
            )
            
            if por_entregador:
                texto_entregadores = " | ".join([f"{nome}: {qtd}" for nome, qtd in por_entregador])
            else:
                texto_entregadores = "Nenhuma entrega ainda"
                
            self.lbl_status_entregadores.configure(text=texto_entregadores)
            
        except Exception as e:
            self.lbl_status_total.configure(text="Erro ao carregar")
            print(f"[ERRO] Atualizar painel: {e}")

    # ================== HISTÓRICO DE ENTREGAS POR PERÍODO ==================
    def consultar_historico_entregas(self):
        """Consulta entregas por período com filtros"""
        top = ctk.CTkToplevel(self)
        top.title("Histórico de Entregas")
        top.geometry("850x700")
        top.attributes("-topmost", True)
        top.lift()
        top.focus_force()
        top.grab_set()
        
        # --- FILTROS ---
        frame_filtros = ctk.CTkFrame(top, fg_color="#1a1a2e")
        frame_filtros.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(frame_filtros, text="📅 FILTRAR POR PERÍODO", 
                     font=("Arial", 14, "bold"), text_color="#3B8ED0").grid(row=0, column=0, columnspan=6, pady=(10,15))
        
        # Data inicial
        ctk.CTkLabel(frame_filtros, text="De:").grid(row=1, column=0, padx=(15,5), pady=10)
        entry_data_ini = ctk.CTkEntry(frame_filtros, placeholder_text="dd/mm/aaaa", width=100)
        entry_data_ini.grid(row=1, column=1, padx=5)
        data_ini_padrao = (datetime.now() - timedelta(days=7)).strftime("%d/%m/%Y")
        entry_data_ini.insert(0, data_ini_padrao)
        
        # Data final
        ctk.CTkLabel(frame_filtros, text="Até:").grid(row=1, column=2, padx=(15,5))
        entry_data_fim = ctk.CTkEntry(frame_filtros, placeholder_text="dd/mm/aaaa", width=100)
        entry_data_fim.grid(row=1, column=3, padx=5)
        entry_data_fim.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        # Filtro por entregador
        ctk.CTkLabel(frame_filtros, text="Entregador:").grid(row=1, column=4, padx=(15,5))
        combo_entregador = ctk.CTkComboBox(frame_filtros, values=["Todos", "Entregador A", "Entregador B", "Moto Extra/App"], width=130)
        combo_entregador.grid(row=1, column=5, padx=(5,15))
        combo_entregador.set("Todos")
        
        # Atalhos de período
        frame_atalhos = ctk.CTkFrame(frame_filtros, fg_color="transparent")
        frame_atalhos.grid(row=2, column=0, columnspan=6, pady=(10,5))
        
        def definir_periodo(dias):
            entry_data_ini.delete(0, "end")
            entry_data_fim.delete(0, "end")
            entry_data_fim.insert(0, datetime.now().strftime("%d/%m/%Y"))
            if dias == 0:
                entry_data_ini.insert(0, datetime.now().strftime("%d/%m/%Y"))
            else:
                entry_data_ini.insert(0, (datetime.now() - timedelta(days=dias)).strftime("%d/%m/%Y"))
            executar_busca()
        
        ctk.CTkButton(frame_atalhos, text="Hoje", width=60, fg_color="#444", text_color="white",
                      command=lambda: definir_periodo(0)).pack(side="left", padx=3)
        ctk.CTkButton(frame_atalhos, text="7 dias", width=60, fg_color="#444", text_color="white",
                      command=lambda: definir_periodo(7)).pack(side="left", padx=3)
        ctk.CTkButton(frame_atalhos, text="15 dias", width=60, fg_color="#444", text_color="white",
                      command=lambda: definir_periodo(15)).pack(side="left", padx=3)
        ctk.CTkButton(frame_atalhos, text="30 dias", width=60, fg_color="#444", text_color="white",
                      command=lambda: definir_periodo(30)).pack(side="left", padx=3)
        ctk.CTkButton(frame_atalhos, text="60 dias", width=60, fg_color="#444", text_color="white",
                      command=lambda: definir_periodo(60)).pack(side="left", padx=3)
        
        # Botão buscar
        btn_buscar = ctk.CTkButton(frame_filtros, text="🔍 BUSCAR", width=100, fg_color="#2CC985", 
                                    text_color="white", font=("Arial", 12, "bold"),
                                    command=lambda: executar_busca())
        btn_buscar.grid(row=3, column=0, columnspan=6, pady=15)
        
        # --- RESUMO ---
        frame_resumo = ctk.CTkFrame(top, fg_color="#2C3E50")
        frame_resumo.pack(fill="x", padx=15, pady=(0,10))
        
        lbl_resumo_total = ctk.CTkLabel(frame_resumo, text="Total: 0 entregas | R$ 0.00", 
                                         font=("Arial", 16, "bold"))
        lbl_resumo_total.pack(pady=10)
        
        lbl_resumo_entregadores = ctk.CTkLabel(frame_resumo, text="", font=("Arial", 11), 
                                                text_color="#BDC3C7")
        lbl_resumo_entregadores.pack(pady=(0,10))
        
        # --- LISTA DE ENTREGAS ---
        ctk.CTkLabel(top, text="Detalhes dos Pedidos:", font=("Arial", 12, "bold")).pack(anchor="w", padx=15)
        
        scroll = ctk.CTkScrollableFrame(top, height=280)
        scroll.pack(fill="both", expand=True, padx=15, pady=(5,10))
        
        # --- BOTÃO EXPORTAR ---
        btn_exportar = ctk.CTkButton(top, text="📥 EXPORTAR PERÍODO (CSV)", fg_color="#8E44AD", 
                                      text_color="white", command=lambda: exportar_periodo())
        btn_exportar.pack(pady=(5,15))
        
        # Variável para guardar os dados da busca atual
        dados_busca_atual = []
        
        def converter_data(data_str):
            """Converte dd/mm/aaaa para aaaa-mm-dd"""
            try:
                partes = data_str.strip().split("/")
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
            except:
                return None
        
        def executar_busca():
            nonlocal dados_busca_atual
            
            # Limpa lista anterior
            for widget in scroll.winfo_children():
                widget.destroy()
            
            # Converte datas
            data_ini = converter_data(entry_data_ini.get())
            data_fim = converter_data(entry_data_fim.get())
            
            if not data_ini or not data_fim:
                messagebox.showwarning("Erro", "Formato de data inválido.\nUse: dd/mm/aaaa")
                return
            
            entregador_filtro = combo_entregador.get()
            
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                cursor = conn.cursor()
                
                # Query base
                if entregador_filtro == "Todos":
                    cursor.execute("""
                        SELECT p.id, p.data, c.nome, c.telefone, p.entregador, 
                               p.valor_total, p.metodo_pagamento
                        FROM pedidos p
                        LEFT JOIN clientes c ON p.cliente_tel = c.telefone
                        WHERE p.data BETWEEN ? AND ?
                        ORDER BY p.data DESC, p.id DESC
                    """, (data_ini, data_fim))
                else:
                    cursor.execute("""
                        SELECT p.id, p.data, c.nome, c.telefone, p.entregador, 
                               p.valor_total, p.metodo_pagamento
                        FROM pedidos p
                        LEFT JOIN clientes c ON p.cliente_tel = c.telefone
                        WHERE p.data BETWEEN ? AND ? AND p.entregador = ?
                        ORDER BY p.data DESC, p.id DESC
                    """, (data_ini, data_fim, entregador_filtro))
                
                pedidos = cursor.fetchall()
                dados_busca_atual = pedidos
                
                # Resumo por entregador
                if entregador_filtro == "Todos":
                    cursor.execute("""
                        SELECT entregador, COUNT(*), SUM(valor_total)
                        FROM pedidos
                        WHERE data BETWEEN ? AND ?
                        GROUP BY entregador
                    """, (data_ini, data_fim))
                else:
                    cursor.execute("""
                        SELECT entregador, COUNT(*), SUM(valor_total)
                        FROM pedidos
                        WHERE data BETWEEN ? AND ? AND entregador = ?
                        GROUP BY entregador
                    """, (data_ini, data_fim, entregador_filtro))
                
                resumo_entregadores = cursor.fetchall()
                conn.close()
                
                # Calcula totais
                total_entregas = len(pedidos)
                total_valor = sum([p[5] for p in pedidos if p[5]]) if pedidos else 0
                
                # Atualiza resumo
                lbl_resumo_total.configure(text=f"Total: {total_entregas} entregas | R$ {total_valor:.2f}")
                
                if resumo_entregadores:
                    texto_ent = " | ".join([f"{e[0]}: {e[1]} (R$ {e[2] or 0:.2f})" for e in resumo_entregadores])
                    lbl_resumo_entregadores.configure(text=texto_ent)
                else:
                    lbl_resumo_entregadores.configure(text="Nenhuma entrega no período")
                
                # Popula lista
                if not pedidos:
                    ctk.CTkLabel(scroll, text="Nenhuma entrega encontrada no período.", 
                                 text_color="#888").pack(pady=20)
                    return
                
                data_anterior = None
                for pid, data, cliente, telefone, entregador, valor, metodo in pedidos:
                    # Separador por data
                    data_fmt = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
                    if data_fmt != data_anterior:
                        ctk.CTkLabel(scroll, text=f"📅 {data_fmt}", font=("Arial", 12, "bold"),
                                     text_color="#F39C12").pack(anchor="w", pady=(15,5))
                        data_anterior = data_fmt
                    
                    # Card do pedido
                    card = ctk.CTkFrame(scroll, fg_color="#333")
                    card.pack(fill="x", pady=2)
                    
                    cliente_nome = cliente if cliente else "Cliente não encontrado"
                    tel_fmt = self.formatar_telefone_visual(telefone) if telefone else "N/A"
                    metodo_str = metodo if metodo else "N/A"
                    valor = valor or 0
                    
                    texto_pedido = f"#{pid} | {cliente_nome} ({tel_fmt})"
                    texto_detalhe = f"🏍️ {entregador} | 💳 {metodo_str} | 💰 R$ {valor:.2f}"
                    
                    ctk.CTkLabel(card, text=texto_pedido, font=("Arial", 11, "bold"), 
                                 anchor="w").pack(anchor="w", padx=10, pady=(5,0))
                    ctk.CTkLabel(card, text=texto_detalhe, font=("Arial", 10), 
                                 text_color="#BDC3C7", anchor="w").pack(anchor="w", padx=10, pady=(0,5))
                                 
            except Exception as e:
                messagebox.showerror("Erro", f"Erro na busca:\n{e}")
        
        def exportar_periodo():
            if not dados_busca_atual:
                messagebox.showwarning("Aviso", "Faça uma busca primeiro.")
                return
            
            data_ini_nome = entry_data_ini.get().replace("/", "-")
            data_fim_nome = entry_data_fim.get().replace("/", "-")
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("Arquivo CSV", "*.csv")],
                initialfile=f"Entregas_{data_ini_nome}_a_{data_fim_nome}.csv",
                title="Salvar Relatório"
            )
            
            if not filename:
                return
            
            try:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["ID", "Data", "Cliente", "Telefone", "Entregador", "Valor (R$)", "Pagamento"])
                    
                    for pid, data, cliente, telefone, entregador, valor, metodo in dados_busca_atual:
                        data_fmt = datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
                        valor_fmt = f"{valor or 0:.2f}".replace(".", ",")
                        writer.writerow([pid, data_fmt, cliente or "N/A", telefone or "N/A", entregador, valor_fmt, metodo or "N/A"])
                
                messagebox.showinfo("Sucesso", f"Relatório exportado!\n\n{filename}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar:\n{e}")
        
        # Executa busca inicial
        executar_busca()

    # ================== LÓGICA DE PAGAMENTO ==================
    def toggle_pagamento_duplo(self):
        if self.chk_pagamento_duplo.get() == 1:
            self.frame_pag2.pack(fill="x", padx=10, pady=(5,0), before=self.frame_troco)
            self.entry_val_pag1.configure(placeholder_text="Valor Parc. 1")
        else:
            self.frame_pag2.pack_forget()
            self.entry_val_pag1.configure(placeholder_text="Valor Total")

    def mudou_forma_pag1(self, escolha):
        if escolha == "Cartão":
            self.combo_parcelas1.pack(side="left", padx=5)
            self.entry_troco.delete(0, "end")
            self.entry_troco.configure(state="disabled")
        else:
            self.combo_parcelas1.pack_forget()
            if escolha == "Dinheiro": 
                self.entry_troco.configure(state="normal")
            else: 
                self.entry_troco.configure(state="disabled")

    def mudou_forma_pag2(self, escolha):
        if escolha == "Cartão": 
            self.combo_parcelas2.pack(side="left", padx=5)
        else: 
            self.combo_parcelas2.pack_forget()

    def auto_completar_restante(self, event=None):
        try:
            total = self.atualizar_totais()
            val1 = self.formatar_float(self.entry_val_pag1.get())
            restante = total - val1
            if restante > 0:
                self.entry_val_pag2.delete(0, "end")
                self.entry_val_pag2.insert(0, f"{restante:.2f}")
        except: 
            pass

    def calcular_troco_dinamico(self, event=None):
        total = self.atualizar_totais()
        pago_dinheiro = self.formatar_float(self.entry_troco.get())
        
        forma1 = self.combo_pag1.get()
        val1 = self.formatar_float(self.entry_val_pag1.get())
        
        if self.chk_pagamento_duplo.get() == 0:
            if forma1 == "Dinheiro":
                if pago_dinheiro > total: 
                    self.lbl_troco.configure(text=f"TROCO: R$ {pago_dinheiro - total:.2f}")
                else: 
                    self.lbl_troco.configure(text="Troco: R$ 0.00")
            else:
                 self.lbl_troco.configure(text="SEM TROCO")
        else:
            forma2 = self.combo_pag2.get()
            val2 = self.formatar_float(self.entry_val_pag2.get())
            
            if abs((val1 + val2) - total) > 0.1:
                self.lbl_troco.configure(text="Valores incorretos")
                return

            if forma1 == "Dinheiro" or forma2 == "Dinheiro":
                 if pago_dinheiro > 0: 
                     devido_em_dinheiro = 0
                     if forma1 == "Dinheiro": 
                         devido_em_dinheiro += val1
                     if forma2 == "Dinheiro": 
                         devido_em_dinheiro += val2
                     
                     if pago_dinheiro > devido_em_dinheiro:
                         self.lbl_troco.configure(text=f"TROCO: R$ {pago_dinheiro - devido_em_dinheiro:.2f}")
                     else:
                         self.lbl_troco.configure(text="Troco: R$ 0.00")

    # ================== HISTÓRICO DE ENDEREÇOS ==================
    def abrir_historico_enderecos(self):
        tel_limpo = self.limpar_telefone(self.entry_tel.get())
        if not tel_limpo:
            messagebox.showwarning("Aviso", "Digite um telefone primeiro.")
            return
            
        top = ctk.CTkToplevel(self)
        top.title("Histórico de Endereços")
        top.geometry("550x500")
        top.attributes("-topmost", True)
        
        frame_topo = ctk.CTkFrame(top)
        frame_topo.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame_topo, text="Endereços Antigos", font=("Arial", 14, "bold")).pack(side="left")
        
        ctk.CTkButton(frame_topo, text="➕ NOVO ENDEREÇO", width=140, fg_color="#3498DB", text_color="white",
                      command=lambda: self.adicionar_endereco_manual(tel_limpo, top)).pack(side="right")
        
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.carregar_lista_historico(scroll, tel_limpo, top)

    def carregar_lista_historico(self, scroll_frame, tel_limpo, top_window):
        for widget in scroll_frame.winfo_children(): 
            widget.destroy()

        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT rua, numero, bairro, referencia, ultimo_uso FROM historico_enderecos WHERE telefone_cliente = ? ORDER BY ultimo_uso DESC", (tel_limpo,))
            enderecos = cursor.fetchall()
            conn.close()
        except Exception as e:
            ctk.CTkLabel(scroll_frame, text=f"Erro: {e}").pack(pady=20)
            return
        
        if not enderecos:
            ctk.CTkLabel(scroll_frame, text="Nenhum endereço salvo.").pack(pady=20)
            return
            
        def usar_endereco(dados):
            self.entry_rua.delete(0, "end")
            self.entry_rua.insert(0, dados[0])
            self.entry_num.delete(0, "end")
            self.entry_num.insert(0, dados[1])
            self.entry_bairro.delete(0, "end")
            self.entry_bairro.insert(0, dados[2])
            self.entry_ref.delete(0, "end")
            self.entry_ref.insert(0, dados[3])
            top_window.destroy()

        for end in enderecos:
            card = ctk.CTkFrame(scroll_frame, fg_color="#333")
            card.pack(fill="x", pady=5)
            texto = f"{end[0]}, {end[1]}\nBairro: {end[2]}\nRef: {end[3]}"
            ctk.CTkLabel(card, text=texto, justify="left", anchor="w").pack(side="left", padx=10, pady=5)
            ctk.CTkButton(card, text="USAR ESTE", width=80, fg_color="#27AE60", text_color="white", command=lambda e=end: usar_endereco(e)).pack(side="right", padx=10)

    def adicionar_endereco_manual(self, tel_limpo, janela_pai):
        add_win = ctk.CTkToplevel(janela_pai)
        add_win.title("Adicionar Endereço")
        add_win.geometry("400x350")
        add_win.attributes("-topmost", True)
        add_win.lift()
        add_win.focus_force()
        add_win.grab_set()
        
        ctk.CTkLabel(add_win, text="Rua:").pack(anchor="w", padx=20, pady=(20,0))
        e_rua = ctk.CTkEntry(add_win)
        e_rua.pack(fill="x", padx=20)
        ctk.CTkLabel(add_win, text="Número:").pack(anchor="w", padx=20)
        e_num = ctk.CTkEntry(add_win)
        e_num.pack(fill="x", padx=20)
        ctk.CTkLabel(add_win, text="Bairro:").pack(anchor="w", padx=20)
        e_bairro = ctk.CTkEntry(add_win)
        e_bairro.pack(fill="x", padx=20)
        ctk.CTkLabel(add_win, text="Referência:").pack(anchor="w", padx=20)
        e_ref = ctk.CTkEntry(add_win)
        e_ref.pack(fill="x", padx=20)
        
        def salvar_novo():
            r, n, b, ref = e_rua.get(), e_num.get(), e_bairro.get(), e_ref.get()
            if not r or not b:
                messagebox.showwarning("Erro", "Rua e Bairro são obrigatórios.")
                return
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO historico_enderecos (telefone_cliente, rua, numero, bairro, referencia, ultimo_uso) VALUES (?, ?, ?, ?, ?, ?)",
                                (tel_limpo, r, n, b, ref, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                messagebox.showinfo("Sucesso", "Endereço adicionado!")
                add_win.destroy()
                
                scroll_widget = None
                for widget in janela_pai.winfo_children():
                    if isinstance(widget, ctk.CTkScrollableFrame):
                        scroll_widget = widget
                        break
                if scroll_widget:
                    self.carregar_lista_historico(scroll_widget, tel_limpo, janela_pai)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

        ctk.CTkButton(add_win, text="SALVAR", command=salvar_novo, fg_color="#2ECC71", text_color="white").pack(pady=20)

    # ================== GESTÃO DE CLIENTES ==================
    def abrir_gestao_clientes(self):
        top = ctk.CTkToplevel(self)
        top.title("Buscar Cliente / Iniciar Pedido")
        top.geometry("950x650") 
        top.attributes("-topmost", True)
        top.lift()
        top.focus_force()
        top.grab_set()

        frame_busca = ctk.CTkFrame(top)
        frame_busca.pack(fill="x", padx=10, pady=10)
        
        entry_busca = ctk.CTkEntry(frame_busca, placeholder_text="Digite Nome ou Telefone e dê Enter...")
        entry_busca.pack(side="left", fill="x", expand=True, padx=(0, 10))
        entry_busca.focus_set() 
        
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0,10))

        def usar_cliente_para_pedido(dados_cli):
            self.limpar_tela()
            tel_formatado = self.formatar_telefone_visual(dados_cli[0])
            self.entry_tel.delete(0, "end")
            self.entry_tel.insert(0, tel_formatado)
            self.entry_nome.insert(0, dados_cli[1])
            if dados_cli[2]: 
                self.entry_rua.insert(0, dados_cli[2])
            if dados_cli[3]: 
                self.entry_num.insert(0, dados_cli[3])
            if dados_cli[4]: 
                self.entry_bairro.insert(0, dados_cli[4])
            if dados_cli[5]: 
                self.entry_ref.insert(0, dados_cli[5])
            top.destroy()
            self.entry_val.focus_set() 

        def carregar_clientes(termo=""):
            for widget in scroll.winfo_children(): 
                widget.destroy()
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                cursor = conn.cursor()
                if termo:
                    t = f"%{termo}%"
                    cursor.execute("SELECT * FROM clientes WHERE nome LIKE ? OR telefone LIKE ? ORDER BY nome", (t, t))
                else:
                    cursor.execute("SELECT * FROM clientes ORDER BY nome LIMIT 50")
                clientes = cursor.fetchall()
                conn.close()
            except Exception as e:
                ctk.CTkLabel(scroll, text=f"Erro: {e}").pack(pady=20)
                return

            if not clientes:
                ctk.CTkLabel(scroll, text="Nenhum cliente encontrado.").pack(pady=20)
                return

            for cli in clientes:
                card = ctk.CTkFrame(scroll, fg_color="#2C3E50")
                card.pack(fill="x", pady=5)
                tel_fmt = self.formatar_telefone_visual(cli[0])
                info_texto = f"{cli[1]} - {tel_fmt}\n{cli[2] or ''}, {cli[3] or ''} - {cli[4] or ''}"
                ctk.CTkLabel(card, text=info_texto, font=("Arial", 13), justify="left", anchor="w").pack(side="left", padx=10, pady=10)
                
                ctk.CTkButton(card, text="✅ NOVO PEDIDO", font=("Arial", 12, "bold"), width=120, fg_color="#2ECC71", 
                              text_color="black", command=lambda c=cli: usar_cliente_para_pedido(c)).pack(side="right", padx=10)

                ctk.CTkButton(card, text="🗑️", width=40, fg_color="#C0392B", text_color="white", command=lambda t=cli[0]: deletar_cliente(t)).pack(side="right", padx=5)
                ctk.CTkButton(card, text="✏️", width=40, fg_color="#F39C12", text_color="white", command=lambda c=cli: modal_editar_cliente(c)).pack(side="right", padx=5)
                ctk.CTkButton(card, text="🔔", width=40, fg_color="#8E44AD", text_color="white", command=lambda c=cli: modal_adicionar_lembrete(c)).pack(side="right", padx=5)

        def deletar_cliente(telefone):
            if messagebox.askyesno("Excluir", "Tem certeza? Isso apaga o histórico de pedidos deste cliente!"):
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM clientes WHERE telefone = ?", (telefone,))
                    cursor.execute("DELETE FROM pedidos WHERE cliente_tel = ?", (telefone,))
                    cursor.execute("DELETE FROM lembretes WHERE cliente_tel = ?", (telefone,))
                    cursor.execute("DELETE FROM historico_enderecos WHERE telefone_cliente = ?", (telefone,))
                    conn.commit()
                    conn.close()
                    carregar_clientes(entry_busca.get())
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao deletar:\n{e}")

        def modal_editar_cliente(dados_cli):
            edit_win = ctk.CTkToplevel(top)
            edit_win.title(f"Editar: {dados_cli[1]}")
            edit_win.geometry("400x450")
            edit_win.attributes("-topmost", True)
            edit_win.lift()
            edit_win.focus_force()
            edit_win.grab_set() 
            
            ctk.CTkLabel(edit_win, text="Nome:").pack(anchor="w", padx=20)
            e_nome = ctk.CTkEntry(edit_win)
            e_nome.insert(0, dados_cli[1])
            e_nome.pack(fill="x", padx=20)
            ctk.CTkLabel(edit_win, text="Rua:").pack(anchor="w", padx=20)
            e_rua = ctk.CTkEntry(edit_win)
            e_rua.insert(0, dados_cli[2] if dados_cli[2] else "")
            e_rua.pack(fill="x", padx=20)
            ctk.CTkLabel(edit_win, text="Número:").pack(anchor="w", padx=20)
            e_num = ctk.CTkEntry(edit_win)
            e_num.insert(0, dados_cli[3] if dados_cli[3] else "")
            e_num.pack(fill="x", padx=20)
            ctk.CTkLabel(edit_win, text="Bairro:").pack(anchor="w", padx=20)
            e_bairro = ctk.CTkEntry(edit_win)
            e_bairro.insert(0, dados_cli[4] if dados_cli[4] else "")
            e_bairro.pack(fill="x", padx=20)
            ctk.CTkLabel(edit_win, text="Referência:").pack(anchor="w", padx=20)
            e_ref = ctk.CTkEntry(edit_win)
            e_ref.insert(0, dados_cli[5] if dados_cli[5] else "")
            e_ref.pack(fill="x", padx=20)
            
            def salvar_edicao():
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE clientes SET nome=?, rua=?, numero=?, bairro=?, referencia=? WHERE telefone=?", (e_nome.get(), e_rua.get(), e_num.get(), e_bairro.get(), e_ref.get(), dados_cli[0]))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Sucesso", "Dados atualizados!")
                    edit_win.destroy()
                    carregar_clientes(entry_busca.get())
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

            ctk.CTkButton(edit_win, text="SALVAR ALTERAÇÕES", command=salvar_edicao, fg_color="#27AE60", text_color="white").pack(pady=20)

        def modal_adicionar_lembrete(dados_cli):
            lem_win = ctk.CTkToplevel(top)
            lem_win.title(f"Novo Lembrete: {dados_cli[1]}")
            lem_win.geometry("400x300")
            lem_win.attributes("-topmost", True)
            lem_win.lift()
            lem_win.focus_force()
            lem_win.grab_set()
            
            ctk.CTkLabel(lem_win, text="Nome do Medicamento:").pack(anchor="w", padx=20, pady=(20,0))
            e_med = ctk.CTkEntry(lem_win)
            e_med.pack(fill="x", padx=20)
            ctk.CTkLabel(lem_win, text="Duração (Dias):").pack(anchor="w", padx=20)
            e_dias = ctk.CTkEntry(lem_win)
            e_dias.pack(fill="x", padx=20)
            
            def salvar_lembrete_manual():
                med = e_med.get()
                dias = e_dias.get()
                if not med or not dias.isdigit():
                    messagebox.showwarning("Erro", "Preencha corretamente.")
                    return
                hoje_dt = datetime.now()
                d_int = int(dias)
                data_aviso = (hoje_dt + timedelta(days=d_int-3)).strftime("%Y-%m-%d")
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO lembretes (cliente_tel, medicamento, data_aviso, status) VALUES (?, ?, ?, 'PENDENTE')", (dados_cli[0], med, data_aviso))
                    conn.commit()
                    conn.close()
                    messagebox.showinfo("Sucesso", "Lembrete agendado!")
                    lem_win.destroy()
                    self.verificar_avisos_hoje_silencioso()
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao salvar:\n{e}")

            ctk.CTkButton(lem_win, text="AGENDAR", command=salvar_lembrete_manual, fg_color="#8E44AD", text_color="white").pack(pady=20)

        entry_busca.bind("<Return>", lambda event: carregar_clientes(entry_busca.get()))
        btn_buscar = ctk.CTkButton(frame_busca, text="🔍", width=50, command=lambda: carregar_clientes(entry_busca.get()), text_color="white")
        btn_buscar.pack(side="right")
        carregar_clientes()

    # ================== FUNÇÕES DE SUPORTE ==================
    def limpar_telefone(self, tel):
        numeros = "".join(filter(str.isdigit, tel))
        tam = len(numeros)
        if tam == 8 or tam == 9: 
            return f"{DDD_PADRAO}{numeros}"
        return numeros

    def formatar_telefone_visual(self, tel):
        numeros = "".join(filter(str.isdigit, tel))
        if len(numeros) == 11: 
            return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
        elif len(numeros) == 10: 
            return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
        return tel

    def formatar_float(self, valor_str):
        try: 
            return float(valor_str.replace(",", ".").strip())
        except: 
            return 0.0

    def toggle_lembrete(self):
        if self.chk_lembrete.get() == 1:
            self.entry_med_nome.pack(fill="x", padx=10, pady=(0,5))
            self.entry_dias_duracao.pack(fill="x", padx=10, pady=(0,10))
        else:
            self.entry_med_nome.pack_forget()
            self.entry_dias_duracao.pack_forget()

    def limpar_tela(self):
        self.entry_tel.delete(0, "end")
        self.entry_nome.delete(0, "end")
        self.entry_rua.delete(0, "end")
        self.entry_num.delete(0, "end")
        self.entry_bairro.delete(0, "end")
        self.entry_ref.delete(0, "end")
        self.entry_val.delete(0, "end")
        self.entry_taxa.delete(0, "end")
        self.entry_troco.delete(0, "end")
        self.lbl_total.configure(text="TOTAL: R$ 0.00")
        self.lbl_troco.configure(text="Troco: R$ 0.00")
        
        # Reset Pagamento
        self.chk_pagamento_duplo.deselect()
        self.toggle_pagamento_duplo()
        self.combo_pag1.set("Dinheiro")
        self.mudou_forma_pag1("Dinheiro")
        self.entry_val_pag1.delete(0, "end")
        self.entry_val_pag2.delete(0, "end")
        self.entry_troco.configure(state="normal")
        
        self.chk_lembrete.deselect()
        self.toggle_lembrete()
        self.entry_med_nome.delete(0, "end")
        self.entry_dias_duracao.delete(0, "end")
        self.entry_tel.focus_set()
        
        # Reset entregador
        self.var_entregador.set("Entregador A")

    def buscar_cliente(self, event=None):
        tel_bruto = self.entry_tel.get()
        if not tel_bruto.strip(): 
            return
        tel_limpo = self.limpar_telefone(tel_bruto)
        
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT nome, rua, numero, bairro, referencia FROM clientes WHERE telefone = ?", (tel_limpo,))
            res = cursor.fetchone()
            conn.close()
        except: 
            res = None
        
        if res:
            self.entry_nome.delete(0, "end")
            self.entry_nome.insert(0, res[0])
            if res[1]: 
                self.entry_rua.delete(0, "end")
                self.entry_rua.insert(0, res[1])
            if res[2]: 
                self.entry_num.delete(0, "end")
                self.entry_num.insert(0, res[2])
            if res[3]: 
                self.entry_bairro.delete(0, "end")
                self.entry_bairro.insert(0, res[3])
            if res[4]: 
                self.entry_ref.delete(0, "end")
                self.entry_ref.insert(0, res[4])
            if self.entry_tel.get() != self.formatar_telefone_visual(tel_limpo):
                self.entry_tel.delete(0, "end")
                self.entry_tel.insert(0, self.formatar_telefone_visual(tel_limpo))
            self.after(10, lambda: self.entry_val.focus_set())
        else:
            self.entry_nome.focus_set()

    def atualizar_totais(self, event=None):
        val_prod = self.formatar_float(self.entry_val.get())
        val_taxa = self.formatar_float(self.entry_taxa.get())
        if event:
            self.entry_val.delete(0, "end")
            self.entry_val.insert(0, f"{val_prod:.2f}")
            self.entry_taxa.delete(0, "end")
            self.entry_taxa.insert(0, f"{val_taxa:.2f}")
        total = val_prod + val_taxa
        self.lbl_total.configure(text=f"TOTAL: R$ {total:.2f}")
        return total

    def fazer_backup_seguranca(self):
        try:
            db_origem = DB_PATH
            if not os.path.exists(db_origem):
                messagebox.showerror("Erro", "Banco de dados não encontrado.")
                return
            hoje_str = datetime.now().strftime("%Y-%m-%d_%H%M")
            nome_sugerido = f"backup_totalpharma_{hoje_str}.db"
            destino = filedialog.asksaveasfilename(title="Salvar Backup de Segurança", initialfile=nome_sugerido, defaultextension=".db", filetypes=[("Arquivo de Banco de Dados", "*.db")])
            if destino:
                shutil.copy2(db_origem, destino)
                messagebox.showinfo("Sucesso", f"Backup realizado com sucesso!\n\nSalvo em:\n{destino}")
        except Exception as e:
            messagebox.showerror("Erro Backup", f"Não foi possível fazer o backup:\n{e}")

    def salvar_apenas_cliente(self):
        tel_limpo = self.limpar_telefone(self.entry_tel.get())
        nome = self.entry_nome.get().strip()
        
        if not tel_limpo or not nome:
            messagebox.showwarning("Aviso", "Para cadastrar, preencha pelo menos Telefone e Nome.")
            return
        
        # Validação extra
        if len(tel_limpo) < 10 or len(tel_limpo) > 11:
            messagebox.showwarning("Aviso", f"Telefone inválido: {tel_limpo} ({len(tel_limpo)} dígitos)\nEsperado: 10 ou 11 dígitos.")
            return
            
        rua = self.entry_rua.get().strip()
        num = self.entry_num.get().strip()
        bairro = self.entry_bairro.get().strip()
        ref = self.entry_ref.get().strip()
        
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            # Verifica se já existe
            cursor.execute("SELECT nome FROM clientes WHERE telefone = ?", (tel_limpo,))
            existente = cursor.fetchone()
            
            cursor.execute("INSERT OR REPLACE INTO clientes (telefone, nome, rua, numero, bairro, referencia) VALUES (?, ?, ?, ?, ?, ?)", 
                           (tel_limpo, nome, rua, num, bairro, ref))
            conn.commit()
            
            if existente:
                messagebox.showinfo("Sucesso", f"Cliente {nome} ATUALIZADO!")
            else:
                messagebox.showinfo("Sucesso", f"Cliente {nome} CADASTRADO com sucesso!")
                
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Erro de Integridade", f"Telefone já existe ou dado inválido:\n{e}")
        except sqlite3.OperationalError as e:
            messagebox.showerror("Erro Operacional", f"Banco pode estar corrompido ou bloqueado:\n{e}")
        except Exception as e:
            messagebox.showerror("Erro BD", f"Erro inesperado:\n{type(e).__name__}: {e}")
        finally:
            if conn:
                conn.close()

    def imprimir_apenas_endereco(self):
        if not WINDOWS_PRINT_AVAILABLE:
            messagebox.showwarning("Aviso", "Impressão não disponível neste sistema.")
            return
            
        tel_limpo = self.limpar_telefone(self.entry_tel.get())
        nome = self.entry_nome.get().strip()
        if not tel_limpo or not nome:
            messagebox.showwarning("Aviso", "Preencha dados do cliente.")
            return
        rua = self.entry_rua.get().strip()
        num = self.entry_num.get().strip()
        bairro = self.entry_bairro.get().strip()
        ref = self.entry_ref.get().strip()
        tel_fmt = self.formatar_telefone_visual(tel_limpo)
        rua_wrap = textwrap.fill(f"{rua}, {num}", width=LARGURA_PAPEL)
        bairro_wrap = textwrap.fill(f"Bairro: {bairro}", width=LARGURA_PAPEL)
        ref_wrap = textwrap.fill(f"Obs: {ref}", width=LARGURA_PAPEL)

        texto = "-" * 32 + "\n       ENTREGA RAPIDA\n" + "-" * 32 + "\n"
        texto += f"CLI: {nome}\nTEL: {tel_fmt}\n" + "-" * 32 + "\n"
        texto += f"{rua_wrap}\n{bairro_wrap}\n\n"
        if ref: 
            texto += f"{ref_wrap}\n"
        texto += "-" * 32 + "\n" + f"MOTO: {self.var_entregador.get()}\n" + "-" * 32 + "\n"
        self.imprimir_via_windows_gdi(texto)

    def imprimir_via_windows_gdi(self, texto_cupom):
        if not WINDOWS_PRINT_AVAILABLE:
            messagebox.showwarning("Aviso", "Impressão não disponível neste sistema.")
            return
            
        try:
            hDC = win32ui.CreateDC()
            hDC.CreatePrinterDC(win32print.GetDefaultPrinter())
            hDC.StartDoc("Cupom TotalPharma")
            hDC.StartPage()
            
            font_dict = {'name': 'Courier New', 'height': 26, 'weight': 600} 
            font = win32ui.CreateFont(font_dict)
            hDC.SelectObject(font)
            
            y = 50
            for linha in texto_cupom.split("\n"):
                hDC.TextOut(10, y, linha)
                y += 28 
                
            hDC.TextOut(10, y + 50, ".")
            hDC.EndPage()
            hDC.EndDoc()
            hDC.DeleteDC()
        except Exception as e:
            messagebox.showerror("Erro GDI", f"Erro na impressão:\n{e}")

    def finalizar(self):
        tel_limpo = self.limpar_telefone(self.entry_tel.get())
        nome = self.entry_nome.get().strip()
        if not tel_limpo or not nome:
            messagebox.showwarning("Aviso", "Preencha Telefone e Nome.")
            return
        rua = self.entry_rua.get().strip()
        num = self.entry_num.get().strip()
        bairro = self.entry_bairro.get().strip()
        ref = self.entry_ref.get().strip()
        total = self.atualizar_totais()
        if total <= 0:
            messagebox.showwarning("Aviso", "Valor total zerado.")
            return

        salvar_lembrete = False
        data_aviso = None
        med_nome = ""
        if self.chk_lembrete.get() == 1:
            med_nome = self.entry_med_nome.get().strip()
            dias_duracao = self.entry_dias_duracao.get().strip()
            if med_nome and dias_duracao.isdigit():
                hoje_dt = datetime.now()
                dias = int(dias_duracao)
                data_aviso = (hoje_dt + timedelta(days=dias-3)).strftime("%Y-%m-%d")
                salvar_lembrete = True

        # --- Lógica de Pagamento ---
        pag_desc = ""
        pag_resumo_bd = "" 
        
        forma1 = self.combo_pag1.get()
        if self.chk_pagamento_duplo.get() == 0:
            # Pagamento Único
            if forma1 == "Cartão":
                parc = self.combo_parcelas1.get()
                pag_desc = f"PAGAMENTO: Cartão ({parc})"
                pag_resumo_bd = f"Cartão ({parc})"
            else:
                pag_desc = f"PAGAMENTO: {forma1.upper()}"
                pag_resumo_bd = forma1
                
            if forma1 == "Dinheiro":
                pago = self.formatar_float(self.entry_troco.get())
                troco = pago - total
                if troco > 0: 
                    pag_desc += f"\nDinheiro: R$ {pago:.2f} | Troco: R$ {troco:.2f}"
                else: 
                    pag_desc += "\nSem Troco"
        else:
            # Pagamento Duplo
            val1 = self.formatar_float(self.entry_val_pag1.get())
            parc1 = self.combo_parcelas1.get() if forma1 == "Cartão" else ""
            desc1 = f"{forma1} {parc1}"
            
            forma2 = self.combo_pag2.get()
            val2 = self.formatar_float(self.entry_val_pag2.get())
            parc2 = self.combo_parcelas2.get() if forma2 == "Cartão" else ""
            desc2 = f"{forma2} {parc2}"
            
            pag_desc = "PAGAMENTO MISTO:"
            pag_desc += f"\n1) {desc1}: R$ {val1:.2f}"
            pag_desc += f"\n2) {desc2}: R$ {val2:.2f}"
            pag_resumo_bd = f"Misto: {desc1}/{desc2}"
            
            if "Dinheiro" in [forma1, forma2]:
                pago = self.formatar_float(self.entry_troco.get())
                soma_din = 0
                if forma1 == "Dinheiro": 
                    soma_din += val1
                if forma2 == "Dinheiro": 
                    soma_din += val2
                if pago > soma_din:
                    pag_desc += f"\nTroco: R$ {pago - soma_din:.2f}"

        # --- Cupom ---
        tel_fmt = self.formatar_telefone_visual(tel_limpo)
        sep = "-" * 32 
        rua_wrap = textwrap.fill(f"{rua}, {num}", width=LARGURA_PAPEL)
        bairro_wrap = textwrap.fill(f"Bairro: {bairro}", width=LARGURA_PAPEL)
        ref_wrap = textwrap.fill(f"Obs: {ref}", width=LARGURA_PAPEL)
        dt_hora = datetime.now().strftime('%d/%m/%Y %H:%M')

        cupom = f"""
     FARMACIA TOTALPHARMA
{dt_hora}
{sep}
CLIENTE: {nome}
TEL: {tel_fmt}
{sep}
ENTREGA:
{rua_wrap}
{bairro_wrap}

{ref_wrap}
{sep}
MOTOBOY: {self.var_entregador.get()}
{sep}
VALORES:
Prod:  R$ {self.formatar_float(self.entry_val.get()):.2f}
Taxa:  R$ {self.formatar_float(self.entry_taxa.get()):.2f}
TOTAL: R$ {total:.2f}
{sep}
{pag_desc}
{sep}

   Obrigado pela preferencia!
"""
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            cursor.execute("INSERT OR REPLACE INTO clientes (telefone, nome, rua, numero, bairro, referencia) VALUES (?, ?, ?, ?, ?, ?)", 
                           (tel_limpo, nome, rua, num, bairro, ref))
                           
            cursor.execute("SELECT rua, numero FROM historico_enderecos WHERE telefone_cliente = ? ORDER BY id DESC LIMIT 1", (tel_limpo,))
            ultimo = cursor.fetchone()
            if not ultimo or (ultimo[0] != rua or ultimo[1] != num):
                 cursor.execute("INSERT INTO historico_enderecos (telefone_cliente, rua, numero, bairro, referencia, ultimo_uso) VALUES (?, ?, ?, ?, ?, ?)",
                                (tel_limpo, rua, num, bairro, ref, datetime.now().strftime("%Y-%m-%d")))

            cursor.execute("INSERT INTO pedidos (data, cliente_tel, entregador, valor_total, metodo_pagamento, detalhes_pagamento) VALUES (?, ?, ?, ?, ?, ?)", 
                           (datetime.now().strftime("%Y-%m-%d"), tel_limpo, self.var_entregador.get(), total, pag_resumo_bd, pag_desc))
            
            if salvar_lembrete:
                cursor.execute("INSERT INTO lembretes (cliente_tel, medicamento, data_aviso, status) VALUES (?, ?, ?, 'PENDENTE')", 
                               (tel_limpo, med_nome, data_aviso))
            conn.commit()
        except Exception as e:
            messagebox.showerror("Erro BD", str(e))
        finally:
            if conn:
                conn.close()

        if WINDOWS_PRINT_AVAILABLE:
            self.imprimir_via_windows_gdi(cupom)
        self.limpar_tela()
        self.atualizar_painel_status()

    def verificar_avisos_hoje_silencioso(self):
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM lembretes WHERE data_aviso <= ? AND status = 'PENDENTE'", (hoje,))
            qtd = cursor.fetchone()[0]
            conn.close()
            if qtd > 0: 
                self.btn_alertas.configure(fg_color="#E74C3C", text=f"🔔 {qtd} CLIENTES!", text_color="white") 
            else: 
                self.btn_alertas.configure(fg_color="#555", text="🔔 RECOMPRAS", text_color="white")
        except: 
            pass

    def ver_alertas_recompra(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT l.id, c.nome, c.telefone, l.medicamento, l.data_aviso FROM lembretes l JOIN clientes c ON l.cliente_tel = c.telefone WHERE l.data_aviso <= ? AND l.status = 'PENDENTE'", (hoje,))
            dados = cursor.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar:\n{e}")
            return

        if not dados:
            messagebox.showinfo("Tudo Certo", "Nenhum cliente para ligar hoje.")
            return
            
        top = ctk.CTkToplevel(self)
        top.title("Gestão de Recompras")
        top.geometry("700x500")
        top.attributes("-topmost", True)
        top.lift()
        top.focus_force()
        top.grab_set()
        
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        for id_lembrete, nome, tel, med, data in dados:
            card = ctk.CTkFrame(scroll, fg_color="#444")
            card.pack(fill="x", pady=5)
            tel_fmt = self.formatar_telefone_visual(tel)
            lbl_info = ctk.CTkLabel(card, text=f"{nome} ({tel_fmt})\nRemédio: {med}", font=("Arial", 14), anchor="w", justify="left")
            lbl_info.pack(side="left", padx=10, pady=10)
            
            btn_zap = ctk.CTkButton(card, text="💬 WHATSAPP", width=120, fg_color="#25D366", text_color="white",
                                    command=lambda n=nome, t=tel, m=med: self.abrir_whatsapp_recompra(n, t, m))
            btn_zap.pack(side="right", padx=5)
            btn_ok = ctk.CTkButton(card, text="✅ JÁ RESOLVI", width=120, fg_color="#27AE60", text_color="white", 
                                   command=lambda i=id_lembrete, t=top: self.dar_baixa_lembrete(i, t))
            btn_ok.pack(side="right", padx=5)

    def abrir_whatsapp_recompra(self, nome, telefone, remedio):
        numeros = "".join(filter(str.isdigit, telefone))
        if len(numeros) <= 11: 
            numeros = "55" + numeros
        msg = f"Olá {nome}, tudo bem? 👋\n\nAqui é da *Farmácia TotalPharma*.\n\nPassando apenas para lembrar que está próximo da data de reposição do seu *{remedio}*.\n\nGostaria de garantir a entrega agora para não ficar sem? 🛵💊"
        link = f"https://wa.me/{numeros}?text={urllib.parse.quote(msg)}"
        webbrowser.open(link)

    def dar_baixa_lembrete(self, id_lembrete, janela):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("UPDATE lembretes SET status = 'CONCLUIDO' WHERE id = ?", (id_lembrete,))
            conn.commit()
            conn.close()
            janela.destroy()
            self.ver_alertas_recompra()
            self.verificar_avisos_hoje_silencioso()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha:\n{e}")

    def listar_todos_agendamentos(self):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, c.nome, c.telefone, l.medicamento, l.data_aviso 
                FROM lembretes l
                JOIN clientes c ON l.cliente_tel = c.telefone
                WHERE l.status = 'PENDENTE'
                ORDER BY l.data_aviso ASC
            """)
            dados = cursor.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar:\n{e}")
            return

        top = ctk.CTkToplevel(self)
        top.title("Todos os Agendamentos Futuros")
        top.geometry("700x600")
        top.attributes("-topmost", True)
        top.lift()
        top.focus_force()
        top.grab_set()
        
        ctk.CTkLabel(top, text="PRÓXIMAS RECOMPRAS", font=("Arial", 20, "bold"), text_color="#3498DB").pack(pady=10)
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        hoje = datetime.now().date()
        
        if not dados:
            ctk.CTkLabel(scroll, text="Nenhum agendamento encontrado.").pack(pady=20)
            return

        for id_lembrete, nome, tel, med, data_str in dados:
            card = ctk.CTkFrame(scroll, fg_color="#2C3E50")
            card.pack(fill="x", pady=5)
            data_alvo = datetime.strptime(data_str, "%Y-%m-%d").date()
            dias_restantes = (data_alvo - hoje).days
            
            if dias_restantes < 0:
                cor_status = "#E74C3C"
                texto_status = f"ATRASADO {abs(dias_restantes)} DIAS"
            elif dias_restantes == 0:
                cor_status = "#F39C12"
                texto_status = "É HOJE!"
            else:
                cor_status = "#27AE60"
                texto_status = f"Faltam {dias_restantes} dias ({data_alvo.strftime('%d/%m')})"

            frame_info = ctk.CTkFrame(card, fg_color="transparent")
            frame_info.pack(side="left", padx=10, pady=5)
            tel_fmt = self.formatar_telefone_visual(tel)
            ctk.CTkLabel(frame_info, text=f"{nome}", font=("Arial", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(frame_info, text=f"Remédio: {med}", text_color="#BDC3C7").pack(anchor="w")
            ctk.CTkLabel(card, text=texto_status, text_color=cor_status, font=("Arial", 13, "bold")).pack(side="left", padx=20)
            
            btn_apagar = ctk.CTkButton(card, text="🗑️", width=40, fg_color="#C0392B", text_color="white", command=lambda i=id_lembrete, t=top: self.apagar_lembrete(i, t))
            btn_apagar.pack(side="right", padx=5)
            if dias_restantes <= 0:
                btn_zap = ctk.CTkButton(card, text="💬", width=40, fg_color="#25D366", text_color="white", command=lambda n=nome, tele=tel, m=med: self.abrir_whatsapp_recompra(n, tele, m))
                btn_zap.pack(side="right", padx=5)

    def apagar_lembrete(self, id_lembrete, janela):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja apagar este lembrete?"):
            try:
                conn = sqlite3.connect(DB_PATH, timeout=10)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM lembretes WHERE id = ?", (id_lembrete,))
                conn.commit()
                conn.close()
                janela.destroy()
                self.listar_todos_agendamentos()
                self.verificar_avisos_hoje_silencioso()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha:\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()