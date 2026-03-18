@echo off
chcp 65001 >nul
title Shopee Affiliate Bot
color 0A
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║     SHOPEE AFFILIATE BOT — SISTEMA COMPLETO     ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  [1/3] Abrindo Chrome com sessao Shopee...
start "" "%~dp0start_chrome.bat"
timeout /t 6 /nobreak >nul
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  Faca login em affiliate.shopee.com.br           ║
echo  ║  (so na primeira vez - sessao e salva)           ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Pressione qualquer tecla apos fazer login...
pause >nul
echo.
echo  [2/3] Iniciando Dashboard em localhost:8501...
start "Dashboard" cmd /k "python -m streamlit run dashboard\app.py --server.port 8501 --server.headless true"
timeout /t 4 /nobreak >nul
echo  [3/3] Iniciando Robo Mestre...
start "Robot Master" cmd /k "python robot_master.py"
timeout /t 3 /nobreak >nul
start "" "http://localhost:8501"
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         SISTEMA INICIADO COM SUCESSO!            ║
echo  ║  Dashboard:  http://localhost:8501               ║
echo  ║  Robo:       rodando em background               ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
