@echo off
echo 🚀 Запуск Graph Editor в полном режиме

REM Проверяем Node.js
where node >nul 2>nul
if errorlevel 1 (
    echo ❌ Node.js не установлен
    echo Установите Node.js: https://nodejs.org/
    pause
    exit /b 1
)

REM Проверяем Python
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python не установлен
    pause
    exit /b 1
)

echo 🔧 Запуск AI API сервера...
start /B python api.py
echo ✅ AI API сервер запущен

timeout /t 2 /nobreak >nul

echo 🔧 Запуск прокси сервера...
start /B node proxy-server.js
echo ✅ Прокси сервер запущен

timeout /t 2 /nobreak >nul

echo 🌐 Открываю Graph Editor...
start http://localhost:3000/proxy-index.html

echo.
echo ✅ Система запущена!
echo 📊 Состояние:
echo    AI API:    http://localhost:5000/api/health
echo    Прокси:    http://localhost:3000
echo    Редактор:  http://localhost:3000/proxy-index.html
echo.
echo 🛑 Для остановки закройте все окна и нажмите любую клавишу...

pause >nul

REM Закрываем процессы
taskkill /F /IM python.exe >nul 2>nul
taskkill /F /IM node.exe >nul 2>nul

echo 👋 Система остановлена
pause