import json
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

# pyrefly: ignore [missing-import]
from tkcalendar import Calendar

from src.config import CATEGORIAS_BUSCA, OUTPUT_DIR
from src.main import main

# 
# CORES INSTITUCIONAIS SMS - ULTRA COMPACTO 16:9
# 
COR_FUNDO = "#F0F4F8"  # Fundo azul-gelo claro
COR_TEXTO = "#00384A"  # Azul-petróleo escuro
COR_TEXTO_MUTED = "#64748B"  # Cinza secundário
COR_BOTAO = "#0083B0"  # Azul turquesa
COR_HOVER = "#006A8E"  # Turquesa escuro (hover)
COR_BORDA = "#00384A"  # Borda azul-petróleo


def executar():
    selecionadas = [nome for nome, var in checkboxes.items() if var.get()]
    if not selecionadas:
        messagebox.showwarning("Aviso", "Selecione ao menos uma categoria de busca.")
        return

    data_busca = entrada_data.get().strip()
    if not data_busca:
        messagebox.showwarning("Aviso", "Informe uma data.")
        return

    status.config(text="Executando busca...", fg=COR_BOTAO)
    resumo.config(text="")
    botao.config(state="disabled")

    def tarefa_background():
        try:
            main(categorias_busca=selecionadas, data_busca=data_busca)
            with open(OUTPUT_DIR / "log_execucao.json", "r", encoding="utf-8") as f:
                log = json.load(f)

            def sucesso():
                status.config(text="Busca concluída!", fg="#2E7D32")
                resumo.config(
                    text=(
                        f"ATAS: {log['total_encontradas']} | "
                        f"Exportadas: {log['total_exportadas']} | "
                        f"Ignoradas: {len(log['ignoradas'])}\n"
                        f"Edição: {data_busca} | Execução: {log['data_execucao']}"
                    )
                )
                botao.config(state="normal")

            janela.after(0, sucesso)

        except Exception as e:
            def erro():
                status.config(text="Erro na execução.", fg="#D32F2F")
                botao.config(state="normal")
                messagebox.showerror("Erro", str(e))

            janela.after(0, erro)

    threading.Thread(target=tarefa_background, daemon=True).start()


def executar_thread():
    executar()


def abrir_calendario():
    top = tk.Toplevel(janela)
    top.title("Selecionar Data")
    top.configure(bg=COR_FUNDO)
    top.resizable(False, False)
    top.grab_set()

    x = janela.winfo_x() + 185
    y = janela.winfo_y() + 45
    top.geometry(f"270x270+{x}+{y}")

    cal = Calendar(
        top,
        locale="pt_BR",
        selectmode="day",
        date_pattern="dd/mm/yyyy",
        background="#FFFFFF",
        foreground="black",
        headersbackground="#FFFFFF",
        headersforeground="black",
        normalbackground="#FFFFFF",
        normalforeground="black",
        weekendbackground="#FFFFFF",
        weekendforeground="black",
        othermonthbackground="#FFFFFF",
        othermonthforeground="#94A3B8",
        selectbackground=COR_BOTAO,
        selectforeground="white",
    )
    cal.pack(pady=10, padx=10)

    def confirmar():
        entrada_data.delete(0, tk.END)
        entrada_data.insert(0, cal.get_date())
        top.destroy()

    btn_confirmar = tk.Button(
        top,
        text="Confirmar Data",
        font=("Segoe UI", 9, "bold"),
        bg=COR_BOTAO,
        fg="white",
        relief="flat",
        bd=0,
        pady=4,
        padx=12,
        cursor="hand2",
        command=confirmar,
    )
    btn_confirmar.pack(pady=(0, 10))


# 
# JANELA PRINCIPAL (PAISAGEM ULTRA COMPACTA - 640x360)
#
janela = tk.Tk()
janela.title("Buscar ATAS")
janela.geometry("640x360")
janela.configure(bg=COR_FUNDO)
janela.resizable(False, False)

# 
tk.Frame(janela, bg=COR_FUNDO, height=10).pack()

