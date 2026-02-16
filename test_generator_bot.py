import json
import io
import telebot
from telebot.types import Message, Document
import logging
import zipfile  # <-- 1. Добавлен импорт zipfile

# --- НАСТРОЙКА ЛОГГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# -------------------------------

# Вставь токен бота
TOKEN = ""

# ------------------------------------------------------------------
# Класс-генератор 
# ------------------------------------------------------------------

class BDDGenerator:
    """
    Класс инкапсулирует логику генерации BDD-сценариев.
    """
    def __init__(self, model: dict):
        self.model = model
        self.states = {}
        self.ways_to_action_cache = {}
        self.ways_to_state_cache = {}
        self._build_states_map()
        logger.debug("Карта состояний построена.")

    def _build_states_map(self):
        for action_name, action_data in self.model.items():
            for final_state in action_data["final_states"]:
                if final_state not in self.states:
                    self.states[final_state] = {"actions": []}
                self.states[final_state]["actions"].append(action_name)

    def get_ways_to_action(self, action_name: str) -> list[list[str]]:
        if action_name in self.ways_to_action_cache:
            return self.ways_to_action_cache[action_name]

        action = self.model[action_name]
        init_states = action["init_states"]

        if not init_states:
            self.ways_to_action_cache[action_name] = []
            return []

        ways_to_states = {}
        
        for init_state in init_states:
            if init_state not in self.states:
                self.ways_to_action_cache[action_name] = []
                return []
            
            ways_to_state = self.get_ways_to_state(init_state)
            
            if not ways_to_state:
                self.ways_to_action_cache[action_name] = []
                return []
                
            ways_to_states[init_state] = ways_to_state

        final_ways: list[list[str]] = []
        for state_name, ways_to_state in ways_to_states.items():
            if len(final_ways) == 0:
                final_ways = ways_to_state
                continue

            merged_ways: list[list[str]] = []
            for way_left in final_ways:
                for way_right in ways_to_state:
                    merged_path = list(dict.fromkeys(way_left + way_right))
                    merged_ways.append(merged_path)
            final_ways = merged_ways

        self.ways_to_action_cache[action_name] = final_ways
        return final_ways

    def get_ways_to_state(self, state_name: str) -> list[list[str]]:
        if state_name in self.ways_to_state_cache:
            return self.ways_to_state_cache[state_name]

        if state_name not in self.states:
            self.ways_to_state_cache[state_name] = []
            return []

        state = self.states[state_name]
        all_ways_to_state: list[list[str]] = []

        for action_name in state["actions"]:
            prereq_paths = self.get_ways_to_action(action_name)

            if len(prereq_paths) == 0:
                final_paths_for_action = [[action_name]]
            else:
                final_paths_for_action = []
                for path in prereq_paths:
                    new_path = path.copy()
                    new_path.append(action_name)
                    final_paths_for_action.append(new_path)
            
            all_ways_to_state.extend(final_paths_for_action)

        self.ways_to_state_cache[state_name] = all_ways_to_state
        return all_ways_to_state

    def generate_all_bdd_files(self) -> dict[str, str]:
        all_files = {}

        for action_name in self.model.keys():
            logger.info(f"Генерация BDD для действия: '{action_name}'")
            prereq_paths = self.get_ways_to_action(action_name)
            final_states = self.model[action_name]["final_states"]

            if not prereq_paths:
                prereq_paths = [[]] 
            
            txt_content = f"Функциональность: {action_name}\n\n"
            
            for i, path in enumerate(prereq_paths):
                scenario_num = i + 1
                txt_content += f"Сценарий {scenario_num} {action_name}\n"
                
                for step in path:
                    txt_content += f"Когда {step}\n"
                
                txt_content += f"Когда {action_name}\n"
                
                for state in final_states:
                    txt_content += f"Тогда {state}\n"
                
                txt_content += "\n"
            
            safe_name = "".join(c for c in action_name if c.isalnum() or c in " _-").rstrip()
            filename = f"{safe_name.replace(' ', '_')}.txt"
            
            all_files[filename] = txt_content
            
        return all_files

# ------------------------------------------------------------------
# Основная логика обработки и отправки (с архивацией)
# ------------------------------------------------------------------

bot = telebot.TeleBot(TOKEN)

