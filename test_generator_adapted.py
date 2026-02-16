#!/usr/bin/env python3
"""
Адаптированный генератор тестов для структуры test_project.json
Основан на алгоритме из test_generator_bot.py
"""

import json
import os
import zipfile
import io
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BDDGeneratorSimple:
    """
    Упрощенная версия BDDGenerator без зависимостей
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
            for final_state in action_data.get("final_states", []):
                if final_state not in self.states:
                    self.states[final_state] = {"actions": []}
                self.states[final_state]["actions"].append(action_name)

    def get_ways_to_action(self, action_name: str):
        if action_name in self.ways_to_action_cache:
            return self.ways_to_action_cache[action_name]

        action = self.model.get(action_name, {})
        init_states = action.get("init_states", [])

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

        final_ways = []
        for state_name, ways_to_state in ways_to_states.items():
            if len(final_ways) == 0:
                final_ways = ways_to_state
                continue

            merged_ways = []
            for way_left in final_ways:
                for way_right in ways_to_state:
                    merged_path = list(dict.fromkeys(way_left + way_right))
                    merged_ways.append(merged_path)
            final_ways = merged_ways

        self.ways_to_action_cache[action_name] = final_ways
        return final_ways

    def get_ways_to_state(self, state_name: str):
        if state_name in self.ways_to_state_cache:
            return self.ways_to_state_cache[state_name]

        if state_name not in self.states:
            self.ways_to_state_cache[state_name] = []
            return []

        state = self.states[state_name]
        all_ways_to_state = []

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

    def generate_all_bdd_files(self):
        all_files = {}

        for action_name in self.model.keys():
            logger.info(f"Генерация BDD для действия: '{action_name}'")
            prereq_paths = self.get_ways_to_action(action_name)
            final_states = self.model[action_name].get("final_states", [])

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


class BDDGeneratorAdapted:
    """
    Адаптированный генератор BDD-сценариев для структуры test_project.json
    """
    
    def __init__(self, model_data):
        """
        Инициализация генератора для структуры test_project.json
        
        Args:
            model_data: Данные модели в формате test_project.json
        """
        self.model_data = model_data
        self.states = {}
        self.ways_to_action_cache = {}
        self.ways_to_state_cache = {}
        
        # Преобразуем нашу структуру в формат для BDDGenerator
        self.simple_model = self._convert_to_simple_format()
        
        # Инициализируем оригинальный генератор
        self.bdd_generator = BDDGeneratorSimple(self.simple_model)
        
        logger.info(f"Инициализирован адаптированный генератор для {len(self.simple_model)} действий")
    
    def _convert_to_simple_format(self):
        """
        Преобразует структуру test_project.json в простой формат для BDDGenerator
        
        Возвращает:
            dict в формате {action_name: {"init_states": [], "final_states": []}}
        """
        simple_model = {}
        
        # Строим карту состояний: state_id -> state_name
        state_map = {}
        for obj in self.model_data.get('model_objects', []):
            object_id = obj.get('object_id')
            object_name = obj.get('object_name', '')
            
            for state in obj.get('resource_state', []):
                state_id = state.get('state_id')
                state_name = state.get('state_name', '')
                state_map[state_id] = f"{object_name} {state_name}"
        
        # Строим карту связей: action_id -> {init_states: [], final_states: []}
        action_states = {}
        
        # Инициализируем все действия
        for action in self.model_data.get('model_actions', []):
            action_id = action.get('action_id')
            action_name = action.get('action_name', f"Действие {action_id}")
            action_states[action_id] = {
                'name': action_name,
                'init_states': [],  # Состояния, которые ведут к действию
                'final_states': []  # Состояния, которые создаются действием
            }
        
        # Анализируем связи для определения init_states и final_states
        for conn in self.model_data.get('model_connections', []):
            conn_out = conn.get('connection_out', '')
            conn_in = conn.get('connection_in', '')
            
            # Определяем тип связи
            if conn_out.startswith('a'):  # Действие -> Состояние
                # conn_out - действие, conn_in - состояние
                action_id = conn_out
                
                # Извлекаем state_id из строки формата "o00000s00000"
                if conn_in and len(conn_in) >= 8:
                    # Формат: o00000s00000
                    if 's' in conn_in:
                        parts = conn_in.split('s')
                        if len(parts) == 2:
                            state_id = 's' + parts[1]
                            if state_id in state_map:
                                if action_id in action_states:
                                    action_states[action_id]['final_states'].append(state_map[state_id])
            
            elif conn_out.startswith('o'):  # Состояние -> Действие
                # conn_out - состояние, conn_in - действие
                if conn_in and conn_in.startswith('a'):
                    action_id = conn_in
                    
                    # Извлекаем state_id из conn_out
                    if 's' in conn_out:
                        parts = conn_out.split('s')
                        if len(parts) == 2:
                            state_id = 's' + parts[1]
                            if state_id in state_map:
                                if action_id in action_states:
                                    action_states[action_id]['init_states'].append(state_map[state_id])
        
        # Преобразуем в простой формат
        for action_id, states in action_states.items():
            action_name = states['name']
            simple_model[action_name] = {
                "init_states": list(set(states['init_states'])),  # Убираем дубли
                "final_states": list(set(states['final_states']))
            }
        
        return simple_model
    
    def generate_all_bdd_files(self):
        """
        Генерирует все BDD файлы используя адаптированный алгоритм
        
        Returns:
            dict {filename: content}
        """
        return self.bdd_generator.generate_all_bdd_files()
    
    def generate_bdd_for_action(self, action_name):
        """
        Генерирует BDD для конкретного действия
        
        Args:
            action_name: Название действия
            
        Returns:
            Строка с BDD сценарием
        """
        # Находим action_id по названию
        action_id = None
        for action in self.model_data.get('model_actions', []):
            if action.get('action_name') == action_name:
                action_id = action.get('action_id')
                break
        
        if not action_id:
            return f"# Ошибка: действие '{action_name}' не найдено\n"
        
        # Генерируем пути к действию
        prereq_paths = self.bdd_generator.get_ways_to_action(action_name)
        final_states = self.simple_model.get(action_name, {}).get('final_states', [])
        
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
        
        return txt_content
    
    def generate_all_tests(self):
        """
        Генерирует все тесты для всех действий
        
        Returns:
            dict {filename: content}
        """
        all_tests = {}
        
        for action_name in self.simple_model.keys():
            safe_name = "".join(c for c in action_name if c.isalnum() or c in " _-").rstrip()
            filename = f"bdd_{safe_name.replace(' ', '_')}.txt"
            
            test_content = self.generate_bdd_for_action(action_name)
            all_tests[filename] = test_content
            
            logger.info(f"Сгенерирован BDD для действия: {action_name}")
        
        return all_tests
    
    def generate_tests_for_actions(self, action_names):
        """
        Генерирует тесты только для указанных действий
        
        Args:
            action_names: Список названий действий
            
        Returns:
            dict {filename: content} для выбранных тестов
        """
        selected_tests = {}
        
        for action_name in action_names:
            if action_name in self.simple_model:
                safe_name = "".join(c for c in action_name if c.isalnum() or c in " _-").rstrip()
                filename = f"bdd_{safe_name.replace(' ', '_')}.txt"
                
                test_content = self.generate_bdd_for_action(action_name)
                selected_tests[filename] = test_content
                
                logger.info(f"Сгенерирован BDD для действия: {action_name}")
            else:
                logger.warning(f"Действие '{action_name}' не найдено в модели")
        
        return selected_tests


class TestGeneratorAdapted:
    """
    Полный адаптированный генератор тестов с поддержкой ZIP архивов
    """
    
    def __init__(self, model_data):
        self.model_data = model_data
        self.generator = BDDGeneratorAdapted(model_data)
    
    def generate_all(self):
        """Генерирует все тесты"""
        return self.generator.generate_all_tests()
    
    def generate_for_actions(self, action_names):
        """Генерирует тесты для указанных действий"""
        return self.generator.generate_tests_for_actions(action_names)
    
    def generate_for_action_ids(self, action_ids):
        """Генерирует тесты для указанных ID действий"""
        # Преобразуем action_ids в action_names
        action_names = []
        action_id_to_name = {}
        
        for action in self.model_data.get('model_actions', []):
            action_id = action.get('action_id')
            action_name = action.get('action_name')
            action_id_to_name[action_id] = action_name
        
        for action_id in action_ids:
            if action_id in action_id_to_name:
                action_names.append(action_id_to_name[action_id])
            else:
                logger.warning(f"Действие с ID '{action_id}' не найдено")
        
        return self.generate_for_actions(action_names)
    
    def create_zip_archive(self, tests_dict, archive_name=None):
        """Создает ZIP архив с тестами"""
        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"bdd_tests_{timestamp}.zip"
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in tests_dict.items():
                zipf.writestr(filename, content.encode('utf-8'))
            
            # Добавляем README
            readme_content = self._generate_readme(tests_dict)
            zipf.writestr("README.md", readme_content.encode('utf-8'))
        
        zip_buffer.seek(0)
        return zip_buffer, archive_name
    
    def _generate_readme(self, tests_dict):
        """Генерирует README файл для архива"""
        readme = f"# BDD тесты (адаптированный алгоритм)\n\n"
        readme += f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        readme += f"**Всего тестов:** {len(tests_dict)}\n\n"
        
        readme += "## Описание\n"
        readme += "Эти BDD тесты сгенерированы адаптированным алгоритмом из test_generator_bot.py\n"
        readme += "для структуры test_project.json\n\n"
        
        readme += "## Формат тестов\n"
        readme += "Каждый тест содержит:\n"
        readme += "- **Функциональность**: Название действия\n"
        readme += "- **Сценарии**: Все возможные пути выполнения действия\n"
        readme += "- **Когда**: Предусловия и шаги\n"
        readme += "- **Тогда**: Ожидаемые результаты\n\n"
        
        readme += "## Список тестов\n"
        for filename in sorted(tests_dict.keys()):
            readme += f"- `{filename}`\n"
        
        return readme


# Функции для интеграции
def load_model(filepath):
    """Загружает модель из файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки модели: {e}")
        return None


