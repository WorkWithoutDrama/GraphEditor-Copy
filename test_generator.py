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

class TestGenerator:
    """
    Генератор E2E тестов для структуры test_project.json
    """
    
    def __init__(self, model_data):
        """
        Инициализация генератора тестов
        
        Args:
            model_data: Данные модели в формате test_project.json
        """
        self.model = model_data
        
        # Создаем структуры для быстрого доступа
        self.actions = {}
        self.objects = {}
        self.connections = []
        self.state_map = {}  # Карта состояний: state_id -> {object_name, state_name}
        
        self._parse_model()
        logger.info(f"Инициализирован генератор тестов: {len(self.actions)} действий, {len(self.objects)} объектов")
    
    def _parse_model(self):
        """Разбирает структуру модели"""
        # Парсим действия
        for action in self.model.get('model_actions', []):
            action_id = action.get('action_id')
            self.actions[action_id] = {
                'id': action_id,
                'name': action.get('action_name', ''),
                'links': action.get('action_links', {})
            }
        
        # Парсим объекты и состояния
        for obj in self.model.get('model_objects', []):
            object_id = obj.get('object_id')
            object_name = obj.get('object_name', '')
            self.objects[object_id] = {
                'id': object_id,
                'name': object_name,
                'states': {}
            }
            
            # Добавляем состояния в карту
            for state in obj.get('resource_state', []):
                state_id = state.get('state_id')
                state_name = state.get('state_name', '')
                self.state_map[state_id] = {
                    'object_id': object_id,
                    'object_name': object_name,
                    'state_name': state_name
                }
                self.objects[object_id]['states'][state_id] = state_name
        
        # Парсим связи
        self.connections = self.model.get('model_connections', [])
        
        # Строим граф зависимостей
        self._build_dependency_graph()
    
    def _build_dependency_graph(self):
        """Строит граф зависимостей между действиями и состояниями"""
        self.dependency_graph = {
            'action_to_states': {},  # Действие -> состояния
            'state_to_actions': {},  # Состояние -> действия
            'preconditions': {},     # Предусловия для действий
        }
        
        # Анализируем связи для построения графа
        for conn in self.connections:
            conn_out = conn.get('connection_out', '')
            conn_in = conn.get('connection_in', '')
            
            # Определяем тип connection_out (действие или состояние)
            if conn_out.startswith('a'):  # Это действие
                # connection_in должно быть состоянием (формат: object_id + state_id)
                if conn_in and len(conn_in) >= 8:  # Минимальная длина для o00000s00000
                    state_id = conn_in[6:]  # Извлекаем state_id из строки
                    if state_id in self.state_map:
                        if conn_out not in self.dependency_graph['action_to_states']:
                            self.dependency_graph['action_to_states'][conn_out] = []
                        self.dependency_graph['action_to_states'][conn_out].append(state_id)
                        
                        if state_id not in self.dependency_graph['state_to_actions']:
                            self.dependency_graph['state_to_actions'][state_id] = []
                        self.dependency_graph['state_to_actions'][state_id].append(conn_out)
            
            elif conn_out.startswith('o'):  # Это состояние
                # Ищем state_id в строке
                if 's' in conn_out:
                    parts = conn_out.split('s')
                    if len(parts) == 2:
                        state_id = 's' + parts[1]
                        if state_id in self.state_map:
                            # connection_in должно быть действием
                            if conn_in and conn_in.startswith('a'):
                                if state_id not in self.dependency_graph['state_to_actions']:
                                    self.dependency_graph['state_to_actions'][state_id] = []
                                self.dependency_graph['state_to_actions'][state_id].append(conn_in)
                                
                                if conn_in not in self.dependency_graph['preconditions']:
                                    self.dependency_graph['preconditions'][conn_in] = []
                                self.dependency_graph['preconditions'][conn_in].append(state_id)
    
    def _get_state_description(self, state_id):
        """Получает полное описание состояния"""
        if state_id in self.state_map:
            state_info = self.state_map[state_id]
            return f"{state_info['object_name']} {state_info['state_name']}"
        return f"Состояние {state_id}"
    
    def _get_action_description(self, action_id):
        """Получает полное описание действия"""
        if action_id in self.actions:
            return self.actions[action_id]['name']
        return f"Действие {action_id}"
    
    def _find_paths_to_action(self, action_id, visited=None):
        """
        Находит все пути (цепочки действий) для достижения указанного действия
        
        Args:
            action_id: ID действия
            visited: Множество посещенных действий (для предотвращения циклов)
            
        Returns:
            Список путей (каждый путь - список ID действий)
        """
        if visited is None:
            visited = set()
        
        # Если действие уже посещено, возвращаем пустой список (избегаем циклов)
        if action_id in visited:
            return []
        
        visited.add(action_id)
        
        # Получаем предусловия для действия
        preconditions = self.dependency_graph.get('preconditions', {}).get(action_id, [])
        
        # Если нет предусловий, путь состоит только из этого действия
        if not preconditions:
            visited.remove(action_id)
            return [[action_id]]
        
        # Для каждого предусловия находим пути
        all_paths = []
        for state_id in preconditions:
            # Находим действия, которые приводят к этому состоянию
            leading_actions = self.dependency_graph.get('state_to_actions', {}).get(state_id, [])
            
            for leading_action in leading_actions:
                # Рекурсивно находим пути к leading_action
                sub_paths = self._find_paths_to_action(leading_action, visited.copy())
                
                # Добавляем текущее действие в конец каждого подпути
                for path in sub_paths:
                    if action_id not in path:  # Избегаем дублирования
                        new_path = path + [action_id]
                        all_paths.append(new_path)
        
        visited.remove(action_id)
        
        # Если не нашли путей, возвращаем путь только с текущим действием
        if not all_paths:
            return [[action_id]]
        
        return all_paths
    
    def generate_test_for_action(self, action_id):
        """
        Генерирует E2E тест для конкретного действия
        
        Args:
            action_id: ID действия
            
        Returns:
            Строка с тестом в формате BDD
        """
        if action_id not in self.actions:
            return f"# Ошибка: действие {action_id} не найдено в модели\n"
        
        action_name = self.actions[action_id]['name']
        
        # Находим все пути к действию
        paths = self._find_paths_to_action(action_id)
        
        # Генерируем тест
        test_content = f"# E2E тест: {action_name}\n"
        test_content += f"# Действие ID: {action_id}\n"
        test_content += f"# Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Определяем ожидаемые состояния после выполнения действия
        resulting_states = []
        if action_id in self.dependency_graph.get('action_to_states', {}):
            for state_id in self.dependency_graph['action_to_states'][action_id]:
                resulting_states.append(self._get_state_description(state_id))
        
        # Генерируем сценарии для каждого пути
        for i, path in enumerate(paths):
            scenario_num = i + 1
            
            test_content += f"## Сценарий {scenario_num}\n\n"
            test_content += f"**Предусловия:**\n"
            
            # Описываем цепочку действий
            for j, prev_action_id in enumerate(path[:-1]):
                prev_action_name = self._get_action_description(prev_action_id)
                test_content += f"{j+1}. {prev_action_name}\n"
            
            test_content += f"\n**Шаги теста:**\n"
            
            # Выполняем цепочку действий
            for j, action_in_path in enumerate(path):
                action_desc = self._get_action_description(action_in_path)
                test_content += f"{j+1}. {action_desc}\n"
            
            test_content += f"\n**Ожидаемый результат:**\n"
            
            if resulting_states:
                for state_desc in resulting_states:
                    test_content += f"- {state_desc}\n"
            else:
                test_content += f"- Действие '{action_name}' выполнено успешно\n"
            
            test_content += f"\n**Проверки:**\n"
            test_content += f"1. Убедиться, что все предусловия выполнены\n"
            test_content += f"2. Выполнить действие '{action_name}'\n"
            
            if resulting_states:
                for k, state_desc in enumerate(resulting_states):
                    test_content += f"{k+3}. Проверить, что {state_desc}\n"
            
            test_content += "\n---\n\n"
        
        return test_content
    
    def generate_all_tests(self):
        """
        Генерирует все E2E тесты для всех действий в модели
        
        Returns:
            Словарь {filename: content} для всех тестов
        """
        all_tests = {}
        
        for action_id in self.actions:
            action_name = self.actions[action_id]['name']
            safe_name = "".join(c for c in action_name if c.isalnum() or c in " _-").rstrip()
            filename = f"e2e_test_{action_id}_{safe_name.replace(' ', '_')}.md"
            
            test_content = self.generate_test_for_action(action_id)
            all_tests[filename] = test_content
            
            logger.info(f"Сгенерирован тест для действия: {action_name} ({action_id})")
        
        return all_tests
    
    def generate_tests_for_actions(self, action_ids):
        """
        Генерирует тесты только для указанных действий
        
        Args:
            action_ids: Список ID действий
            
        Returns:
            Словарь {filename: content} для выбранных тестов
        """
        selected_tests = {}
        
        for action_id in action_ids:
            if action_id in self.actions:
                action_name = self.actions[action_id]['name']
                safe_name = "".join(c for c in action_name if c.isalnum() or c in " _-").rstrip()
                filename = f"e2e_test_{action_id}_{safe_name.replace(' ', '_')}.md"
                
                test_content = self.generate_test_for_action(action_id)
                selected_tests[filename] = test_content
                
                logger.info(f"Сгенерирован тест для действия: {action_name} ({action_id})")
            else:
                logger.warning(f"Действие {action_id} не найдено в модели")
        
        return selected_tests
    
    def create_zip_archive(self, tests_dict, archive_name=None):
        """
        Создает ZIP архив с тестами
        
        Args:
            tests_dict: Словарь {filename: content}
            archive_name: Имя ZIP файла (опционально)
            
        Returns:
            BytesIO объект с ZIP архивом
        """
        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"e2e_tests_{timestamp}.zip"
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in tests_dict.items():
                zipf.writestr(filename, content.encode('utf-8'))
        
        zip_buffer.seek(0)
        return zip_buffer, archive_name
    
    def generate_summary_report(self, tests_dict):
        """
        Генерирует сводный отчет о тестах
        
        Args:
            tests_dict: Словарь с тестами
            
        Returns:
            Строка с отчетом
        """
        total_tests = len(tests_dict)
        total_actions = len(self.actions)
        
        report = f"# Сводный отчет о тестах\n\n"
        report += f"**Дата генерации:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**Всего действий в модели:** {total_actions}\n"
        report += f"**Сгенерировано тестов:** {total_tests}\n\n"
        
        report += "## Список тестов:\n\n"
        
        for filename in sorted(tests_dict.keys()):
            # Извлекаем ID действия из имени файла
            parts = filename.split('_')
            if len(parts) >= 3:
                action_id = parts[2]
                if action_id in self.actions:
                    action_name = self.actions[action_id]['name']
                    report += f"- **{action_name}** (`{action_id}`) → `{filename}`\n"
        
        report += f"\n## Статистика модели:\n"
        report += f"- Действий: {len(self.actions)}\n"
        report += f"- Объектов: {len(self.objects)}\n"
        report += f"- Состояний: {len(self.state_map)}\n"
        report += f"- Связей: {len(self.connections)}\n"
        
        return report


