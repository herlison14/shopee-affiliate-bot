@echo off
REM ============================================================
REM  Shopee Affiliate Bot — Build Script (PyInstaller)
REM  Gera ShopeeAffiliateBot.exe pronto para distribuição
REM ============================================================

echo.
echo === Shopee Affiliate Bot — Build ===
echo.

REM ── Verifica Python ──────────────────────────────────────────
python --version
if errorlevel 1 (
    echo ERRO: Python nao encontrado. Instale Python 3.10-3.12.
    pause & exit /b 1
)

REM ── Instala dependências de build ────────────────────────────
echo [1/5] Instalando PyInstaller e dependencias...
pip install pyinstaller pyinstaller-hooks-contrib pyjwt[crypto] requests cryptography --quiet

REM ── Copia a chave publica para bot_client ────────────────────
echo [2/5] Copiando chave publica RSA...
if exist "..\license_server\keys\public.pem" (
    copy "..\license_server\keys\public.pem" "..\bot_client\public.pem" >nul
    echo     public.pem copiada com sucesso.
) else (
    echo     AVISO: public.pem nao encontrada. Execute generate_keys.py primeiro.
    echo     Continuando sem chave publica ^(modo dev^)...
)

REM ── Baixa browsers do Playwright ─────────────────────────────
echo [3/5] Verificando browsers do Playwright...
playwright install chromium --with-deps
if errorlevel 1 (
    echo AVISO: Falha ao instalar Playwright chromium.
)

REM ── Compila o .exe ───────────────────────────────────────────
echo [4/5] Compilando .exe com PyInstaller...
cd ..
pyinstaller build\shopee_bot.spec --clean --noconfirm

if errorlevel 1 (
    echo ERRO: Build falhou.
    pause & exit /b 1
)

REM ── Copia arquivos extras para dist/ ─────────────────────────
echo [5/5] Preparando pasta de distribuicao...
if not exist "dist\ShopeeAffiliateBot" mkdir "dist\ShopeeAffiliateBot"

REM Copia .env.example
copy ".env.example" "dist\ShopeeAffiliateBot\.env.example" >nul 2>&1

REM Copia browsers do Playwright
set PLAYWRIGHT_BROWSERS=%USERPROFILE%\AppData\Local\ms-playwright
if exist "%PLAYWRIGHT_BROWSERS%\chromium-*" (
    echo     Copiando browsers do Playwright...
    xcopy "%PLAYWRIGHT_BROWSERS%\chromium-*" "dist\ShopeeAffiliateBot\ms-playwright\chromium-latest\" /E /I /Q >nul
)

REM Cria README de instalacao
echo Shopee Affiliate Bot > "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo. >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo INSTRUCOES DE INSTALACAO: >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo 1. Renomeie .env.example para .env >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo 2. Preencha suas credenciais no .env >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo 3. Execute ShopeeAffiliateBot.exe >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo 4. Insira sua chave de licenca na tela de ativacao >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo. >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"
echo Suporte: (21) 99792-7927 >> "dist\ShopeeAffiliateBot\LEIA-ME.txt"

echo.
echo ============================================================
echo  BUILD CONCLUIDO!
echo  Arquivo: dist\ShopeeAffiliateBot\ShopeeAffiliateBot.exe
echo ============================================================
echo.
pause
