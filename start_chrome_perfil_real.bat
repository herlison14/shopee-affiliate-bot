@echo off
echo ATENCAO: feche TODAS as janelas do Chrome antes de continuar.
echo Pressione qualquer tecla quando o Chrome estiver fechado...
pause
echo Abrindo Chrome com seu perfil REAL (historico/cookies existentes) + depuracao remota...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\herli\AppData\Local\Google\Chrome\User Data" --profile-directory="Default" --no-first-run "https://affiliate.shopee.com.br/offer/product_offer"
timeout /t 3
echo Chrome aberto com seu perfil de sempre! Deve abrir ja logado, ou pedir login normalmente.
pause
