# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — Shopee Affiliate Bot
Gera um .exe único com todas as dependências embutidas.
"""
import sys
from pathlib import Path

BASE = Path(SPECPATH).parent

# ── Dados extras a incluir no bundle ──────────────────────────────────────────
datas = [
    # Chave pública RSA para validação offline
    (str(BASE / "bot_client" / "public.pem"),  "bot_client"),
    # Pasta bot_client inteira
    (str(BASE / "bot_client"),                  "bot_client"),
    # Configs e templates do Streamlit (necessário para rodar como subprocess)
    (str(BASE / "dashboard"),                   "dashboard"),
    (str(BASE / "config"),                      "config"),
    (str(BASE / "scraper"),                     "scraper"),
    (str(BASE / "scheduler"),                   "scheduler"),
    (str(BASE / "ai"),                          "ai"),
    (str(BASE / "converter"),                   "converter"),
    # Arquivo .env.example
    (str(BASE / ".env.example"),                "."),
]

# ── Imports ocultos (PyInstaller não detecta automaticamente) ─────────────────
hiddenimports = [
    # JWT / crypto
    "jwt",
    "jwt.algorithms",
    "cryptography",
    "cryptography.hazmat.primitives.asymmetric.rsa",
    "cryptography.hazmat.primitives.serialization",
    # Requests
    "requests",
    "urllib3",
    "certifi",
    # Anthropic SDK
    "anthropic",
    "httpx",
    # Playwright
    "playwright",
    "playwright.async_api",
    "playwright.sync_api",
    # APScheduler
    "apscheduler",
    "apscheduler.schedulers.background",
    "apscheduler.triggers.cron",
    # Pandas / Excel
    "pandas",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.utils",
    # Dotenv
    "dotenv",
    "python_dotenv",
    # Tkinter (GUI)
    "tkinter",
    "tkinter.scrolledtext",
    "tkinter.messagebox",
    # Utils
    "psutil",
    "yt_dlp",
]

a = Analysis(
    [str(BASE / "launcher.py")],
    pathex=[str(BASE)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(BASE / "build" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui o servidor de licenças (não vai no .exe do cliente)
        "license_server",
        # Exclui módulos desnecessários para reduzir tamanho
        "matplotlib",
        "scipy",
        "numpy.testing",
        "IPython",
        "jupyter",
        "pytest",
    ],
    noarchive=False,
    optimize=2,  # otimiza bytecode
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShopeeAffiliateBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # comprime com UPX (reduz tamanho ~30%)
    console=False,      # sem janela de console (GUI only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE / "build" / "icon.ico") if (BASE / "build" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ShopeeAffiliateBot",
)