def generate_tests(model_data, action_ids=None):
    """
    Основная функция генерации тестов
    
    Args:
        model_data: Данные модели
        action_ids: Список ID действий (None для всех)
        
    Returns:
        (tests_dict, zip_buffer, archive_name)
    """
    try:
        generator = TestGeneratorAdapted(model_data)
        
        if action_ids is None:
            # Генерация всех тестов
            tests_dict = generator.generate_all()
        else:
            # Генерация тестов для выбранных действий
            tests_dict = generator.generate_for_action_ids(action_ids)
        
        # Создаем ZIP архив
        zip_buffer, archive_name = generator.create_zip_archive(tests_dict)
        
        return tests_dict, zip_buffer, archive_name
        
    except Exception as e:
        logger.error(f"Ошибка генерации тестов: {e}")
        return {}, None, None


# Тестирование
if __name__ == "__main__":
    print("Тестирование адаптированного генератора тестов...")
    
    # Загружаем тестовую модель
    model = load_model("test_project.json")
    
    if model:
        print(f"✓ Модель загружена: {len(model.get('model_actions', []))} действий")
        
        # Тест 1: Генерация всех тестов
        print("\n1. Генерация всех тестов...")
        tests_dict, zip_buffer, archive_name = generate_tests(model)
        
        if tests_dict:
            print(f"✓ Сгенерировано {len(tests_dict)} тестов")
            print(f"✓ Создан архив: {archive_name}")
            
            # Сохраняем архив для проверки
            with open(archive_name, 'wb') as f:
                f.write(zip_buffer.getvalue())
            print(f"✓ Архив сохранен на диск")
            
            # Показываем пример теста
            first_file = list(tests_dict.keys())[0]
            print(f"\nПример теста ({first_file}):")
            print("=" * 50)
            print(tests_dict[first_file][:500] + "...")
            print("=" * 50)
        
        # Тест 2: Генерация тестов для конкретных действий
        print("\n2. Генерация тестов для действий a00001 и a00002...")
        tests_dict2, zip_buffer2, archive_name2 = generate_tests(model, ["a00001", "a00002"])
        
        if tests_dict2:
            print(f"✓ Сгенерировано {len(tests_dict2)} тестов для выбранных действий")
            print(f"✓ Создан архив: {archive_name2}")
        
        print("\n✅ Адаптированный генератор тестов работает корректно!")
    else:
        print("❌ Не удалось загрузить модель test_project.json")