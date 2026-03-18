@echo off
title Configurar Agendamento Automatico
cd /d "C:\Users\herli\Downloads\shopee-affiliate-bot"

echo ============================================
echo   AGENDANDO EXECUCAO AUTOMATICA DIARIA
echo ============================================
echo.
echo O bot sera executado todo dia as 08:00
echo Certifique-se que o Chrome esteja aberto
echo com remote debugging antes desse horario.
echo.

:: Cria a tarefa agendada no Windows
schtasks /create /tn "ShopeeAffiliateBot" /tr "python C:\Users\herli\Downloads\shopee-affiliate-bot\main.py" /sc daily /st 08:00 /f /rl HIGHEST

if %errorlevel% == 0 (
    echo.
    echo [OK] Tarefa agendada com sucesso!
    echo      Nome: ShopeeAffiliateBot
    echo      Horario: Todo dia as 08:00
    echo.
    echo Para ver a tarefa: Agendador de Tarefas do Windows
    echo Para remover: schtasks /delete /tn "ShopeeAffiliateBot" /f
) else (
    echo [ERRO] Falha ao criar tarefa. Execute como Administrador.
)

pause
