@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ========================================
echo    🚀 GRAPH EDITOR - УПРОЩЕННЫЙ ЗАПУСК (Windows)
echo ========================================
echo.

REM Проверяем Node.js
echo Проверка Node.js...
where node >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('node --version') do set NODE_VERSION=%%i
    echo ✅ Node.js: !NODE_VERSION!
) else (
    echo ❌ Node.js не установлен
    echo Установите Node.js: https://nodejs.org/
    start https://nodejs.org/
    exit /b 1
)

REM Проверяем Python
echo Проверка Python...
where python >nul 2>nul
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ Python: !PYTHON_VERSION!
) else (
    where python3 >nul 2>nul
    if %errorlevel% equ 0 (
        for /f "tokens=*" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
        echo ✅ Python: !PYTHON_VERSION!
    ) else (
        echo ❌ Python 3 не установлен
        echo Установите Python 3: https://www.python.org/
        start https://www.python.org/
        exit /b 1
    )
)

REM Проверяем Ollama
echo 🤖 Проверка Ollama...
where ollama >nul 2>nul
if %errorlevel% equ 0 (
    echo ✅ Ollama установлен
    
    REM Проверяем, запущен ли сервер Ollama
    curl -s http://localhost:11434/api/tags >nul 2>nul
    if !errorlevel! neq 0 (
        echo    🚀 Запуск сервера Ollama...
        start /B ollama serve >nul 2>nul
        set OLLAMA_STARTED=1
        echo    ✅ Ollama запущен
        
        REM Ждем запуска сервера
        echo    ⏳ Ожидание запуска сервера...
        timeout /t 5 /nobreak >nul
        
        REM Проверяем, что сервер запустился
        curl -s http://localhost:11434/api/tags >nul 2>nul
        if !errorlevel! equ 0 (
            echo    ✅ Сервер Ollama готов
        ) else (
            echo    ⚠️  Не удалось запустить сервер Ollama. LLM функции могут не работать.
        )
    ) else (
        echo    ✅ Сервер Ollama уже запущен
    )
    
    REM Проверяем наличие модели llama3.2
    echo    🔍 Проверка модели llama3.2...
    curl -s http://localhost:11434/api/tags | findstr "llama3.2" >nul 2>nul
    if !errorlevel! equ 0 (
        echo    ✅ Модель llama3.2 найдена
    ) else (
        echo    ⬇️  Модель llama3.2 не найдена. Загрузка...
        start /B ollama pull llama3.2 >nul 2>nul
        echo    ✅ Модель загружается в фоновом режиме
    )
) else (
    echo    ⚠️  Ollama не установлен. LLM функции не будут доступны.
    echo    Установите Ollama: https://ollama.ai/
    echo    Или используйте DeepSeek через настройки интерфейса.
)

echo.

REM Останавливаем старые процессы
echo 🧹 Останавливаю старые процессы...
taskkill /F /IM python.exe /T >nul 2>nul
taskkill /F /IM node.exe /T >nul 2>nul
timeout /t 2 /nobreak >nul

REM Запускаем API
echo 🔧 Запуск AI API...
echo    Использую api_main.py с гарантированным выводом логов
echo.
echo 🚀 ЗАПУСК API (логи БУДУТ ВИДНЫ ниже):
echo =======================================

REM Запускаем API в отдельном окне
start "Graph Editor API" cmd /c "python api_main.py 2>&1 | tee api_startup.log"
echo    📝 Логи API пишутся в: api_startup.log

REM Даем время на запуск и проверяем порт
echo ⏳ Запуск API... (ожидание 10 секунд)
set API_PORT=
for /L %%i in (1,1,10) do (
    REM Проверяем файл с портом
    if exist api_port.txt (
        set /p API_PORT=<api_port.txt
        REM Проверяем, слушает ли порт
        curl -s http://localhost:!API_PORT!/api/health >nul 2>nul
        if !errorlevel! equ 0 (
            echo    ✅ API запущен на порту !API_PORT!
            goto :api_found
        )
    )
    
    REM Также проверяем стандартные порты
    for %%p in (5001 5002 5003 5004 5005 5006 5007 5008 5009 5010) do (
        curl -s http://localhost:%%p/api/health >nul 2>nul
        if !errorlevel! equ 0 (
            set API_PORT=%%p
            echo    ✅ API найден на порту !API_PORT!
            goto :api_found
        )
    )
    
    timeout /t 1 /nobreak >nul
    echo    ⏳ Ожидание запуска API (%%i/10)...
)

