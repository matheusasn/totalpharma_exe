import customtkinter as ctk
import sqlite3
from tkinter import messagebox
from datetime import datetime
import platform
import os

# -------------- CONFIGURAÇÕES INICIAIS --------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def init_db():
    try:
        # Pega caminho seguro para o DB (AppData ou Home)
        app_data = os.getenv('APPDATA') if platform.system() == "Windows" else os.path.expanduser('~')
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
                FOREIGN KEY(cliente_tel) REFERENCES clientes(telefone)
            )
        """)
        conn.commit()
        conn.close()
        return db_path
    except Exception as e:
        messagebox.showerror("Erro Banco de Dados", str(e))
        return "dados_farmacia.db"

DB_PATH = init_db()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TotalPharma - PDV Delivery")
        self.geometry("800x600") # Janela mais larga para 2 colunas
        
        # Layout Principal (Grid 2 colunas)
        self.grid_columnconfigure(0, weight=1) # Coluna Esquerda (Cliente)
        self.grid_columnconfigure(1, weight=1) # Coluna Direita (Pagamento)
        self.grid_rowconfigure(0, weight=1)

        self.criar_coluna_cliente()
        self.criar_coluna_pagamento()

    # ---------------- UI: COLUNA ESQUERDA (CLIENTE) ----------------
    def criar_coluna_cliente(self):
        frame_cli = ctk.CTkFrame(self)
        frame_cli.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(frame_cli, text="DADOS DO CLIENTE", font=("Arial", 16, "bold"), text_color="#3B8ED0").pack(pady=(15,10))

        # Telefone
        ctk.CTkLabel(frame_cli, text="Telefone (Digite e aperte Tab):").pack(anchor="w", padx=15)
        self.entry_tel = ctk.CTkEntry(frame_cli, placeholder_text="Somente números")
        self.entry_tel.pack(fill="x", padx=15, pady=(0, 10))
        self.entry_tel.bind("<FocusOut>", self.buscar_cliente) # Busca ao sair do campo

        # Nome
        ctk.CTkLabel(frame_cli, text="Nome do Cliente:").pack(anchor="w", padx=15)
        self.entry_nome = ctk.CTkEntry(frame_cli)
        self.entry_nome.pack(fill="x", padx=15, pady=(0, 10))

        # Endereço
        ctk.CTkLabel(frame_cli, text="Endereço Completo:").pack(anchor="w", padx=15)
        self.txt_end = ctk.CTkTextbox(frame_cli, height=100)
        self.txt_end.pack(fill="x", padx=15, pady=(0, 10))

        # Entregador
        ctk.CTkLabel(frame_cli, text="Selecione o Entregador:").pack(anchor="w", padx=15, pady=(10,0))
        self.var_entregador = ctk.StringVar(value="Moto 1")
        frame_radio = ctk.CTkFrame(frame_cli, fg_color="transparent")
        frame_radio.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkRadioButton(frame_radio, text="Moto 1", variable=self.var_entregador, value="Moto 1").pack(side="left", padx=5)
        ctk.CTkRadioButton(frame_radio, text="Moto 2", variable=self.var_entregador, value="Moto 2").pack(side="left", padx=5)

    # ---------------- UI: COLUNA DIREITA (PAGAMENTO) ----------------
    def criar_coluna_pagamento(self):
        frame_pag = ctk.CTkFrame(self)
        frame_pag.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(frame_pag, text="VALORES DO PEDIDO", font=("Arial", 16, "bold"), text_color="#2CC985").pack(pady=(15,10))

        # Valor Produtos
        ctk.CTkLabel(frame_pag, text="Valor dos Produtos (R$):").pack(anchor="w", padx=20)
        self.entry_val = ctk.CTkEntry(frame_pag, placeholder_text="0.00", font=("Arial", 14))
        self.entry_val.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_val.bind("<FocusOut>", self.atualizar_totais) # Formata ao sair

        # Taxa
        ctk.CTkLabel(frame_pag, text="Taxa de Entrega (R$):").pack(anchor="w", padx=20)
        self.entry_taxa = ctk.CTkEntry(frame_pag, placeholder_text="0.00")
        self.entry_taxa.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_taxa.bind("<FocusOut>", self.atualizar_totais)

        # TOTAL (Label Grande)
        self.lbl_total = ctk.CTkLabel(frame_pag, text="TOTAL: R$ 0.00", font=("Arial", 24, "bold"))
        self.lbl_total.pack(pady=15)

        ctk.CTkFrame(frame_pag, height=2, fg_color="gray").pack(fill="x", padx=20, pady=5)

        # Troco
        ctk.CTkLabel(frame_pag, text="Cliente vai pagar com quanto? (Para Troco)").pack(anchor="w", padx=20)
        self.entry_troco = ctk.CTkEntry(frame_pag, placeholder_text="Ex: 50.00")
        self.entry_troco.pack(fill="x", padx=20, pady=(0, 10))
        self.entry_troco.bind("<KeyRelease>", self.calcular_troco_dinamico) # Calcula enquanto digita

        self.lbl_troco = ctk.CTkLabel(frame_pag, text="Troco: R$ 0.00", text_color="yellow", font=("Arial", 14, "bold"))
        self.lbl_troco.pack(pady=5)

        # Botões
        ctk.CTkButton(frame_pag, text="CONCLUIR E IMPRIMIR", command=self.finalizar, height=50, fg_color="#2CC985", text_color="black", font=("Arial", 14, "bold")).pack(fill="x", padx=20, pady=(30, 10))
        ctk.CTkButton(frame_pag, text="Ver Relatório do Dia", command=self.ver_relatorio, fg_color="#444").pack(fill="x", padx=20)

    # ---------------- LÓGICA ----------------
    def buscar_cliente(self, event=None):
        tel = self.entry_tel.get().strip()
        if not tel: return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nome, endereco FROM clientes WHERE telefone = ?", (tel,))
        res = cursor.fetchone()
        conn.close()
        
        if res:
            self.entry_nome.delete(0, "end")
            self.entry_nome.insert(0, res[0])
            self.txt_end.delete("1.0", "end")
            self.txt_end.insert("1.0", res[1])

    def formatar_float(self, valor_str):
        try:
            # Troca virgula por ponto e remove letras
            limpo = valor_str.replace(",", ".").strip()
            if not limpo: return 0.0
            return float(limpo)
        except:
            return 0.0

    def atualizar_totais(self, event=None):
        # 1. Pega valores
        val_prod = self.formatar_float(self.entry_val.get())
        val_taxa = self.formatar_float(self.entry_taxa.get())
        
        # 2. Formata bonitinho nos campos (Ex: vira 5.00)
        if event: # Só reescreve se foi evento de sair do campo
            self.entry_val.delete(0, "end")
            self.entry_val.insert(0, f"{val_prod:.2f}")
            self.entry_taxa.delete(0, "end")
            self.entry_taxa.insert(0, f"{val_taxa:.2f}")

        # 3. Atualiza Label Total
        total = val_prod + val_taxa
        self.lbl_total.configure(text=f"TOTAL: R$ {total:.2f}")
        return total

    def calcular_troco_dinamico(self, event=None):
        total = self.atualizar_totais(event=None)
        pago = self.formatar_float(self.entry_troco.get())
        
        if pago > total:
            troco = pago - total
            self.lbl_troco.configure(text=f"LEVAR DE TROCO: R$ {troco:.2f}")
        else:
            self.lbl_troco.configure(text="Troco: R$ 0.00")

    def enviar_impressora(self, texto):
        if platform.system() == "Windows":
            try:
                # Cria arquivo temporario
                filename = "cupom_temp.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(texto)
                
                # NOVO COMANDO DE IMPRESSÃO (Mais limpo)
                # os.startfile manda o arquivo para a aplicação padrão associada
                # A ação "print" tenta imprimir direto
                os.startfile(filename, "print")
                
            except Exception as e:
                messagebox.showerror("Erro Impressão", f"Verifique a impressora padrão.\nErro: {e}")
        else:
            # Simulação no Mac
            print(texto)
            messagebox.showinfo("Impressão (Simulada)", "Cupom gerado no console (Mac)")

    def finalizar(self):
        tel = self.entry_tel.get().strip()
        nome = self.entry_nome.get().strip()
        end = self.txt_end.get("1.0", "end").strip()
        
        if not tel or not nome:
            messagebox.showwarning("Aviso", "Preencha Telefone e Nome")
            return

        total = self.atualizar_totais()
        if total <= 0:
            messagebox.showwarning("Aviso", "O valor total está zerado!")
            return

        # Monta Cupom
        pago = self.formatar_float(self.entry_troco.get())
        troco_msg = f"R$ {pago - total:.2f}" if pago > total else "Nao precisa"
        
        cupom = f"""
