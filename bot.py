import os
import json
import requests
import logging
from pydantic import BaseModel, Field, ValidationError, RootModel
from telegram import Update, File, InlineKeyboardMarkup, InlineKeyboardButton, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import graphviz

# Импорт fitz для работы с PDF (если установлен)
try:
    import fitz # PyMuPDF
except ImportError:
    fitz = None
    
# --- 1. КОНФИГУРАЦИЯ ---
# ЗАМЕНИТЕ ЭТО НА СВОЙ ТОКЕН TELEGRAM
TELEGRAM_BOT_TOKEN = "8211210757:AAHdbM8PxWUyCJchgi2hTy-ie9gd0W0kmB8" # <-- Вставьте сюда свой настоящий токен.
OPENROUTER_API_KEY = "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"

# УКАЗАННЫЕ ВАМИ КОНСТАНТЫ ДЛЯ OPENROUTER
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "deepseek/deepseek-chat" 

# Настройка логгера
logger = logging.getLogger(__name__)

# --- 2. МОДЕЛЬ ДАННЫХ Pydantic (Для валидации JSON) ---
class ActionModel(BaseModel):
    """Модель одного действия/перехода."""
    init_states: list[str] = Field(description="Список состояний системы, при которых возможно действие.")
    final_states: list[str] = Field(description="Список состояний системы, которые наступают после действия.")

class SystemModel(RootModel):
    """Модель всей системы: словарь 'Название действия': ActionModel."""
    root: dict[str, ActionModel] 

# --- 3. Функции обработки документов (Эмуляция RAG) ---
def extract_text_from_file(file_path: str) -> str:
    """Простая функция для извлечения текста (поддержка TXT и PDF, если fitz установлен)."""
    try:
        file_path_lower = file_path.lower()
        
        if file_path_lower.endswith(('.txt', '.md')):
            with open(file_path, 'r', encoding='utf-8') as f:
                logger.info(f"Извлечение текста из TXT/MD файла: {file_path}")
                return f.read()
        
        elif file_path_lower.endswith('.pdf') and fitz:
            text = ""
            logger.info(f"Извлечение текста из PDF файла (PyMuPDF): {file_path}")
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text
            
        else:
            if not fitz and file_path_lower.endswith('.pdf'):
                 logger.warning("PyMuPDF (fitz) не установлен. PDF не поддерживается.")
            logger.warning(f"Неподдерживаемый формат файла: {file_path}")
            return "Не удалось извлечь текст из файла. Формат не поддерживается или не установлена библиотека PyMuPDF."

    except Exception as e:
        logger.error(f"Ошибка при чтении файла {file_path}: {e}", exc_info=True)
        return ""