# TÍTULO
titulo = tk.Label(
    janela,
    text="Buscar ATAS",
    font=("Segoe UI", 18, "bold"),
    bg=COR_FUNDO,
    fg=COR_TEXTO,
)
titulo.pack(pady=(0, 1))

subtitulo = tk.Label(
    janela,
    text="Leitura automática do Diário Oficial",
    font=("Segoe UI", 9),
    bg=COR_FUNDO,
    fg=COR_TEXTO_MUTED,
)
subtitulo.pack(pady=(0, 12))

# DATA DE BUSCA
frame_data = tk.Frame(janela, bg=COR_FUNDO)
frame_data.pack(pady=(0, 12))

lbl_data = tk.Label(
    frame_data,
    text="Busca por Edição",
    font=("Segoe UI", 9, "bold"),
    bg=COR_FUNDO,
    fg=COR_TEXTO,
)
lbl_data.pack(pady=(0, 2))

frame_input_data = tk.Frame(frame_data, bg=COR_FUNDO)
frame_input_data.pack()

entrada_data = tk.Entry(
    frame_input_data,
    width=12,
    font=("Segoe UI", 10),
    justify="center",
    bd=1,
    relief="solid",
    bg="#FFFFFF",
    fg=COR_TEXTO,
    highlightbackground=COR_BORDA,
    highlightcolor=COR_BORDA,
)
entrada_data.pack(side="left", padx=(0, 4), ipady=1)
entrada_data.insert(0, datetime.now().strftime("%d/%m/%Y"))

btn_cal = tk.Button(
    frame_input_data,
    text="📅",
    font=("Segoe UI", 9),
    bg="#FFFFFF",
    fg=COR_TEXTO,
    bd=1,
    relief="solid",
    cursor="hand2",
    width=3,
    command=abrir_calendario,
)
btn_cal.pack(side="left")

# CATEGORIAS DE BUSCA
frame = tk.LabelFrame(
    janela,
    text=" Buscar por ",
    padx=12,
    pady=8,
    bg=COR_FUNDO,
    fg=COR_TEXTO,
    font=("Segoe UI", 9, "bold"),
    bd=1,
    relief="solid",
)
frame.pack(pady=(0, 14), padx=25, fill="x")

frame_checkboxes = tk.Frame(frame, bg=COR_FUNDO)
frame_checkboxes.pack(fill="x", expand=True)

checkboxes = {}

for nome in CATEGORIAS_BUSCA:
    var = tk.BooleanVar()
    cb = tk.Checkbutton(
        frame_checkboxes,
        text=nome,
        variable=var,
        font=("Segoe UI", 8, "bold"),
        bg=COR_FUNDO,
        fg=COR_TEXTO,
        selectcolor=COR_FUNDO,
        activebackground=COR_FUNDO,
        activeforeground=COR_TEXTO,
    )
    cb.pack(side="left", expand=True, anchor="center")
    checkboxes[nome] = var

# BOTÃO EXECUTAR
botao = tk.Button(
    janela,
    text="Executar Busca  ➔",
    font=("Segoe UI", 10, "bold"),
    bg=COR_BOTAO,
    fg="white",
    activebackground=COR_HOVER,
    activeforeground="white",
    relief="flat",
    bd=0,
    width=22,
    pady=6,
    cursor="hand2",
    command=executar_thread,
)

botao.bind("<Enter>", lambda e: botao.config(bg=COR_HOVER))
botao.bind("<Leave>", lambda e: botao.config(bg=COR_BOTAO))
botao.pack(pady=(0, 10))

# STATUS & RESUMO
status = tk.Label(
    janela,
    text="Status da Busca",
    font=("Segoe UI", 9, "bold"),
    bg=COR_FUNDO,
    fg=COR_TEXTO_MUTED,
)
status.pack(pady=(0, 2))

resumo = tk.Label(
    janela,
    text="",
    font=("Segoe UI", 8),
    justify="center",
    bg=COR_FUNDO,
    fg=COR_TEXTO,
)
resumo.pack()

def iniciar():
    janela.mainloop()


if __name__ == "__main__":
    iniciar()