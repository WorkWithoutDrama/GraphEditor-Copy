# Graph Editor - Упрощенный запуск (PowerShell)
# Для Windows 10/11 с PowerShell 5.1 или выше

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🚀 GRAPH EDITOR - УПРОЩЕННЫЙ ЗАПУСК (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем Node.js
Write-Host "Проверка Node.js..." -ForegroundColor Yellow
$nodeCheck = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCheck) {
    $nodeVersion = node --version
    Write-Host "✅ Node.js: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Node.js не установлен" -ForegroundColor Red
    Write-Host "Установите Node.js: https://nodejs.org/" -ForegroundColor Yellow
    Start-Process "https://nodejs.org/"
    exit 1
}

# Проверяем Python
Write-Host "Проверка Python..." -ForegroundColor Yellow
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCheck) {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} else {
    $python3Check = Get-Command python3 -ErrorAction SilentlyContinue
    if ($python3Check) {
        $pythonVersion = python3 --version 2>&1
        Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Python 3 не установлен" -ForegroundColor Red
        Write-Host "Установите Python 3: https://www.python.org/" -ForegroundColor Yellow
        Start-Process "https://www.python.org/"
        exit 1
    }
}

# Проверяем Ollama
Write-Host "🤖 Проверка Ollama..." -ForegroundColor Yellow
$ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaStarted = $false

if ($ollamaCheck) {
    Write-Host "✅ Ollama установлен" -ForegroundColor Green
    
    # Проверяем, запущен ли сервер Ollama
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
        Write-Host "   ✅ Сервер Ollama уже запущен" -ForegroundColor Green
    } catch {
        Write-Host "   🚀 Запуск сервера Ollama..." -ForegroundColor Yellow
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
        $ollamaStarted = $true
        Write-Host "   ✅ Ollama запущен" -ForegroundColor Green
        
        # Ждем запуска сервера
        Write-Host "   ⏳ Ожидание запуска сервера..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Проверяем, что сервер запустился
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
            Write-Host "   ✅ Сервер Ollama готов" -ForegroundColor Green
        } catch {
            Write-Host "   ⚠️  Не удалось запустить сервер Ollama. LLM функции могут не работать." -ForegroundColor Yellow
        }
    }
    
    # Проверяем наличие модели llama3.2
    Write-Host "   🔍 Проверка модели llama3.2..." -ForegroundColor Yellow
    try {
        $models = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
        if ($models.models.name -contains "llama3.2") {
            Write-Host "   ✅ Модель llama3.2 найдена" -ForegroundColor Green
        } else {
            Write-Host "   ⬇️  Модель llama3.2 не найдена. Загрузка..." -ForegroundColor Yellow
            Start-Process "ollama" -ArgumentList "pull llama3.2" -WindowStyle Hidden
            Write-Host "   ✅ Модель загружается в фоновом режиме" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ⚠️  Не удалось проверить модели" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  Ollama не установлен. LLM функции не будут доступны." -ForegroundColor Yellow
    Write-Host "   Установите Ollama: https://ollama.ai/" -ForegroundColor Yellow
    Write-Host "   Или используйте DeepSeek через настройки интерфейса." -ForegroundColor Yellow
}

Write-Host ""

# Останавливаем старые процессы
Write-Host "🧹 Останавливаю старые процессы..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Запускаем API
Write-Host "🔧 Запуск AI API..." -ForegroundColor Yellow
Write-Host "   Использую api_main.py с гарантированным выводом логов" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 ЗАПУСК API:" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Запускаем API в отдельном окне PowerShell
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python api_main.py 2>&1 | Tee-Object -FilePath api_startup.log
}

Write-Host "   📝 Логи API пишутся в: api_startup.log" -ForegroundColor Gray
Write-Host "   ⏳ Запуск API... (ожидание 10 секунд)" -ForegroundColor Yellow

# Даем время на запуск и проверяем порт
$apiPort = $null
for ($i = 1; $i -le 10; $i++) {
    # Проверяем файл с портом
    if (Test-Path "api_port.txt") {
        $apiPort = Get-Content "api_port.txt" -First 1
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:$apiPort/api/health" -TimeoutSec 1
            Write-Host "   ✅ API запущен на порту $apiPort" -ForegroundColor Green
            break
        } catch { }
    }
    
    # Также проверяем стандартные порты
    foreach ($port in @(5001, 5002, 5003, 5004, 5005, 5006, 5007, 5008, 5009, 5010)) {
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:$port/api/health" -TimeoutSec 1
            $apiPort = $port
            Write-Host "   ✅ API найден на порту $apiPort" -ForegroundColor Green
            break
        } catch { }
    }
    
    if ($apiPort) { break }
    
    Start-Sleep -Seconds 1
    Write-Host "   ⏳ Ожидание запуска API ($i/10)..." -ForegroundColor Gray
}

if (-not $apiPort) {
    Write-Host "   ⚠️  API порт не определен, использую порт по умолчанию 5009" -ForegroundColor Yellow
    $apiPort = 5009
    
    # Проверяем, работает ли API
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:$apiPort/api/health" -TimeoutSec 1
        Write-Host "   ✅ API работает на порту $apiPort" -ForegroundColor Green
    } catch {
        Write-Host "   ❌ API не запустился" -ForegroundColor Red
        Write-Host "   Пробую альтернативный способ..." -ForegroundColor Yellow
        Write-Host "   Откройте новый терминал и запустите:" -ForegroundColor Yellow
        Write-Host "   cd '$PWD'; python api_simple_with_cors.py" -ForegroundColor White
        Write-Host "   Затем в этом окне нажмите Enter..." -ForegroundColor Yellow
        Read-Host
    }
}

