import customtkinter as ctk
import sqlite3
from tkinter import messagebox
from datetime import datetime
import platform
import os

# -------------- BANCO DE DADOS --------------
def init_db():
    conn = sqlite3.connect("dados_farmacia.db")
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

init_db()

# -------------- APP / TEMA --------------
ctk.set_appearance_mode("dark")      # "dark" ou "light"
ctk.set_default_color_theme("blue")  # ou "green", "dark-blue"

app = ctk.CTk()
app.title("Farmácia Delivery - CTk")
app.geometry("500x780")

# Frame principal
main = ctk.CTkFrame(app, corner_radius=10)
main.pack(fill="both", expand=True, padx=20, pady=20)

for i in range(0, 16):
    main.rowconfigure(i, weight=0)
main.columnconfigure(0, weight=1)

# -------------- FUNÇÕES --------------
def buscar_cliente(event=None):
    tel = entry_tel.get().strip()
    if not tel:
        return
    
    conn = sqlite3.connect("dados_farmacia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nome, endereco FROM clientes WHERE telefone = ?", (tel,))
    res = cursor.fetchone()
    conn.close()
    
    if res:
        entry_nome.delete(0, "end")
        entry_nome.insert(0, res[0])
        txt_end.delete("1.0", "end")
        txt_end.insert("1.0", res[1])

def enviar_impressora(texto):
    if platform.system() == "Windows":
        try:
            filename = "print_temp.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(texto)
            os.system(f"notepad /p {filename}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))
    else:
        top = ctk.CTkToplevel(app)
        top.title("Cupom")
        top.geometry("400x500")
        txt = ctk.CTkTextbox(top, font=("Courier", 14))
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", texto)
        txt.configure(state="disabled")

def finalizar():
    tel = entry_tel.get().strip()
    nome = entry_nome.get().strip()
    end = txt_end.get("1.0", "end").strip()
    
    if not tel or not nome:
        messagebox.showwarning("Aviso", "Preencha Telefone e Nome")
        return

    try:
        v_prod = float((entry_val.get() or "0").replace(",", "."))
        v_taxa = float((entry_taxa.get() or "0").replace(",", "."))
        total = v_prod + v_taxa
        
        troco_msg = "NAO PRECISA"
        v_pg = float((entry_troco.get() or "0").replace(",", "."))
        if v_pg > total:
            troco_msg = f"LEVAR: R$ {v_pg - total:.2f}"
    except ValueError:
        messagebox.showerror("Erro", "Valores inválidos")
        return

    # Salvar no BD
    conn = sqlite3.connect("dados_farmacia.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO clientes VALUES (?, ?, ?)", (tel, nome, end))
    hoje = datetime.now().strftime("%Y-%m-%d")
    entregador_selecionado = var_entregador.get()
    cursor.execute(
        "INSERT INTO pedidos (data, cliente_tel, entregador, valor_total) VALUES (?, ?, ?, ?)",
        (hoje, tel, entregador_selecionado, total)
    )
    conn.commit()
    conn.close()

    cupom = f"""
--------------------------------
          TotalPharma             
--------------------------------
DATA: {datetime.now().strftime('%d/%m %H:%M')}
--------------------------------
CLI: {nome}
TEL: {tel}
--------------------------------
ENDEREÇO:
{end}
--------------------------------
MOTOBOY: {entregador_selecionado}
--------------------------------
Valor:     R$ {v_prod:.2f}
Taxa:      R$ {v_taxa:.2f}
TOTAL:     R$ {total:.2f}
--------------------------------
TROCO: {troco_msg}
--------------------------------
"""
    enviar_impressora(cupom)

    entry_val.delete(0, "end")
    entry_troco.delete(0, "end")
    entry_tel.focus_set()

def ver_relatorio():
    top = ctk.CTkToplevel(app)
    top.title("Relatório")
    top.geometry("300x200")
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("dados_farmacia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT count(*), sum(valor_total) FROM pedidos WHERE data = ?", (hoje,))
    qtd, total = cursor.fetchone()
    total = total if total else 0
    conn.close()
    
    ctk.CTkLabel(top, text=f"Pedidos Hoje: {qtd}", font=("Arial", 16)).pack(pady=10)
    ctk.CTkLabel(top, text=f"Total: R$ {total:.2f}", font=("Arial", 18, "bold")).pack(pady=10)

# -------------- CAMPOS --------------

# Telefone
ctk.CTkLabel(main, text="TELEFONE (Tab para buscar):", anchor="w").grid(row=0, column=0, sticky="w")
entry_tel = ctk.CTkEntry(main, placeholder_text="(83) 99999-9999")
entry_tel.grid(row=1, column=0, sticky="ew", pady=(0, 10))
entry_tel.bind("<FocusOut>", buscar_cliente)

# Nome
ctk.CTkLabel(main, text="NOME DO CLIENTE:", anchor="w").grid(row=2, column=0, sticky="w")
entry_nome = ctk.CTkEntry(main, placeholder_text="Nome completo")
entry_nome.grid(row=3, column=0, sticky="ew", pady=(0, 10))

# Endereço
ctk.CTkLabel(main, text="ENDEREÇO COMPLETO:", anchor="w").grid(row=4, column=0, sticky="w")
txt_end = ctk.CTkTextbox(main, height=80)
txt_end.grid(row=5, column=0, sticky="ew", pady=(0, 10))

# Valor produtos
ctk.CTkLabel(main, text="VALOR DOS PRODUTOS (R$):", anchor="w").grid(row=6, column=0, sticky="w")
entry_val = ctk.CTkEntry(main, placeholder_text="0,00")
entry_val.grid(row=7, column=0, sticky="ew", pady=(0, 10))

# Taxa
ctk.CTkLabel(main, text="TAXA DE ENTREGA (R$):", anchor="w").grid(row=8, column=0, sticky="w")
entry_taxa = ctk.CTkEntry(main)
entry_taxa.insert(0, "5.00")
entry_taxa.grid(row=9, column=0, sticky="ew", pady=(0, 10))

# Troco
ctk.CTkLabel(main, text="TROCO PARA QUANTO?", anchor="w").grid(row=10, column=0, sticky="w")
entry_troco = ctk.CTkEntry(main, placeholder_text="Valor entregue pelo cliente")
entry_troco.grid(row=11, column=0, sticky="ew", pady=(0, 15))

# Entregador
ctk.CTkLabel(main, text="SELECIONE O ENTREGADOR:", anchor="w").grid(row=12, column=0, sticky="w")

frame_moto = ctk.CTkFrame(main, fg_color="transparent")
frame_moto.grid(row=13, column=0, sticky="w", pady=(5, 15))

var_entregador = ctk.StringVar(value="Moto 1")

ctk.CTkRadioButton(frame_moto, text="Moto 1", variable=var_entregador, value="Moto 1").pack(side="left", padx=5)
ctk.CTkRadioButton(frame_moto, text="Moto 2", variable=var_entregador, value="Moto 2").pack(side="left", padx=5)
ctk.CTkRadioButton(frame_moto, text="Moto 3", variable=var_entregador, value="Moto 3").pack(side="left", padx=5)

# Botões
btn_salvar = ctk.CTkButton(main, text="IMPRIMIR E SALVAR", command=finalizar, height=40)
btn_salvar.grid(row=14, column=0, sticky="ew", pady=(10, 10))

btn_relatorio = ctk.CTkButton(main, text="VER RELATÓRIOS", command=ver_relatorio, height=36, fg_color="#666666")
btn_relatorio.grid(row=15, column=0, sticky="ew")

app.mainloop()
