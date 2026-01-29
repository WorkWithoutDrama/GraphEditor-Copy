# Graph Editor with AI Assistant

A web-based graph editor with integrated AI assistant that converts system descriptions into graph models.

## 🚀 Quick Start

### For macOS Users:
1. **Double-click** `WORK.command`
2. **Allow execution** if prompted
3. **Wait** for browser to open
4. **Click "Graph Manager"** in the editor
5. **Describe your system** or upload a file

### Requirements:
- **Node.js** (https://nodejs.org/)
- **Python 3** (https://python.org/)

## 📋 Features

- **Interactive Graph Editor**: Create and edit graphs visually
- **AI Assistant**: Convert text descriptions to graph models  
- **File Support**: Import/export JSON, text, PDF files
- **Real-time Editing**: Add nodes, edges, modify structure
- **Responsive Design**: Works on desktop browsers

## 🏗️ Architecture

```
Browser → Proxy (localhost:3000) → AI API (localhost:5000+)
```

## 📁 Files

### Core Files:
- `WORK.command` - Launch script (macOS)
- `api.py` - AI API server (Python)
- `proxy-fixed.js` - Proxy server (Node.js)
- `proxy-index.html` - Main editor interface
- `graph-manager.js` - AI chat interface
- `script.js` - Graph editor logic

### Utilities:
- `cleanup.command` - Clean ports if occupied
- `check-deps.command` - Check dependencies
- `.gitignore` - Git ignore rules

## 🛠️ Development

### Running Manually:
```bash
# Terminal 1: AI API
python3 api.py

# Terminal 2: Proxy
node proxy-fixed.js

# Browser: Open http://localhost:3000
```

### Troubleshooting:
```bash
# Clean ports:
./cleanup.command

# Check dependencies:
./check-deps.command

# Fix permissions:
chmod +x *.command
```

## 🎯 Usage Example

1. Launch with `WORK.command`
2. Describe: "User registration system with email validation"
3. AI creates graph with:
   - Nodes: "User registers", "System validates email", "Account created"
   - Edges: Connections between actions
4. Edit and refine the generated graph

## 📄 License

Educational/development use.

## 🤝 Support

1. Ensure Node.js and Python 3 are installed
2. Run `check-deps.command` to verify
3. Use `cleanup.command` if ports are busy
4. Check browser console for errors

---

**Graph Editor: Transform descriptions into visual models**

### Способ 1: Автоматический запуск (рекомендуется)
```bash
# macOS/Linux
./start-full.sh

# Windows
start-full.bat
```

### Способ 2: Вручную (3 терминала)

#### Терминал 1: AI API сервер
```bash
python api.py
```
**Должно появиться:** `Запуск API сервера на порту 5000...`

#### Терминал 2: Прокси сервер
```bash
node proxy-server.js
```
**Должно появиться:** `Proxy server running on http://localhost:3000`

#### Терминал 3: Открыть браузер
Откройте в браузере:
```
http://localhost:3000/proxy-index.html
```

## Что происходит при ошибке:

Если серверы не запущены, Graph Manager покажет:

```
❌ Graph Manager не может подключиться к AI API

📋 Требуется запуск серверов:

1. Запустите AI API сервер
   python api.py

2. Запустите прокси сервер
   node proxy-server.js

3. Обновите страницу после запуска серверов
```

## Архитектура:
```
[Ваш браузер] → [Прокси (localhost:3000)] → [AI API (localhost:5000)]
```

## Проверка работы:

1. **AI API сервер:** http://localhost:5000/api/health
   - Должен вернуть `{"status": "ok"}`

2. **Прокси сервер:** http://localhost:3000
   - Должна открыться страница прокси

3. **Graph Editor:** http://localhost:3000/proxy-index.html
   - Должен открыться редактор с работающим Graph Manager

## Устранение неполадок:

### ❌ "Прокси недоступен"
```
./start-simple.sh
```
Скрипт проверит и покажет что запустить.

### ❌ "API недоступен"
Убедитесь, что `api.py` запущен и отвечает:
```bash
curl http://localhost:5000/api/health
```

### ❌ "CORS ошибка"
Всегда открывайте через `http://localhost:3000/proxy-index.html`
НЕ открывайте как `file://`

## Важные файлы:

- `proxy-index.html` - основная страница (работает через прокси)
- `proxy-server.js` - прокси сервер (решает CORS)
- `api.py` - AI API сервер
- `start-full.sh` / `start-full.bat` - автоматический запуск
- `start-simple.sh` - проверка и инструкции

## После запуска:
1. Нажмите кнопку **"Graph Manager"** в редакторе
2. Отправьте описание системы или загрузите файл
3. AI создаст графовую модель

**Готово! Теперь Graph Manager работает в полном режиме с AI API.**