--------------------------------
      FARMACIA TOTALPHARMA      
--------------------------------
DATA: {datetime.now().strftime('%d/%m/%Y %H:%M')}
--------------------------------
CLIENTE: {nome}
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
Pago:      R$ {pago:.2f}
TROCO:     {troco_msg}
--------------------------------
"""
        # Salva BD
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO clientes VALUES (?, ?, ?)", (tel, nome, end))
        cursor.execute(
            "INSERT INTO pedidos (data, cliente_tel, entregador, valor_total) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d"), tel, self.var_entregador.get(), total)
        )
        conn.commit()
        conn.close()

        self.enviar_impressora(cupom)
        
        # Limpa campos de valor para proximo
        self.entry_val.delete(0, "end")
        self.entry_taxa.delete(0, "end")
        self.entry_troco.delete(0, "end")
        self.lbl_total.configure(text="TOTAL: R$ 0.00")
        self.lbl_troco.configure(text="Troco: R$ 0.00")
        self.entry_tel.focus_set()

    def ver_relatorio(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*), sum(valor_total) FROM pedidos WHERE data = ?", (hoje,))
        qtd, total = cursor.fetchone()
        total = total if total else 0.0
        conn.close()
        
        msg = f"Resumo de Hoje ({datetime.now().strftime('%d/%m')}):\n\n"
        msg += f"Entregas: {qtd}\n"
        msg += f"Faturamento: R$ {total:.2f}"
        messagebox.showinfo("Relatório", msg)

if __name__ == "__main__":
    app = App()
    app.mainloop()