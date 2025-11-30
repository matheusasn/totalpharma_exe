import customtkinter as ctk
import sqlite3
from tkinter import messagebox
from datetime import datetime
import os
import sys

# Importações exclusivas do Windows
import win32api
import win32print
import ctypes # Para o ícone na barra de tarefas

# -------------- CONFIGURAÇÕES INICIAIS --------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def configurar_identidade_windows():
    """Força o ícone a aparecer na Barra de Tarefas do Windows"""
    try:
        myappid = 'totalpharma.delivery.pdv.vfinal' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass

configurar_identidade_windows()

def init_db():
    try:
        app_data = os.getenv('APPDATA')
        pasta_app = os.path.join(app_data, "TotalPharma")
        
        if not os.path.exists(pasta_app):
            os.makedirs(pasta_app)
        
        db_path = os.path.join(pasta_app, "dados_farmacia.db")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                telefone TEXT PRIMARY KEY,
                nome TEXT,
                endereco TEXT
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
        
        try:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN metodo_pagamento TEXT")
        except:
            pass

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
        self.geometry("900x650")
        
        # --- ÍCONE ---
        caminho_icone = "farmacia.ico"
        if os.path.exists(caminho_icone):
            try:
                self.iconbitmap(caminho_icone)
                self.wm_iconbitmap(caminho_icone)
            except:
                pass 
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.criar_coluna_cliente()
        self.criar_coluna_pagamento()

    def criar_coluna_cliente(self):
        frame_cli = ctk.CTkFrame(self)
        frame_cli.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(frame_cli, text="DADOS DO CLIENTE", font=("Arial", 16, "bold"), text_color="#3B8ED0").pack(pady=(15,10))

        ctk.CTkLabel(frame_cli, text="Telefone (Digite e Tab):").pack(anchor="w", padx=15)
        self.entry_tel = ctk.CTkEntry(frame_cli, placeholder_text="Somente números")
        self.entry_tel.pack(fill="x", padx=15, pady=(0, 10))
        self.entry_tel.bind("<FocusOut>", self.buscar_cliente)

        ctk.CTkLabel(frame_cli, text="Nome do Cliente:").pack(anchor="w", padx=15)
        self.entry_nome = ctk.CTkEntry(frame_cli)
        self.entry_nome.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(frame_cli, text="Endereço Completo:").pack(anchor="w", padx=15)
        self.txt_end = ctk.CTkTextbox(frame_cli, height=100)
        self.txt_end.pack(fill="x", padx=15, pady=(0, 10))

        # --- SEUS TEXTOS PERSONALIZADOS AQUI ---
        ctk.CTkLabel(frame_cli, text="Selecione o Entregador:").pack(anchor="w", padx=15, pady=(10,0))
        self.var_entregador = ctk.StringVar(value="Entregador da Manhã")
        
        frame_radio = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_radio.pack(fill="x", padx=15, pady=5)
        
        # Opções personalizadas
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

        # Seletor de Pagamento
        ctk.CTkLabel(frame_pag, text="Forma de Pagamento:").pack(anchor="w", padx=20, pady=(10, 0))
        self.combo_pagamento = ctk.CTkComboBox(frame_pag, values=["Dinheiro", "Pix", "Cartão"], command=self.mudou_forma_pagamento)
        self.combo_pagamento.pack(fill="x", padx=20, pady=(0, 10))
        self.combo_pagamento.set("Dinheiro") 

        # Total
        self.lbl_total = ctk.CTkLabel(frame_pag, text="TOTAL: R$ 0.00", font=("Arial", 28, "bold"))
        self.lbl_total.pack(pady=10)

        ctk.CTkFrame(frame_pag, height=2, fg_color="gray").pack(fill="x", padx=20, pady=5)

        # Troco
        ctk.CTkLabel(frame_pag, text="Valor em Dinheiro (Para Troco):").pack(anchor="w", padx=20)
        self.entry_troco = ctk.CTkEntry(frame_pag, placeholder_text="Ex: 50.00")
        self.entry_troco.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_troco.bind("<KeyRelease>", self.calcular_troco_dinamico)

        self.lbl_troco = ctk.CTkLabel(frame_pag, text="Troco: R$ 0.00", text_color="#F1C40F", font=("Arial", 18, "bold"))
        self.lbl_troco.pack(pady=5)

        # Botões
        self.btn_imprimir = ctk.CTkButton(frame_pag, text="FINALIZAR E IMPRIMIR", command=self.finalizar, height=55, fg_color="#2CC985", text_color="black", font=("Arial", 15, "bold"))
        self.btn_imprimir.pack(fill="x", padx=20, pady=(30, 10))
        
        ctk.CTkButton(frame_pag, text="Relatório Diário", command=self.ver_relatorio, fg_color="#444").pack(fill="x", padx=20)

    # ---------------- LÓGICA ----------------
    def mudou_forma_pagamento(self, escolha):
        if escolha == "Dinheiro":
            self.entry_troco.configure(state="normal")
            self.lbl_troco.configure(text="Troco: R$ 0.00")
        else:
            self.entry_troco.delete(0, "end")
            self.entry_troco.configure(state="disabled")
            self.lbl_troco.configure(text="JÁ PAGO (Sem Troco)")

    def buscar_cliente(self, event=None):
        tel = self.entry_tel.get().strip()
        if not tel: return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, endereco FROM clientes WHERE telefone = ?", (tel,))
        res = cursor.fetchone()
        conn.close()
        if res:
            self.entry_nome.delete(0, "end"); self.entry_nome.insert(0, res[0])
            self.txt_end.delete("1.0", "end"); self.txt_end.insert("1.0", res[1])

    def formatar_float(self, valor_str):
        try: return float(valor_str.replace(",", ".").strip())
        except: return 0.0

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
        if self.combo_pagamento.get() != "Dinheiro":
            return
            
        total = self.atualizar_totais(event=None)
        pago = self.formatar_float(self.entry_troco.get())
        if pago > total:
            self.lbl_troco.configure(text=f"TROCO: R$ {pago - total:.2f}")
        else:
            self.lbl_troco.configure(text="Troco: R$ 0.00")

    def imprimir_cupom_windows(self, texto):
        filename = os.path.abspath("cupom_temp.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(texto)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro arquivo: {e}")
            return

        try:
            printer_name = win32print.GetDefaultPrinter()
            win32api.ShellExecute(0, "print", filename, None, ".", 0)
        except Exception as e:
            messagebox.showwarning("Atenção", f"Erro na impressão direta.\nAbrindo manual.")
            os.startfile(filename)

    def finalizar(self):
        tel = self.entry_tel.get().strip()
        nome = self.entry_nome.get().strip()
        end = self.txt_end.get("1.0", "end").strip()
        
        if not tel or not nome:
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
            pago_msg = f"{forma_pag.upper()}"

        cupom = f"""
--------------------------------
    FARMACIA TOTALPHARMA
--------------------------------
DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}
--------------------------------
CLI: {nome}
TEL: {tel}
--------------------------------
ENDERECO:
{end}
--------------------------------
ENTREGADOR: {self.var_entregador.get()}
--------------------------------
Subtotal:  R$ {self.formatar_float(self.entry_val.get()):.2f}
Taxa:      R$ {self.formatar_float(self.entry_taxa.get()):.2f}
TOTAL:     R$ {total:.2f}
--------------------------------
FORMA PAG: {forma_pag.upper()}
Valor:     {pago_msg}
TROCO:     {troco_msg}
--------------------------------
 Obrigado pela preferencia!
--------------------------------
"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO clientes VALUES (?, ?, ?)", (tel, nome, end))
        cursor.execute("INSERT INTO pedidos (data, cliente_tel, entregador, valor_total, metodo_pagamento) VALUES (?, ?, ?, ?, ?)", 
                       (datetime.now().strftime("%Y-%m-%d"), tel, self.var_entregador.get(), total, forma_pag))
        conn.commit()
        conn.close()

        self.imprimir_cupom_windows(cupom)
        
        self.entry_val.delete(0, "end"); self.entry_taxa.delete(0, "end"); self.entry_troco.delete(0, "end")
        self.lbl_total.configure(text="TOTAL: R$ 0.00")
        self.lbl_troco.configure(text="Troco: R$ 0.00")
        self.combo_pagamento.set("Dinheiro")
        self.entry_troco.configure(state="normal")
        self.entry_tel.focus_set()

    def ver_relatorio(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT count(*), sum(valor_total) FROM pedidos WHERE data = ?", (hoje,))
        qtd, total = cursor.fetchone()
        
        msg = f"RELATÓRIO DE HOJE ({datetime.now().strftime('%d/%m')}):\n\n"
        msg += f"Total Entregas: {qtd}\n"
        msg += f"Faturamento Total: R$ {total if total else 0:.2f}\n\n"
        msg += "--- POR PAGAMENTO ---\n"
        
        try:
            cursor.execute("SELECT metodo_pagamento, sum(valor_total) FROM pedidos WHERE data = ? GROUP BY metodo_pagamento", (hoje,))
            for tipo, val in cursor.fetchall():
                tipo_nome = tipo if tipo else "Desconhecido"
                msg += f"{tipo_nome}: R$ {val:.2f}\n"
        except:
            pass

        conn.close()
        messagebox.showinfo("Relatório", msg)

if __name__ == "__main__":
    app = App()
    app.mainloop()