def process_json_data(message: Message, model: dict):
    """
    Функция для обработки, генерации и отправки BDD-сценариев и ZIP-архива.
    """
    chat_id = message.chat.id
    user_info = f"{chat_id} ({message.from_user.username})"

    try:
        bot.send_message(chat_id, "✅ JSON принят. Начинаю генерацию BDD-сценариев... 🤖")
        
        logger.info(f"Начало генерации BDD для {user_info}...")
        
        generator = BDDGenerator(model)
        all_files = generator.generate_all_bdd_files()
        
        if not all_files:
            logger.warning(f"Для {user_info} не сгенерировано ни одного файла (модель пуста?).")
            bot.send_message(chat_id, "⚠️ Не удалось сгенерировать ни одного файла. Модель пуста?")
            return

        file_count = len(all_files)
        logger.info(f"Генерация для {user_info} завершена. Сгенерировано {file_count} файлов.")
        
        # --- 2. ГЕНЕРАЦИЯ ZIP-АРХИВА В ПАМЯТИ ---
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # Отправка каждого файла и добавление его в архив
            for filename, content in all_files.items():
                file_bytes = content.encode('utf-8')
                
                # Отправка каждого файла по отдельности (для просмотра в Telegram)
                file_stream = io.BytesIO(file_bytes)
                file_stream.name = filename
                bot.send_document(chat_id, file_stream, disable_notification=True)
                
                # Добавление файла в ZIP-архив
                zipf.writestr(filename, file_bytes)

        zip_buffer.seek(0)
        
        # --- 3. ОТПРАВКА ZIP-АРХИВА ---
        zip_filename = f"BDD_scenarios_{chat_id}.zip"
        logger.info(f"Отправка ZIP-архива ({zip_filename}) пользователю {user_info}")
        
        # Создаем файловый поток для отправки ZIP-архива
        zip_stream = io.BytesIO(zip_buffer.read())
        zip_stream.name = zip_filename

        bot.send_document(
            chat_id, 
            zip_stream, 
            caption=f"✅ Готово! Сгенерировано {file_count} BDD-сценариев. Все файлы также собраны в этом архиве."
        )

    except RecursionError:
        logger.error(f"Ошибка рекурсии для {user_info}. Вероятны циклические зависимости в модели.")
        bot.send_message(chat_id, 
            "❌ **Ошибка!**\nОбнаружена бесконечная рекурсия. Пожалуйста, проверь свою модель на **циклические зависимости**.")
    except Exception as e:
        logger.critical(f"Критическая ошибка при обработке модели для {user_info}: {e}", exc_info=True)
        bot.send_message(chat_id, f"❌ **Произошла критическая ошибка при обработке модели:**\n`{e}`\n\nПроверь логику состояний. (Детали см. в `bot.log`)")


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: Message):
    logger.info(f"Пользователь {message.chat.id} ({message.from_user.username}) отправил /start")
    bot.reply_to(message, 
        "Привет! 🤖\n"
        "**Отправь мне файл .json** с твоей моделью (или вставь JSON как обычный текст). "
        "Я сгенерирую BDD-сценарии и отправлю их в виде отдельных `.txt` файлов, а также одним **ZIP-архивом**.")

# ------------------------------------------------------------------
# 1. ОБРАБОТЧИК ДЛЯ JSON-ФАЙЛОВ (.json)
# ------------------------------------------------------------------
@bot.message_handler(content_types=['document'])
def handle_document_json(message: Message):
    chat_id = message.chat.id
    user_info = f"{chat_id} ({message.from_user.username})"
    
    if not message.document.file_name.lower().endswith('.json'):
        logger.warning(f"Получен неподходящий документ от {user_info}: {message.document.file_name}")
        bot.reply_to(message, "❌ **Ошибка!**\nПожалуйста, отправь файл с расширением **.json**.")
        return

    try:
        logger.info(f"Получен .json файл ({message.document.file_name}) от {user_info}. Начинаю загрузку...")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        json_string = downloaded_file.decode('utf-8')
        model = json.loads(json_string)
        
        process_json_data(message, model)
        
    except json.JSONDecodeError as e:
        logger.warning(f"Ошибка декодирования JSON в файле от {user_info}. Ошибка: {e}")
        bot.reply_to(message, f"❌ **Ошибка!**\nНе удалось распознать JSON в файле. Проверь синтаксис.\n\n`{e}`")
    except Exception as e:
        logger.error(f"Ошибка обработки файла от {user_info}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ **Критическая ошибка при загрузке файла:**\n`{e}`")

# ------------------------------------------------------------------
# 2. ОБРАБОТЧИК ДЛЯ JSON В ВИДЕ ЧИСТОГО ТЕКСТА
# ------------------------------------------------------------------
@bot.message_handler(content_types=['text'])
def handle_text_json(message: Message):
    chat_id = message.chat.id
    user_info = f"{chat_id} ({message.from_user.username})"
    logger.info(f"Получено текстовое сообщение от {user_info}. Пробую парсить как JSON...")
    
    try:
        cleaned_text = message.text.replace("‘", "'").replace("’", "'").replace('“', '"').replace('”', '"').replace('«', '"').replace('»', '"')
        
        model = json.loads(cleaned_text)
        logger.info(f"JSON-текст от {user_info} успешно распознан.")
        
        process_json_data(message, model)
        
    except json.JSONDecodeError as e:
        logger.debug(f"Текст от {user_info} не является JSON. Игнорирую.")
        pass
    except Exception as e:
        logger.error(f"Неизвестная ошибка при чтении JSON-текста от {user_info}: {e}", exc_info=True)
        bot.reply_to(message, f"❌ **Произошла неизвестная ошибка при чтении:**\n`{e}`")


print("Бот запущен и готов к работе...")
logger.info("=" * 30)
logger.info("Бот успешно запущен и готов к работе.")
logger.info("=" * 30)

bot.infinity_polling()
