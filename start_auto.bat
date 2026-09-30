@echo off
chcp 65001 >nul
echo ==========================================
echo    Geek Laser Tag - Helios System
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe.
    echo Veuillez installer Python depuis python.org
    pause
    exit /b 1
)

REM Install deps
echo [1/3] Installation des dependances...
pip install flask openpyxl fpdf -q

REM Start server
echo [2/3] Demarrage du serveur...
echo.
echo ==========================================
python app.py
echo.
pause
