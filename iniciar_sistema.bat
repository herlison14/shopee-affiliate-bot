@echo off
title Shopee Affiliate Bot - Sistema Completo
color 0A
cls

echo ============================================
echo   SHOPEE AFFILIATE BOT - INICIANDO...
echo ============================================
echo.

:: Vai para a pasta do projeto
cd /d "C:\Users\herli\Downloads\shopee-affiliate-bot"

:: Verifica se o Chrome ja esta rodando com CDP
curl -s http://localhost:9222/json >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Chrome com Remote Debugging ja esta ativo!
) else (
    echo [>>] Abrindo Chrome com Remote Debugging...
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\ChromeDebug --no-first-run --no-default-browser-check
    timeout /t 4 /nobreak >nul
    echo [OK] Chrome aberto!
)

echo.
echo [>>] Iniciando Dashboard em http://localhost:8501
echo      (abre automaticamente no navegador)
echo.

:: Inicia o dashboard em background
start "Dashboard" cmd /c "cd /d C:\Users\herli\Downloads\shopee-affiliate-bot && python -m streamlit run dashboard/app.py --server.headless true"

:: Aguarda o dashboard subir
timeout /t 5 /nobreak >nul

:: Abre o dashboard no Chrome
start "" "http://localhost:8501"

echo ============================================
echo   SISTEMA PRONTO!
echo ============================================
echo.
echo   Dashboard: http://localhost:8501
echo.
echo   Para rodar o bot agora:
echo     >> Clique em "Executar Pipeline" no Dashboard
echo     >> OU execute: python main.py
echo.
echo   IMPORTANTE: Faca login no Chrome que abriu
echo   e acesse: affiliate.shopee.com.br
echo.
echo ============================================
pause