:api_not_found
if "!API_PORT!"=="" (
    echo    ⚠️  API порт не определен, использую порт по умолчанию 5009
    set API_PORT=5009
    
    REM Проверяем, работает ли API
    curl -s http://localhost:!API_PORT!/api/health >nul 2>nul
    if !errorlevel! equ 0 (
        echo    ✅ API работает на порту !API_PORT!
    ) else (
        echo    ❌ API не запустился
        echo    Пробую альтернативный способ...
        echo    Откройте новый терминал и запустите:
        echo    cd /D "%~dp0" ^& python api_simple_with_cors.py
        echo    Затем в этом окне нажмите Enter...
        pause
    )
)

:api_found
REM Запускаем прокси
echo 🔧 Запуск прокси...
start "Graph Editor Proxy" cmd /c "node proxy-server.js"
timeout /t 3 /nobreak >nul

REM Проверяем прокси
set PROXY_OK=0
for /L %%i in (1,1,5) do (
    netstat -an | findstr ":3000.*LISTENING" >nul 2>nul
    if !errorlevel! equ 0 (
        echo    ✅ Прокси запущен на порту 3000
        set PROXY_OK=1
        goto :proxy_ok
    )
    timeout /t 1 /nobreak >nul
    echo    ⏳ Ожидание запуска прокси (попытка %%i/5)...
)

if !PROXY_OK! equ 0 (
    echo    ❌ Прокси не запустился
    echo    Пробую альтернативный способ...
    echo    Откройте новый терминал и запустите:
    echo    cd /D "%~dp0" ^& node proxy-server.js
    echo    Затем в этом окне нажмите Enter...
    pause
)

:proxy_ok
echo.

REM Проверяем статус LLM
set LLM_STATUS=❌ Недоступен
where ollama >nul 2>nul
if !errorlevel! equ 0 (
    curl -s http://localhost:11434/api/tags >nul 2>nul
    if !errorlevel! equ 0 (
        set LLM_STATUS=✅ Ollama (llama3.2)
    ) else (
        set LLM_STATUS=⚠️  Ollama (сервер не запущен)
    )
)

echo ✅ СИСТЕМА ЗАПУЩЕНА!
echo.
echo 📊 СЕРВЕРЫ:
echo    • AI API:    http://localhost:!API_PORT!/api/health
echo    • Прокси:    http://localhost:3000
echo    • Редактор:  http://localhost:3000/proxy-index.html
echo    • LLM:       !LLM_STATUS!
echo.
echo 📝 ЛОГИ В РЕАЛЬНОМ ВРЕМЕНИ:
echo    • Логи API отображаются в отдельном окне
echo    • JSON модели будет виден после генерации
echo    • Подробные логи также в файле: api.log
echo.
echo 🔍 ДЛЯ ПРОВЕРКИ:
echo    API здоровье: curl http://localhost:!API_PORT!/api/health
echo    Прокси работает: curl http://localhost:3000/api/health
echo.

echo 🎯 ЧТО ДЕЛАТЬ ДАЛЬШЕ:
echo    1. Браузер должен открыться автоматически
echo    2. Если нет, откройте: http://localhost:3000/proxy-index.html
echo    3. Нажмите кнопку 'Graph Manager' (в правом верхнем углу графа)
echo    4. Загрузите файл (.txt, .md, .pdf) или введите текст ТЗ
echo    5. Нажмите 'Отправить' для генерации модели
echo.
echo 🔧 ЕСЛИ ВОЗНИКЛИ ПРОБЛЕМЫ:
echo    • Проверьте, что порты 3000 и !API_PORT! свободны
echo    • Перезапустите скрипт: launch.bat
echo    • Подробная документация: README.md
echo.
echo 🛑 ДЛЯ ОСТАНОВКИ:
echo    Закройте все открытые окна командной строки
echo.

REM Открываем браузер
echo 🌐 Открываю Graph Editor...
start http://localhost:3000/proxy-index.html

echo.
echo Для остановки системы закройте все окна командной строки.
echo Нажмите любую клавишу для выхода...
pause >nul

REM Функция очистки (выполнится при закрытии)
echo.
echo 🧹 Остановка системы...

REM Останавливаем процессы
taskkill /F /IM python.exe /T >nul 2>nul
taskkill /F /IM node.exe /T >nul 2>nul

if defined OLLAMA_STARTED (
    taskkill /F /IM ollama.exe /T >nul 2>nul
    echo    Остановлен Ollama
)

echo ✅ Система остановлена
exit /b 0