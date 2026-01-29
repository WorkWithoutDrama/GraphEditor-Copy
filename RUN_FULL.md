# Запуск Graph Editor в полном режиме

## Требования
- Node.js (для прокси-сервера)
- Python 3 (для AI API)

## Шаг 1: Запустите AI API сервер
```bash
# Терминал 1
python api.py
```
API сервер запустится на `http://localhost:5000`

## Шаг 2: Запустите прокси-сервер
```bash
# Терминал 2
node proxy-server.js
```
Прокси-сервер запустится на `http://localhost:3000`

## Шаг 3: Откройте Graph Editor
Откройте в браузере:
```
http://localhost:3000/proxy-index.html
```

ИЛИ используйте прямой файл:
```bash
# Просто откройте proxy-index.html в браузере
# Он автоматически найдет API через прокси
```

## Что происходит:
1. **Прокси-сервер** (`localhost:3000`) решает проблему CORS
2. **API сервер** (`localhost:5000`) обрабатывает AI запросы  
3. **Браузер** общается с прокси, прокси общается с API

## Альтернативные способы:

### Способ A: Без прокси (только для разработки Chrome)
```bash
# Запустите Chrome с отключенной безопасностью:
open -n -a /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --args --user-data-dir="/tmp/chrome_dev_test" --disable-web-security
# Затем откройте index.html
```

### Способ B: Через локальный веб-сервер
```bash
python serve.py  # Запустит сервер на localhost:8000
# Откройте http://localhost:8000
```

### Способ C: Демо-режим (без API)
```bash
# Просто откройте index.html
# Будет работать в демо-режиме
```

## Устранение неполадок:

### API недоступен
1. Проверьте, что `api.py` запущен: `http://localhost:5000/api/health`
2. Проверьте, что `proxy-server.js` запущен: `http://localhost:3000`

### CORS ошибки
Убедитесь, что вы открываете через `http://localhost:3000/proxy-index.html`, а не как `file://`

### Graph Manager не открывается
Проверьте консоль браузера (F12) на ошибки JavaScript

## Быстрый старт:
```bash
# В трех разных терминалах:
python api.py
node proxy-server.js
open http://localhost:3000/proxy-index.html
```

Теперь Graph Manager будет работать в **полном режиме** с AI API!