# --- 4. Функция вызова OpenRouter ---
def generate_model_from_text(document_text: str) -> dict | None:
    """Отправляет текст ТЗ в OpenRouter и получает JSON-модель."""
    logger.info("Отправка запроса на генерацию модели в OpenRouter...")
    
    # ИЗМЕНЕНИЕ: Обновленный системный промпт, требующий указания инициатора
    system_prompt = (
        "Ты — высококвалифицированный архитектор систем. Твоя задача — "
        "проанализировать предоставленный текст технического задания (ТЗ) и "
        "сформировать модель системы в виде **JSON-объекта**. "
        "Каждый ключ JSON — это **действие/переход**. "
        "**Крайне важно:** каждое название действия должно начинаться с его инициатора: "
        "'**Пользователь**' (для действий, инициированных человеком) или '**Система**' (для автоматических действий, расчетов или отображения данных). "
        "Пример требуемого формата: "
        '{"Пользователь регистрируется": {"init_states": ["Нет сессии"], "final_states": ["Пользователь зарегистрирован"]}, '
        '"Система рассчитывает норму": {"init_states": ["Личные данные сохранены"], "final_states": ["Базовая норма рассчитана"]}, ...}'
        "Значение — это объект с двумя полями: 'init_states' (список условий/состояний "
        "системы, необходимых для выполнения действия) и 'final_states' (список "
        "состояний системы, наступающих после выполнения действия). "
        "**Обязательно** выводи только чистый JSON-объект, без пояснений, кода или '```json'. "
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "[https://github.com/myrepo/system-model-bot](https://github.com/myrepo/system-model-bot)",
        "X-Title": "System Model Generator Bot",
    }

    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "top_p": 0.5,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Проанализируй следующее техническое задание и сгенерируй модель в JSON-формате:\n\n---\n{document_text}"}
        ],
    }

    raw_content = ""
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        
        # Получаем текст ответа
        raw_content = response.json()['choices'][0]['message']['content'].strip()
        
        # Очистка и парсинг JSON 
        if raw_content.startswith('```'):
            raw_content = raw_content.strip('`').lstrip('json').strip()
        
        # Валидация JSON по Pydantic модели
        parsed_json = json.loads(raw_content)
        
        validated_model = SystemModel.model_validate(parsed_json)
        
        # ИСПРАВЛЕНИЕ ОШИБКИ: Используем model_dump() для преобразования объектов Pydantic в чистые словари Python.
        pure_python_dict = validated_model.model_dump()
        
        logger.info("Успешная генерация и валидация модели.") 
        return pure_python_dict # Возвращаем чистый словарь, готовый к json.dumps()

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка HTTP-запроса к OpenRouter: {e}") 
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON от OpenRouter: {e}. Сырой ответ: {raw_content[:500]}") 
        return None
    except ValidationError as e:
        logger.error(f"Ошибка валидации Pydantic: {e}") 
        return None
    except Exception as e:
        logger.error(f"Неизвестная ошибка при генерации модели: {e}", exc_info=True) 
        return None


# --- 5. Функция создания графа Graphviz ---
# ИЗМЕНЕНО: Теперь генерирует и SVG, и DOT/TXT файлы.
def generate_graph_files(model_json: dict, filename: str = "system_model") -> list[str]:
    """Генерирует граф Graphviz в форматах SVG и DOT (текстовый исходник)."""
    
    logger.info("Начало генерации графа Graphviz (DOT и SVG).")
    
    dot = graphviz.Digraph(comment='System State Model', format='svg', engine='dot')
    dot.attr(rankdir='TB') # Граф сверху вниз (Top to Bottom)
    
    for action, details in model_json.items():
        # 1. Действие как прямоугольный узел
        dot.node(action, action, shape='box')
        
        # 2. Связи "init_states" -> Действие
        for init_state in details.get('init_states', []):
            dot.node(init_state, init_state, shape='ellipse')
            dot.edge(init_state, action)
            
        # 3. Связи Действие -> "final_states"
        for final_state in details.get('final_states', []):
            dot.node(final_state, final_state, shape='ellipse')
            dot.edge(action, final_state)

    generated_files = []
    temp_dir = './temp_graphs'
    
    try:
        # 1. Создание папки
        os.makedirs(temp_dir, exist_ok=True)
        full_path = os.path.join(temp_dir, filename)
        
        # 2. Рендеринг SVG (визуальный файл)
        # Устанавливаем format='svg' и cleanup=False, чтобы сохранить исходный DOT-файл
        dot.render(full_path, format='svg', view=False, cleanup=False) 
        svg_path = f"{full_path}.svg"
        
        if os.path.exists(svg_path):
            generated_files.append(svg_path)
            logger.info(f"Граф успешно сгенерирован в SVG файл: {svg_path}")
        
        # 3. Сохранение DOT (текстовый исходник)
        # Graphviz сохраняет DOT исходник в файл с расширением .gv
        dot_path = f"{full_path}.gv" 
        
        if os.path.exists(dot_path):
             # Переименуем его в .txt для удобства чтения пользователем
            txt_path = f"{full_path}.txt"
            os.rename(dot_path, txt_path)
            generated_files.append(txt_path)
            logger.info(f"Граф успешно сгенерирован в DOT/TXT файл: {txt_path}")
        else:
            # Если DOT файл не был создан автоматически, сохраним его вручную
            dot_source_path = f"{full_path}_source.txt"
            with open(dot_source_path, 'w', encoding='utf-8') as f:
                f.write(dot.source)
            generated_files.append(dot_source_path)
            logger.warning("DOT файл не был создан автоматически, сохранен вручную.")
            
        return generated_files
        
    except graphviz.backend.ExecutableNotFound:
        logger.error("Ошибка: Исполняемый файл Graphviz (dot) не найден. Убедитесь, что Graphviz установлен в вашей системе и добавлен в PATH.")
        return []
    except Exception as e:
        logger.error(f"Ошибка при генерации графа: {e}", exc_info=True)
        return []


