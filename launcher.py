"""
Shopee Affiliate Bot — Launcher
Ponto de entrada do .exe: valida licença e exibe painel de controle.
"""
import logging
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, scrolledtext

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
LOG_FILE = BASE_DIR / "logs" / "affiliate_bot.log"
ENV_FILE = BASE_DIR / ".env"
PYTHON = sys.executable

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── Validação de licença ──────────────────────────────────────────────────────

def _check_license() -> bool:
    try:
        sys.path.insert(0, str(BASE_DIR / "bot_client"))
        from license_validator import get_saved_license, validate_license
        from activation_ui import show_activation_window

        key = get_saved_license()
        if key:
            valid, msg = validate_license(key)
            if valid:
                logger.info(f"Licença OK: {msg}")
                return True
            logger.warning(f"Licença inválida: {msg}")

        key = show_activation_window()
        if not key:
            return False

        valid, msg = validate_license(key)
        if not valid:
            messagebox.showerror("Erro", msg)
            return False
        return True

    except ImportError:
        logger.warning("bot_client não encontrado — modo desenvolvimento.")
        return True


# ── Painel de controle ────────────────────────────────────────────────────────

class ControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Shopee Affiliate Bot")
        self.root.geometry("600x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        self.root.eval("tk::PlaceWindow . center")

        self._bot_proc: subprocess.Popen | None = None
        self._dashboard_proc: subprocess.Popen | None = None
        self._scheduler_proc: subprocess.Popen | None = None
        self._log_thread: threading.Thread | None = None
        self._running = True

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        tk.Label(
            self.root, text="🛒  Shopee Affiliate Bot",
            font=("Arial", 16, "bold"), fg="#ee4d2d", bg="#1a1a2e",
        ).pack(pady=(18, 2))
        tk.Label(
            self.root, text="Automação de Marketing de Afiliados",
            font=("Arial", 9), fg="#888888", bg="#1a1a2e",
        ).pack(pady=(0, 15))

        # Status
        self._status_var = tk.StringVar(value="⚪  Aguardando")
        tk.Label(
            self.root, textvariable=self._status_var,
            font=("Arial", 10, "bold"), fg="#00ff88", bg="#1a1a2e",
        ).pack(pady=(0, 10))

        # Botões
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=5)

        self._btn_pipeline = self._make_btn(
            btn_frame, "▶  Executar Pipeline", "#ee4d2d", self._run_pipeline, 0, 0
        )
        self._btn_scheduler = self._make_btn(
            btn_frame, "🕐  Iniciar Agendador", "#2196F3", self._start_scheduler, 0, 1
        )
        self._btn_dashboard = self._make_btn(
            btn_frame, "📊  Abrir Dashboard", "#4CAF50", self._open_dashboard, 1, 0
        )
        self._btn_stop = self._make_btn(
            btn_frame, "⏹  Parar Tudo", "#666666", self._stop_all, 1, 1
        )

        # Config .env
        tk.Button(
            self.root, text="⚙  Editar Configurações (.env)",
            command=self._open_env,
            font=("Arial", 9), bg="#16213e", fg="#aaaaaa",
            relief="flat", cursor="hand2",
        ).pack(pady=(8, 0))

        # Log viewer
        tk.Label(
            self.root, text="Log em tempo real:",
            font=("Arial", 9), fg="#666688", bg="#1a1a2e",
        ).pack(pady=(12, 2))

        self._log_box = scrolledtext.ScrolledText(
            self.root, height=10, width=72,
            font=("Courier", 8), bg="#0d0d1a", fg="#00ff88",
            relief="flat", state="disabled",
        )
        self._log_box.pack(padx=15, pady=(0, 10))

        # Inicia tail do log
        self._start_log_tail()

    def _make_btn(self, parent, text, color, cmd, row, col):
        btn = tk.Button(
            parent, text=text, command=cmd,
            font=("Arial", 10, "bold"),
            bg=color, fg="#ffffff",
            activebackground=color, activeforeground="#ffffff",
            relief="flat", cursor="hand2", width=20, pady=8,
        )
        btn.grid(row=row, column=col, padx=8, pady=5)
        return btn

    # ── Ações ─────────────────────────────────────────────────────────────────

    def _run_pipeline(self):
        if self._bot_proc and self._bot_proc.poll() is None:
            messagebox.showinfo("Info", "Pipeline já está em execução.")
            return
        self._status_var.set("🟢  Pipeline executando...")
        self._bot_proc = subprocess.Popen(
            [PYTHON, str(BASE_DIR / "main.py")],
            cwd=str(BASE_DIR),
        )
        threading.Thread(target=self._wait_proc, args=(self._bot_proc, "Pipeline"), daemon=True).start()

    def _start_scheduler(self):
        if self._scheduler_proc and self._scheduler_proc.poll() is None:
            messagebox.showinfo("Info", "Agendador já está ativo.")
            return
        self._status_var.set("🟡  Agendador ativo...")
        self._scheduler_proc = subprocess.Popen(
            [PYTHON, str(BASE_DIR / "main.py"), "--scheduler"],
            cwd=str(BASE_DIR),
        )

    def _open_dashboard(self):
        if not (self._dashboard_proc and self._dashboard_proc.poll() is None):
            self._dashboard_proc = subprocess.Popen(
                [PYTHON, "-m", "streamlit", "run",
                 str(BASE_DIR / "dashboard" / "app.py"),
                 "--server.port", "8501",
                 "--server.headless", "true"],
                cwd=str(BASE_DIR),
            )
        # Aguarda 2s e abre no browser
        self.root.after(2000, lambda: webbrowser.open("http://localhost:8501"))
        self._status_var.set("🔵  Dashboard aberto em localhost:8501")

    def _stop_all(self):
        for proc in [self._bot_proc, self._scheduler_proc, self._dashboard_proc]:
            if proc and proc.poll() is None:
                proc.terminate()
        self._bot_proc = self._scheduler_proc = self._dashboard_proc = None
        self._status_var.set("⚪  Processos encerrados")

    def _open_env(self):
        env_path = ENV_FILE if ENV_FILE.exists() else BASE_DIR / ".env.example"
        os.startfile(str(env_path))

    def _wait_proc(self, proc, name):
        proc.wait()
        self.root.after(0, lambda: self._status_var.set(f"⚪  {name} finalizado."))

    # ── Log tail ───────────────────────────────────────────────────────────────

    def _start_log_tail(self):
        def tail():
            LOG_FILE.parent.mkdir(exist_ok=True)
            LOG_FILE.touch(exist_ok=True)
            with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)  # vai para o final
                while self._running:
                    line = f.readline()
                    if line:
                        self._append_log(line.rstrip())
                    else:
                        import time
                        time.sleep(0.3)

        self._log_thread = threading.Thread(target=tail, daemon=True)
        self._log_thread.start()

    def _append_log(self, text: str):
        def _do():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", text + "\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.root.after(0, _do)

    # ── Fechar ─────────────────────────────────────────────────────────────────

    def _on_close(self):
        if messagebox.askokcancel("Sair", "Encerrar o bot e fechar?"):
            self._running = False
            self._stop_all()
            self.root.destroy()

    def run(self):
        self.root.mainloop()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not _check_license():
        sys.exit(1)
    ControlPanel().run()


if __name__ == "__main__":
    main()
