@echo off
REM ================================================================
REM sync_session.bat — Envia a sessão Shopee salva para o VPS
REM Uso: sync_session.bat IP_DO_VPS usuario_ssh
REM Exemplo: sync_session.bat 123.45.67.89 ubuntu
REM ================================================================

set VPS_IP=%1
set VPS_USER=%2

if "%VPS_IP%"=="" (
    echo Uso: sync_session.bat IP_DO_VPS usuario_ssh
    echo Exemplo: sync_session.bat 123.45.67.89 ubuntu
    pause
    exit /b 1
)

if "%VPS_USER%"=="" set VPS_USER=ubuntu

echo Enviando sessao Shopee para VPS %VPS_IP%...
scp data\.shopee_session.json %VPS_USER%@%VPS_IP%:~/shopee-affiliate-bot/data/.shopee_session.json

if errorlevel 1 (
    echo ERRO: Nao foi possivel enviar o arquivo.
    echo Certifique-se de que:
    echo   1. SSH esta configurado no VPS
    echo   2. O arquivo data\.shopee_session.json existe
    echo   3. O IP e usuario estao corretos
) else (
    echo Sessao enviada com sucesso!
    echo O VPS ira usar sua sessao ja autenticada.
)

pause
