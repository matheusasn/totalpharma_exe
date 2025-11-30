import customtkinter as ctk
import sqlite3
from tkinter import messagebox
from datetime import datetime
import os
import sys
import textwrap
import csv # <--- Nova biblioteca para gerar Excel/CSV

import win32api
import win32print
import ctypes

# -------------- CONFIGURAÇÕES --------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
DDD_PADRAO = "83" 

def configurar_identidade_windows():
    try:
        myappid = 'totalpharma.delivery.pdv.v4.0' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except: pass

configurar_identidade_windows()

def get_app_path():
    app_data = os.getenv('APPDATA')
    pasta_app = os.path.join(app_data, "TotalPharma")
    if not os.path.exists(pasta_app):
        try: os.makedirs(pasta_app)
        except: pass
    return pasta_app

def init_db():
    try:
        pasta_app = get_app_path()
        db_path = os.path.join(pasta_app, "dados_farmacia.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                cliente_tel TEXT,
                entregador TEXT,
                valor_total REAL,
                metodo_pagamento TEXT, 
                FOREIGN KEY(cliente_tel) REFERENCES clientes(telefone)
            )
        """)
        colunas_novas = ["rua", "numero", "bairro", "referencia", "metodo_pagamento"]
        for col in colunas_novas:
            try:
                tabela = "pedidos" if col == "metodo_pagamento" else "clientes"
                cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} TEXT")
            except: pass
        conn.commit()
        conn.close()
        return db_path
    except Exception as e:
        return "dados_farmacia.db"

DB_PATH = init_db()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TotalPharma - PDV Windows")
        self.geometry("900x720")
        
        try:
            if getattr(sys, 'frozen', False):
                app_path = os.path.dirname(sys.executable)
            else:
                app_path = os.path.dirname(os.path.abspath(__file__))
            caminho_icone = os.path.join(app_path, "farmacia.ico")
            if os.path.exists(caminho_icone):
                self.iconbitmap(caminho_icone)
                self.wm_iconbitmap(caminho_icone)
        except: pass 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.criar_coluna_cliente()
        self.criar_coluna_pagamento()

    def criar_coluna_cliente(self):
        frame_cli = ctk.CTkFrame(self)
        frame_cli.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(frame_cli, text="DADOS DO CLIENTE", font=("Arial", 16, "bold"), text_color="#3B8ED0").pack(pady=(15,10))

        ctk.CTkLabel(frame_cli, text="Telefone (Tab para buscar):").pack(anchor="w", padx=15)
        self.entry_tel = ctk.CTkEntry(frame_cli, placeholder_text="Somente números")
        self.entry_tel.pack(fill="x", padx=15, pady=(0, 10))
        self.entry_tel.bind("<FocusOut>", self.buscar_cliente)

        ctk.CTkLabel(frame_cli, text="Nome do Cliente:").pack(anchor="w", padx=15)
        self.entry_nome = ctk.CTkEntry(frame_cli)
        self.entry_nome.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(frame_cli, text="Endereço de Entrega:", text_color="#3B8ED0", font=("Arial", 13, "bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
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
        self.var_entregador = ctk.StringVar(value="Entregador da Manhã")
        frame_radio = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_radio.pack(fill="x", padx=15, pady=5)
        ctk.CTkRadioButton(frame_radio, text="Entregador da Manhã", variable=self.var_entregador, value="Entregador da Manhã").pack(anchor="w", pady=2)
        ctk.CTkRadioButton(frame_radio, text="Entregador da Tarde/Noite", variable=self.var_entregador, value="Entregador da Tarde/Noite").pack(anchor="w", pady=2)
        ctk.CTkRadioButton(frame_radio, text="Moto Extra", variable=self.var_entregador, value="Moto Extra").pack(anchor="w", pady=2)

    def criar_coluna_pagamento(self):
        frame_pag = ctk.CTkFrame(self)
        frame_pag.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame_pag, text="PAGAMENTO", font=("Arial", 16, "bold"), text_color="#2CC985").pack(pady=(15,10))

        ctk.CTkLabel(frame_pag, text="Valor Produtos (R$):").pack(anchor="w", padx=20)
        self.entry_val = ctk.CTkEntry(frame_pag, placeholder_text="0.00", font=("Arial", 14))
        self.entry_val.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_val.bind("<FocusOut>", self.atualizar_totais)

        ctk.CTkLabel(frame_pag, text="Taxa Entrega (R$):").pack(anchor="w", padx=20)
        self.entry_taxa = ctk.CTkEntry(frame_pag, placeholder_text="0.00")
        self.entry_taxa.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_taxa.bind("<FocusOut>", self.atualizar_totais)

        ctk.CTkLabel(frame_pag, text="Forma de Pagamento:").pack(anchor="w", padx=20, pady=(10, 0))
        self.combo_pagamento = ctk.CTkComboBox(frame_pag, values=["Dinheiro", "Pix", "Cartão"], command=self.mudou_forma_pagamento)
        self.combo_pagamento.pack(fill="x", padx=20, pady=(0, 10))
        self.combo_pagamento.set("Dinheiro") 

        self.lbl_total = ctk.CTkLabel(frame_pag, text="TOTAL: R$ 0.00", font=("Arial", 28, "bold"))
        self.lbl_total.pack(pady=10)

        ctk.CTkFrame(frame_pag, height=2, fg_color="gray").pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(frame_pag, text="Valor em Dinheiro (Para Troco):").pack(anchor="w", padx=20)
        self.entry_troco = ctk.CTkEntry(frame_pag, placeholder_text="Ex: 50.00")
        self.entry_troco.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_troco.bind("<KeyRelease>", self.calcular_troco_dinamico)

        self.lbl_troco = ctk.CTkLabel(frame_pag, text="Troco: R$ 0.00", text_color="#F1C40F", font=("Arial", 18, "bold"))
        self.lbl_troco.pack(pady=5)

        self.btn_imprimir = ctk.CTkButton(frame_pag, text="FINALIZAR E IMPRIMIR", command=self.finalizar, height=55, fg_color="#2CC985", text_color="black", font=("Arial", 15, "bold"))
        self.btn_imprimir.pack(fill="x", padx=20, pady=(30, 10))
        
        frame_botoes = ctk.CTkFrame(frame_pag, fg_color="transparent")
        frame_botoes.pack(fill="x", padx=20)

        self.btn_limpar = ctk.CTkButton(frame_botoes, text="LIMPAR TELA", command=self.limpar_tela, fg_color="#C0392B", width=120)
        self.btn_limpar.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_relatorio = ctk.CTkButton(frame_botoes, text="RELATÓRIO DIA", command=self.abrir_janela_relatorio, fg_color="#555", width=120)
        self.btn_relatorio.pack(side="right", fill="x", expand=True, padx=(5, 0))

    # ---------------- FORMATACAO ----------------
    def limpar_telefone(self, tel):
        numeros = "".join(filter(str.isdigit, tel))
        tam = len(numeros)
        if tam == 8 or tam == 9: return f"{DDD_PADRAO}{numeros}"
        return numeros

    def formatar_telefone_visual(self, tel):
        numeros = "".join(filter(str.isdigit, tel))
        tam = len(numeros)
        if tam == 11: return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
        elif tam == 10: return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
        elif tam == 9: return f"{numeros[:5]}-{numeros[5:]}"
        elif tam == 8: return f"{numeros[:4]}-{numeros[4:]}"
        return tel

    def formatar_float(self, valor_str):
        try: return float(valor_str.replace(",", ".").strip())
        except: return 0.0
    
    # ---------------- LÓGICA GERAL ----------------
    def limpar_tela(self):
        self.entry_tel.delete(0, "end"); self.entry_nome.delete(0, "end")
        self.entry_rua.delete(0, "end"); self.entry_num.delete(0, "end")
        self.entry_bairro.delete(0, "end"); self.entry_ref.delete(0, "end")
        self.entry_val.delete(0, "end"); self.entry_taxa.delete(0, "end")
        self.entry_troco.delete(0, "end")
        self.lbl_total.configure(text="TOTAL: R$ 0.00"); self.lbl_troco.configure(text="Troco: R$ 0.00")
        self.combo_pagamento.set("Dinheiro"); self.entry_troco.configure(state="normal")
        self.var_entregador.set("Entregador da Manhã")
        self.entry_tel.focus_set()

    def mudou_forma_pagamento(self, escolha):
        if escolha == "Dinheiro":
            self.entry_troco.configure(state="normal")
            self.lbl_troco.configure(text="Troco: R$ 0.00")
        else:
            self.entry_troco.delete(0, "end")
            self.entry_troco.configure(state="disabled")
            self.lbl_troco.configure(text="JÁ PAGO (Sem Troco)")

    def buscar_cliente(self, event=None):
        tel_bruto = self.entry_tel.get()
        tel_limpo = self.limpar_telefone(tel_bruto)
        if not tel_limpo: return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT nome, rua, numero, bairro, referencia FROM clientes WHERE telefone = ?", (tel_limpo,))
            res = cursor.fetchone()
        except: res = None
        conn.close()
        if res:
            self.entry_nome.delete(0, "end"); self.entry_nome.insert(0, res[0])
            if res[1]: self.entry_rua.delete(0, "end"); self.entry_rua.insert(0, res[1])
            if res[2]: self.entry_num.delete(0, "end"); self.entry_num.insert(0, res[2])
            if res[3]: self.entry_bairro.delete(0, "end"); self.entry_bairro.insert(0, res[3])
            if res[4]: self.entry_ref.delete(0, "end"); self.entry_ref.insert(0, res[4])
            self.entry_tel.delete(0, "end"); self.entry_tel.insert(0, self.formatar_telefone_visual(tel_limpo))

    def atualizar_totais(self, event=None):
        val_prod = self.formatar_float(self.entry_val.get())
        val_taxa = self.formatar_float(self.entry_taxa.get())
        if event:
            self.entry_val.delete(0, "end"); self.entry_val.insert(0, f"{val_prod:.2f}")
            self.entry_taxa.delete(0, "end"); self.entry_taxa.insert(0, f"{val_taxa:.2f}")
        total = val_prod + val_taxa
        self.lbl_total.configure(text=f"TOTAL: R$ {total:.2f}")
        return total

    def calcular_troco_dinamico(self, event=None):
        if self.combo_pagamento.get() != "Dinheiro": return
        total = self.atualizar_totais(event=None)
        pago = self.formatar_float(self.entry_troco.get())
        if pago > total: self.lbl_troco.configure(text=f"TROCO: R$ {pago - total:.2f}")
        else: self.lbl_troco.configure(text="Troco: R$ 0.00")

    def imprimir_cupom_windows(self, texto):
        try:
            pasta_segura = get_app_path()
            filename = os.path.join(pasta_segura, "cupom_temp.txt")
            with open(filename, "w", encoding="utf-8") as f: f.write(texto)
        except Exception as e:
            messagebox.showerror("Erro de Permissão", f"Erro arquivo:\n{e}")
            return
        try: win32api.ShellExecute(0, "print", filename, None, ".", 0)
        except: os.startfile(filename)

    def finalizar(self):
        tel_bruto = self.entry_tel.get()
        tel_limpo = self.limpar_telefone(tel_bruto)
        nome = self.entry_nome.get().strip()
        rua = self.entry_rua.get().strip()
        num = self.entry_num.get().strip()
        bairro = self.entry_bairro.get().strip()
        ref = self.entry_ref.get().strip()
        
        if not tel_limpo or not nome:
            messagebox.showwarning("Campo Vazio", "Preencha Telefone e Nome.")
            return

        total = self.atualizar_totais()
        if total <= 0:
            messagebox.showwarning("Valor Zerado", "Total do pedido zerado.")
            return

        forma_pag = self.combo_pagamento.get()
        pago = self.formatar_float(self.entry_troco.get())
        
        if forma_pag == "Dinheiro":
            troco_msg = f"R$ {pago - total:.2f}" if pago > total else "Nao precisa"
            pago_msg = f"R$ {pago:.2f}"
        else:
            troco_msg = "NAO (JA PAGO)"
            pago_msg = f"R$ {total:.2f}"

        largura_max = 40 
        rua_fmt = textwrap.fill(f"{rua}, {num}", width=largura_max)
        ref_fmt = textwrap.fill(f"Obs: {ref}", width=largura_max)
        tel_fmt_papel = self.formatar_telefone_visual(tel_limpo)
        val_prod = self.formatar_float(self.entry_val.get())
        val_taxa = self.formatar_float(self.entry_taxa.get())

        cupom = f"""