# Функции для интеграции с API
def load_model_from_file(filepath):
    """Загружает модель из JSON файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки модели из {filepath}: {e}")
        return None


def generate_tests_from_model(model_data, action_ids=None):
    """
    Основная функция для генерации тестов
    
    Args:
        model_data: Данные модели
        action_ids: Список ID действий (None для всех)
        
    Returns:
        (tests_dict, zip_buffer, archive_name, summary)
    """
    try:
        generator = TestGenerator(model_data)
        
        if action_ids is None:
            # Генерация всех тестов
            tests_dict = generator.generate_all_tests()
        else:
            # Генерация тестов для выбранных действий
            tests_dict = generator.generate_tests_for_actions(action_ids)
        
        # Добавляем сводный отчет
        summary = generator.generate_summary_report(tests_dict)
        tests_dict["SUMMARY.md"] = summary
        
        # Создаем ZIP архив
        zip_buffer, archive_name = generator.create_zip_archive(tests_dict)
        
        return tests_dict, zip_buffer, archive_name, summary
        
    except Exception as e:
        logger.error(f"Ошибка генерации тестов: {e}")
        return {}, None, None, f"Ошибка генерации тестов: {str(e)}"


# Пример использования
if __name__ == "__main__":
    # Загрузка тестовой модели
    model = load_model_from_file("test_project.json")
    
    if model:
        # Генерация всех тестов
        tests_dict, zip_buffer, archive_name, summary = generate_tests_from_model(model)
        
        print(f"Сгенерировано {len(tests_dict)} файлов")
        print(f"Имя архива: {archive_name}")
        print("\nСводный отчет:")
        print(summary)
        
        # Сохранение архива на диск (для тестирования)
        with open(archive_name, 'wb') as f:
            f.write(zip_buffer.getvalue())
        print(f"\nАрхив сохранен как {archive_name}")
        
        # Пример генерации тестов для конкретных действий
        selected_actions = ["a00001", "a00002"]
        tests_dict2, zip_buffer2, archive_name2, summary2 = generate_tests_from_model(model, selected_actions)
        print(f"\nСгенерировано {len(tests_dict2)} тестов для выбранных действий")