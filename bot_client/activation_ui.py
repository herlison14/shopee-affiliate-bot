"""
Tela de ativação de licença — exibida na 1ª execução ou se licença inválida.
Usa tkinter (nativo do Python, sem dependência extra).
"""
import tkinter as tk
from tkinter import messagebox


def show_activation_window() -> str | None:
    """
    Exibe janela de ativação e retorna a chave digitada.
    Retorna None se o usuário fechar sem ativar.
    """
    result = {"key": None}

    root = tk.Tk()
    root.title("Ativar Shopee Affiliate Bot")
    root.geometry("480x280")
    root.resizable(False, False)
    root.configure(bg="#1a1a2e")

    # Centraliza janela
    root.eval("tk::PlaceWindow . center")

    # ── Header ────────────────────────────────────────────────────────────────
    tk.Label(
        root,
        text="🛒  Shopee Affiliate Bot",
        font=("Arial", 16, "bold"),
        fg="#ee4d2d",
        bg="#1a1a2e",
    ).pack(pady=(25, 5))

    tk.Label(
        root,
        text="Digite sua chave de licença para ativar o software",
        font=("Arial", 10),
        fg="#aaaaaa",
        bg="#1a1a2e",
    ).pack(pady=(0, 20))

    # ── Input ─────────────────────────────────────────────────────────────────
    frame = tk.Frame(root, bg="#1a1a2e")
    frame.pack(padx=40, fill="x")

    entry_var = tk.StringVar()
    entry = tk.Entry(
        frame,
        textvariable=entry_var,
        font=("Courier", 13, "bold"),
        justify="center",
        bd=2,
        relief="flat",
        bg="#16213e",
        fg="#ffffff",
        insertbackground="#ffffff",
    )
    entry.pack(ipady=10, fill="x")
    entry.insert(0, "SHOPEE-XXXX-XXXX-XXXX-XXXX")
    entry.bind("<FocusIn>", lambda e: entry.delete(0, "end") if entry.get().startswith("SHOPEE-X") else None)
    entry.focus()

    # ── Status ────────────────────────────────────────────────────────────────
    status_var = tk.StringVar()
    status_label = tk.Label(
        root,
        textvariable=status_var,
        font=("Arial", 9),
        fg="#e74c3c",
        bg="#1a1a2e",
    )
    status_label.pack(pady=(8, 0))

    # ── Botão ─────────────────────────────────────────────────────────────────
    def on_activate():
        key = entry_var.get().strip().upper()
        if not key or key == "SHOPEE-XXXX-XXXX-XXXX-XXXX":
            status_var.set("❌ Insira uma chave de licença válida.")
            return

        status_var.set("⏳ Validando...")
        root.update()

        from license_validator import validate_license
        valid, msg = validate_license(key)

        if valid:
            messagebox.showinfo("✅ Ativado!", f"{msg}\n\nO bot será iniciado agora.")
            result["key"] = key
            root.destroy()
        else:
            status_var.set(f"❌ {msg}")

    btn = tk.Button(
        root,
        text="  Ativar Licença  ",
        command=on_activate,
        font=("Arial", 11, "bold"),
        bg="#ee4d2d",
        fg="#ffffff",
        activebackground="#cc3d21",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
    )
    btn.pack(pady=(15, 0))

    # ── Suporte ───────────────────────────────────────────────────────────────
    tk.Label(
        root,
        text="Suporte: (21) 99792-7927",
        font=("Arial", 8),
        fg="#555577",
        bg="#1a1a2e",
    ).pack(side="bottom", pady=8)

    root.mainloop()
    return result["key"]