------------------------------------------
           FARMACIA TOTALPHARMA           
------------------------------------------
DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}
------------------------------------------
CLIENTE: {nome}
TEL:     {tel_fmt_papel}
------------------------------------------
ENDERECO DE ENTREGA:
{rua_fmt}
Bairro: {bairro}
------------------------------------------
{ref_fmt}
------------------------------------------
ENTREGADOR: {self.var_entregador.get()}
------------------------------------------
{'ITEM':<20} {'VALOR':>18}
{'Subtotal':<20} R$ {val_prod:>10.2f}
{'Taxa':<20} R$ {val_taxa:>10.2f}
{'TOTAL A PAGAR':<20} R$ {total:>10.2f}
------------------------------------------
FORMA PAG: {forma_pag.upper()}
Valor Pago:          {pago_msg:>13}
TROCO:               {troco_msg:>13}
------------------------------------------
        Obrigado pela preferencia!        
------------------------------------------
"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO clientes (telefone, nome, rua, numero, bairro, referencia)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tel_limpo, nome, rua, num, bairro, ref))
            cursor.execute("""
                INSERT INTO pedidos (data, cliente_tel, entregador, valor_total, metodo_pagamento) 
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().strftime("%Y-%m-%d"), tel_limpo, self.var_entregador.get(), total, forma_pag))
            conn.commit()
        except Exception as e:
            messagebox.showerror("Erro BD", str(e))
        conn.close()

        self.imprimir_cupom_windows(cupom)
        self.limpar_tela()

    # ---------------- NOVO RELATÓRIO AVANÇADO ----------------
    def abrir_janela_relatorio(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        
        # Conecta no BD para pegar dados
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Total Geral
        cursor.execute("SELECT count(*), sum(valor_total) FROM pedidos WHERE data = ?", (hoje,))
        qtd_total, receita_total = cursor.fetchone()
        receita_total = receita_total if receita_total else 0.0
        ticket_medio = receita_total / qtd_total if qtd_total > 0 else 0.0

        # 2. Entregadores
        cursor.execute("SELECT entregador, count(*) FROM pedidos WHERE data = ? GROUP BY entregador", (hoje,))
        dados_entregadores = cursor.fetchall() # Lista de (Nome, Qtd)

        # 3. Pagamentos
        cursor.execute("SELECT metodo_pagamento, sum(valor_total) FROM pedidos WHERE data = ? GROUP BY metodo_pagamento", (hoje,))
        dados_pagamentos = cursor.fetchall() # Lista de (Tipo, Valor)

        conn.close()

        # --- CRIAÇÃO DA JANELA POP-UP ---
        top = ctk.CTkToplevel(self)
        top.title(f"Relatório do Dia ({datetime.now().strftime('%d/%m')})")
        top.geometry("400x550")
        top.attributes("-topmost", True) # Força ficar na frente

        # Cabeçalho
        ctk.CTkLabel(top, text="RESUMO FINANCEIRO", font=("Arial", 16, "bold"), text_color="#2CC985").pack(pady=(15,5))
        ctk.CTkLabel(top, text=f"Faturamento: R$ {receita_total:.2f}", font=("Arial", 20, "bold")).pack()
        ctk.CTkLabel(top, text=f"Total Entregas: {qtd_total}  |  Ticket Médio: R$ {ticket_medio:.2f}").pack(pady=5)

        ctk.CTkFrame(top, height=2, fg_color="gray").pack(fill="x", padx=20, pady=10)

        # Seção Entregadores
        ctk.CTkLabel(top, text="POR ENTREGADOR (Qtd)", font=("Arial", 14, "bold")).pack()
        if not dados_entregadores:
            ctk.CTkLabel(top, text="Nenhuma entrega hoje.").pack()
        else:
            for nome, qtd in dados_entregadores:
                ctk.CTkLabel(top, text=f"{nome}: {qtd} entregas").pack(anchor="w", padx=40)

        ctk.CTkFrame(top, height=2, fg_color="gray").pack(fill="x", padx=20, pady=10)

        # Seção Pagamentos
        ctk.CTkLabel(top, text="POR PAGAMENTO (R$)", font=("Arial", 14, "bold")).pack()
        if not dados_pagamentos:
            ctk.CTkLabel(top, text="Nenhum pagamento hoje.").pack()
        else:
            for tipo, val in dados_pagamentos:
                tipo_str = tipo if tipo else "Outros"
                ctk.CTkLabel(top, text=f"{tipo_str}: R$ {val:.2f}").pack(anchor="w", padx=40)

        ctk.CTkFrame(top, height=2, fg_color="gray").pack(fill="x", padx=20, pady=20)

        # Botão Exportar Excel (CSV)
        ctk.CTkButton(top, text="SALVAR EM EXCEL (CSV)", command=lambda: self.exportar_csv(hoje), fg_color="#2980B9").pack(fill="x", padx=20, pady=10)

    def exportar_csv(self, data_hoje):
        try:
            # Salva na Área de Trabalho para ser fácil achar
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = os.path.join(desktop, f"Relatorio_Farmacia_{data_hoje}.csv")

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.data, c.nome, p.entregador, p.valor_total, p.metodo_pagamento
                FROM pedidos p
                JOIN clientes c ON p.cliente_tel = c.telefone
                WHERE p.data = ?
            """, (data_hoje,))
            dados = cursor.fetchall()
            conn.close()

            if not dados:
                messagebox.showinfo("Vazio", "Não há dados para exportar hoje.")
                return

            # Escreve CSV
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';') # Ponto e virgula é melhor pro Excel Brasil
                writer.writerow(["ID", "Data", "Cliente", "Entregador", "Valor (R$)", "Pagamento"])
                for linha in dados:
                    # Formata o valor float para string com vírgula (padrão BR)
                    linha_fmt = list(linha)
                    linha_fmt[4] = f"{linha[4]:.2f}".replace(".", ",")
                    writer.writerow(linha_fmt)
            
            messagebox.showinfo("Sucesso", f"Relatório salvo na Área de Trabalho!\n\nArquivo: {os.path.basename(filename)}")
            
        except Exception as e:
            messagebox.showerror("Erro Exportação", str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()