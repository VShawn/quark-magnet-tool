@echo off
cd /d "%~dp0"
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --console ^
  --name 夸克磁力链工具 ^
  --paths src ^
  --add-data "templates;templates" ^
  src\main.py
echo.
echo 产物: dist\夸克磁力链工具.exe
pause
