@echo off
echo.
echo ═══════════════════════════════════════════════
echo   Demarrage de ngrok pour MaishaPay callbacks
echo ═══════════════════════════════════════════════
echo.
echo Demarrage de ngrok sur le port 8000...
start "" ngrok.exe http 8000

timeout /t 4 /nobreak >nul

echo.
echo Ouvrez http://127.0.0.1:4040 dans votre navigateur
echo pour voir l'URL publique ngrok.
echo.
echo Une fois l'URL obtenue, mettez a jour MAISHAPAY_CALLBACK_URL
echo dans le fichier .env avec :
echo   https://XXXX.ngrok-free.app/courses/paiement/callback/
echo.
pause