# Запускаем прокси
Write-Host "🔧 Запуск прокси..." -ForegroundColor Yellow
$proxyJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    node proxy-server.js
}

Start-Sleep -Seconds 3

# Проверяем прокси
$proxyOk = $false
for ($i = 1; $i -le 5; $i++) {
    $netstat = netstat -an | Select-String ":3000.*LISTENING"
    if ($netstat) {
        Write-Host "   ✅ Прокси запущен на порту 3000" -ForegroundColor Green
        $proxyOk = $true
        break
    }
    Start-Sleep -Seconds 1
    Write-Host "   ⏳ Ожидание запуска прокси (попытка $i/5)..." -ForegroundColor Gray
}

if (-not $proxyOk) {
    Write-Host "   ❌ Прокси не запустился" -ForegroundColor Red
    Write-Host "   Пробую альтернативный способ..." -ForegroundColor Yellow
    Write-Host "   Откройте новый терминал и запустите:" -ForegroundColor Yellow
    Write-Host "   cd '$PWD'; node proxy-server.js" -ForegroundColor White
    Write-Host "   Затем в этом окне нажмите Enter..." -ForegroundColor Yellow
    Read-Host
}

# Проверяем статус LLM
$llmStatus = "❌ Недоступен"
if ($ollamaCheck) {
    try {
        $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 1
        $llmStatus = "✅ Ollama (llama3.2)"
    } catch {
        $llmStatus = "⚠️  Ollama (сервер не запущен)"
    }
}

Write-Host ""
Write-Host "✅ СИСТЕМА ЗАПУЩЕНА!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 СЕРВЕРЫ:" -ForegroundColor Cyan
Write-Host "   • AI API:    http://localhost:$apiPort/api/health" -ForegroundColor Gray
Write-Host "   • Прокси:    http://localhost:3000" -ForegroundColor Gray
Write-Host "   • Редактор:  http://localhost:3000/proxy-index.html" -ForegroundColor Gray
Write-Host "   • LLM:       $llmStatus" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 ЛОГИ В РЕАЛЬНОМ ВРЕМЕНИ:" -ForegroundColor Cyan
Write-Host "   • Логи API пишутся в: api_startup.log" -ForegroundColor Gray
Write-Host "   • JSON модели будет виден после генерации" -ForegroundColor Gray
Write-Host "   • Подробные логи также в файле: api.log" -ForegroundColor Gray
Write-Host ""
Write-Host "🔍 ДЛЯ ПРОВЕРКИ:" -ForegroundColor Cyan
Write-Host "   API здоровье: curl http://localhost:$apiPort/api/health" -ForegroundColor Gray
Write-Host "   Прокси работает: curl http://localhost:3000/api/health" -ForegroundColor Gray
Write-Host ""

Write-Host "🎯 ЧТО ДЕЛАТЬ ДАЛЬШЕ:" -ForegroundColor Cyan
Write-Host "   1. Браузер должен открыться автоматически" -ForegroundColor Gray
Write-Host "   2. Если нет, откройте: http://localhost:3000/proxy-index.html" -ForegroundColor Gray
Write-Host "   3. Нажмите кнопку 'Graph Manager' (в правом верхнем углу графа)" -ForegroundColor Gray
Write-Host "   4. Загрузите файл (.txt, .md, .pdf) или введите текст ТЗ" -ForegroundColor Gray
Write-Host "   5. Нажмите 'Отправить' для генерации модели" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 ЕСЛИ ВОЗНИКЛИ ПРОБЛЕМЫ:" -ForegroundColor Cyan
Write-Host "   • Проверьте, что порты 3000 и $apiPort свободны" -ForegroundColor Gray
Write-Host "   • Перезапустите скрипт: .\launch.ps1" -ForegroundColor Gray
Write-Host "   • Подробная документация: README.md" -ForegroundColor Gray
Write-Host ""
Write-Host "🛑 ДЛЯ ОСТАНОВКИ:" -ForegroundColor Cyan
Write-Host "   Закройте это окно или нажмите Ctrl+C" -ForegroundColor Gray
Write-Host ""

# Открываем браузер
Write-Host "🌐 Открываю Graph Editor..." -ForegroundColor Yellow
Start-Process "http://localhost:3000/proxy-index.html"

Write-Host ""
Write-Host "Нажмите любую клавишу для выхода или Ctrl+C для остановки системы..."
Write-Host ""

# Обработчик для Ctrl+C
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Write-Host ""
    Write-Host "🧹 Остановка системы..." -ForegroundColor Yellow
    
    # Останавливаем задания
    if ($apiJob) { Stop-Job $apiJob -Force }
    if ($proxyJob) { Stop-Job $proxyJob -Force }
    
    # Останавливаем процессы
    Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    
    if ($ollamaStarted) {
        Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "   Остановлен Ollama" -ForegroundColor Gray
    }
    
    Write-Host "✅ Система остановлена" -ForegroundColor Green
    exit 0
}

# Ждем нажатия клавиши или Ctrl+C
try {
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} catch {
    # Пользователь нажал Ctrl+C
}

# Вызываем событие выхода
[System.Environment]::Exit(0)