# --- 6. ОБРАБОТЧИКИ TELEGRAM ---

# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение и инструкцию."""
    logger.info(f"Получена команда /start от пользователя {update.effective_user.id}")
    keyboard = [
        [InlineKeyboardButton("Начать анализ ТЗ", callback_data='analyze_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "🤖 **Бот-Архитектор Систем**\n\n"
        "Я могу автоматически построить модель состояний и переходов системы (как на диаграммах UML State Machine) "
        "на основе вашего **Технического Задания (ТЗ)**.\n\n"
        "1. **Загрузите документ ТЗ** (рекомендуется .txt, .md или .pdf).\n"
        "2. Я проанализирую его с помощью AI (OpenRouter) и выдам **JSON-модель**, **SVG-граф** и **исходник DOT/TXT**."
    )
    await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN, reply_markup=reply_markup)

# Обработка Inline-кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'analyze_start':
        logger.info(f"Нажата кнопка 'Начать анализ ТЗ' от пользователя {query.from_user.id}")
        await query.edit_message_text(
            "Отлично! Теперь, пожалуйста, **отправьте мне файл** с вашим Техническим Заданием (.txt, .md, или .pdf).",
            parse_mode=constants.ParseMode.MARKDOWN
        )

# Обработка документа
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает загруженный файл ТЗ."""
    document = update.message.document
    user_id = update.effective_user.id
    file_name = document.file_name
    
    logger.info(f"Пользователь {user_id} загрузил файл: {file_name} (ID: {document.file_id})")
    
    # Расширения для поддержки
    allowed_extensions = ('.txt', '.md', '.pdf')
    if not file_name.lower().endswith(allowed_extensions):
        logger.warning(f"Пользователь {user_id} загрузил неподдерживаемый формат: {file_name}")
        await update.message.reply_text(f"❌ Неподдерживаемый формат. Пожалуйста, загрузите файл с одним из расширений: {', '.join(allowed_extensions)}")
        return
        
    if document.file_size > 5 * 1024 * 1024: # Ограничение 5MB
        logger.warning(f"Пользователь {user_id} загрузил слишком большой файл: {file_name} ({document.file_size} байт)")
        await update.message.reply_text("Файл слишком большой. Пожалуйста, загрузите документ размером до 5MB.")
        return

    message = await update.message.reply_text(
        "⏳ **Получен документ.** Начинаю извлечение текста и анализ с помощью AI (OpenRouter). Это может занять до минуты...",
        parse_mode=constants.ParseMode.MARKDOWN
    )

    # 1. Загрузка файла
    temp_file_name = file_name
    try:
        new_file = await context.bot.get_file(document.file_id)
        # Сохраняем файл локально
        await new_file.download_to_drive(custom_path=temp_file_name) 
        logger.info(f"Файл {temp_file_name} успешно загружен локально.")
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {temp_file_name} с Telegram: {e}")
        await message.edit_text("❌ **Ошибка загрузки файла.** Попробуйте еще раз.")
        return

    # 2. Извлечение текста (Эмуляция RAG)
    document_text = extract_text_from_file(temp_file_name)
    os.remove(temp_file_name) # Удаляем временный файл
    logger.info(f"Временный файл {temp_file_name} удален.")
    
    if "Не удалось извлечь текст" in document_text or len(document_text) < 100:
        logger.error(f"Ошибка извлечения текста или текст слишком короткий ({len(document_text)} символов) для файла {file_name}.")
        await message.edit_text(document_text.replace('Ошибка:', '❌') + "\n\nПроверьте содержимое и формат файла.")
        return

    await message.edit_text(
        f"✅ **Текст извлечен** ({len(document_text)} символов). Запрос отправлен в OpenRouter для генерации модели...",
        parse_mode=constants.ParseMode.MARKDOWN
    )
    
    # 3. Генерация модели
    model_json = generate_model_from_text(document_text)
    
    if model_json is None:
        await message.edit_text(
            "❌ **Ошибка генерации модели.** AI не смог создать корректный JSON-объект, или произошла внутренняя ошибка.",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    # 4. Форматирование JSON для отправки
    json_output = json.dumps(model_json, ensure_ascii=False, indent=2)
    
    # 5. Генерация графа Graphviz (получаем список файлов: SVG и DOT/TXT)
    generated_files = generate_graph_files(model_json)
    
    # --- Отправка результатов ---
    
    # Отправка JSON
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=bytes(json_output, 'utf-8'),
        filename="system_model.json",
        caption="✅ **Модель системы (JSON):**"
    )
    logger.info(f"JSON-модель отправлена пользователю {user_id}.")

    # Отправка Графа (SVG и DOT/TXT)
    graph_files_sent = False
    
    for file_path in generated_files:
        filename_base = os.path.basename(file_path)
        if filename_base.lower().endswith('.svg'):
            caption = "✅ **Граф состояний и переходов (SVG):**\n\n_Прямоугольники: Действия (начинаются с инициатора: Пользователь/Система).\nЭллипсы: Состояния._"
            graph_files_sent = True
        elif filename_base.lower().endswith('.txt'):
            caption = "📝 **Исходный код графа (DOT/TXT):**\n\n_Используется для ручного редактирования или отладки Graphviz._"
            graph_files_sent = True
        else:
            continue
            
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        filename=filename_base,
                        caption=caption
                    )
                logger.info(f"Файл {filename_base} отправлен пользователю {user_id}.")
            except Exception as e:
                logger.error(f"Ошибка при отправке файла {file_path}: {e}")
            
            os.remove(file_path) # Удаляем временный файл

    # Очистка временной папки, если она пуста
    temp_dir = './temp_graphs'
    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
        try:
            os.rmdir(temp_dir)
            logger.info(f"Временная папка {temp_dir} удалена.")
        except OSError as e:
            logger.warning(f"Не удалось удалить временную папку {temp_dir}: {e}")
            
    if graph_files_sent:
        await message.edit_text(f"🎉 **Готово!** Анализ завершен. JSON, Граф SVG и исходник DOT/TXT отправлены.", parse_mode=constants.ParseMode.MARKDOWN)
    else:
        # Если файлы графа не были отправлены, но JSON был
        await message.edit_text(
            f"⚠️ **Модель JSON сгенерирована, но граф не создан.** Проверьте консоль: возможно, Graphviz не установлен в системе.",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        
        
# --- 7. Основная функция запуска ---
def main():
    """Запускает бота."""
    
    # Конфигурация логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler("bot.log", encoding="utf-8"), # Логи в файл
            logging.StreamHandler() # Логи в консоль
        ]
    )
    
    # Проверка токена
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "ВАШ_ТОКЕН_ТЕЛЕГРАМ_БОТА":
        logger.error("❌ Ошибка: Установите TELEGRAM_BOT_TOKEN в файле bot.py.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(MessageHandler(filters.ATTACHMENT & filters.Document.ALL, handle_document))
    application.add_handler(CallbackQueryHandler(button_handler)) 

    # Обработка текстовых сообщений, чтобы не ломать бота
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_command))
    
    logger.info("🚀 Бот запущен и готов к работе.") 
    application.run_polling(poll_interval=3)
    logger.info("👋 Бот остановлен.") 

if __name__ == '__main__':
    main()