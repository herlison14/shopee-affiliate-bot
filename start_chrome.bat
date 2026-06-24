@echo off
echo Abrindo Chrome com Remote Debugging na porta 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\ChromeDebug --no-first-run --no-default-browser-check "https://affiliate.shopee.com.br/offer/product_offer"
timeout /t 3
echo Chrome aberto! Acesse: https://affiliate.shopee.com.br/offer/product_offer
echo Faca login se necessario, depois execute: python main.py
pause
