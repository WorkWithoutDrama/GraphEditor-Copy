@echo off
echo 🚀 Запуск Graph Editor...
echo ========================

REM Проверяем, запущен ли Python API
echo 🔍 Проверка API сервера...
curl -s http://localhost:5009/api/health > nul 2>&1
if errorlevel 1 (
    echo ✅ Запуск AI API сервера на порту 5009...
    start /B python api.py
    echo    API сервер запущен
    timeout /t 2 /nobreak > nul
) else (
    echo ⚠️  API сервер уже запущен на порту 5009
)

REM Проверяем, запущен ли прокси
echo.
echo 🔍 Проверка прокси-сервера...
curl -s http://localhost:3000 > nul 2>&1
if errorlevel 1 (
    echo ✅ Запуск прокси-сервера на порту 3000...
    start /B node proxy-server.js
    echo    Прокси сервер запущен
    timeout /t 2 /nobreak > nul
) else (
    echo ⚠️  Прокси сервер уже запущен на порту 3000
)

echo.
echo ========================
echo 🎉 Все компоненты запущены!
echo.
echo 🌐 Откройте в браузере:
echo    • http://localhost:3000/proxy-index.html
echo    • http://localhost:3000/test-fix.html
echo.
echo 📝 Для остановки закройте это окно
echo.

pause