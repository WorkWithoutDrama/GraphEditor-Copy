#!/usr/bin/env python3
"""
Инкрементальный построитель модели из ТЗ
Читает ТЗ по предложениям, анализирует и строит модель в JSON
"""

import json
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

class IncrementalModelBuilder:
    def __init__(self, output_file: str = "incremental_model.json"):
        self.output_file = output_file
        self.model = {
            "model_actions": [],
            "model_objects": [],
            "model_connections": []
        }
        
        # Индексы для быстрого поиска
        self.action_ids = set()  # Все action_id
        self.object_ids = set()  # Все object_id
        self.state_combinations = set()  # Все комбинации object_id + state_id
        self.object_names_to_ids = {}  # Имя объекта -> object_id
        
        # Счетчики для генерации ID
        self.next_action_id = 1
        self.next_object_id = 1
        self.next_state_id = {}  # object_id -> следующий state_id
        
        # Загрузка существующей модели, если есть
        self.load_existing_model()

    def load_existing_model(self):
        """Загружает существующую модель из файла"""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                existing_model = json.load(f)
                
                # Восстанавливаем индексы из существующей модели
                if "model_actions" in existing_model:
                    self.model["model_actions"] = existing_model["model_actions"]
                    for action in existing_model["model_actions"]:
                        if "action_id" in action:
                            self.action_ids.add(action["action_id"])
                            # Извлекаем номер из action_id
                            match = re.match(r'a(\d+)', action["action_id"])
                            if match:
                                num = int(match.group(1))
                                if num >= self.next_action_id:
                                    self.next_action_id = num + 1
                
                if "model_objects" in existing_model:
                    self.model["model_objects"] = existing_model["model_objects"]
                    for obj in existing_model["model_objects"]:
                        if "object_id" in obj:
                            self.object_ids.add(obj["object_id"])
                            if "object_name" in obj:
                                self.object_names_to_ids[obj["object_name"]] = obj["object_id"]
                            
                            # Извлекаем номер из object_id
                            match = re.match(r'o(\d+)', obj["object_id"])
                            if match:
                                num = int(match.group(1))
                                if num >= self.next_object_id:
                                    self.next_object_id = num + 1
                            
                            # Восстанавливаем состояния
                            if "resource_state" in obj and isinstance(obj["resource_state"], list):
                                self.next_state_id[obj["object_id"]] = 1
                                for state in obj["resource_state"]:
                                    if "state_id" in state:
                                        self.state_combinations.add(f"{obj['object_id']}{state['state_id']}")
                                        # Извлекаем номер из state_id
                                        match = re.match(r's(\d+)', state["state_id"])
                                        if match:
                                            num = int(match.group(1))
                                            if num >= self.next_state_id.get(obj["object_id"], 1):
                                                self.next_state_id[obj["object_id"]] = num + 1
                
                if "model_connections" in existing_model:
                    self.model["model_connections"] = existing_model["model_connections"]
                    
                print(f"✅ Загружена существующая модель из {self.output_file}")
                print(f"   Действий: {len(self.model['model_actions'])}")
                print(f"   Объектов: {len(self.model['model_objects'])}")
                print(f"   Связей: {len(self.model['model_connections'])}")
                
        except FileNotFoundError:
            print(f"📝 Файл {self.output_file} не найден, начинаем с пустой модели")
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка чтения JSON: {e}, начинаем с пустой модели")

    def save_model(self):
        """Сохраняет модель в JSON файл"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.model, f, ensure_ascii=False, indent=2)
            print(f"💾 Модель сохранена в {self.output_file}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения модели: {e}")
            return False

    def generate_action_id(self) -> str:
        """Генерирует новый ID для действия"""
        action_id = f"a{self.next_action_id:05d}"
        self.next_action_id += 1
        return action_id

    def generate_object_id(self) -> str:
        """Генерирует новый ID для объекта"""
        object_id = f"o{self.next_object_id:05d}"
        self.next_object_id += 1
        return object_id

    def generate_state_id(self, object_id: str) -> str:
        """Генерирует новый ID для состояния объекта"""
        if object_id not in self.next_state_id:
            self.next_state_id[object_id] = 1
        state_id = f"s{self.next_state_id[object_id]:05d}"
        self.next_state_id[object_id] += 1
        return state_id

    def find_or_create_object(self, object_name: str) -> Tuple[str, Dict]:
        """Находит существующий объект или создает новый"""
        # Проверяем, есть ли уже такой объект
        if object_name in self.object_names_to_ids:
            object_id = self.object_names_to_ids[object_name]
            # Находим объект в модели
            for obj in self.model["model_objects"]:
                if obj["object_id"] == object_id:
                    return object_id, obj
        
        # Создаем новый объект
        object_id = self.generate_object_id()
        new_object = {
            "object_id": object_id,
            "object_name": object_name,
            "resource_state": []
        }
        
        self.model["model_objects"].append(new_object)
        self.object_ids.add(object_id)
        self.object_names_to_ids[object_name] = object_id
        self.next_state_id[object_id] = 1
        
        print(f"➕ Создан новый объект: {object_name} ({object_id})")
        return object_id, new_object

    def find_or_create_state(self, object_id: str, object_name: str, state_name: str) -> str:
        """Находит существующее состояние или создает новое"""
        # Находим объект
        for obj in self.model["model_objects"]:
            if obj["object_id"] == object_id:
                # Проверяем, есть ли уже такое состояние
                for state in obj["resource_state"]:
                    if state["state_name"] == state_name:
                        state_id = state["state_id"]
                        combined_id = f"{object_id}{state_id}"
                        self.state_combinations.add(combined_id)
                        return state_id
                
                # Создаем новое состояние
                state_id = self.generate_state_id(object_id)
                new_state = {
                    "state_id": state_id,
                    "state_name": state_name
                }
                obj["resource_state"].append(new_state)
                
                combined_id = f"{object_id}{state_id}"
                self.state_combinations.add(combined_id)
                
                print(f"   ➕ Добавлено состояние для {object_name}: {state_name} ({state_id})")
                return state_id
        
        # Если объект не найден (не должно происходить)
        print(f"⚠️ Объект {object_id} не найден при создании состояния")
        return ""

    def find_or_create_action(self, action_name: str) -> Tuple[str, Dict]:
        """Находит существующее действие или создает новое"""
        # Проверяем, есть ли уже такое действие
        for action in self.model["model_actions"]:
            if action["action_name"] == action_name:
                return action["action_id"], action
        
        # Создаем новое действие
        action_id = self.generate_action_id()
        new_action = {
            "action_id": action_id,
            "action_name": action_name,
            "action_links": {
                "manual": "",
                "API": "",
                "UI": ""
            }
        }
        
        self.model["model_actions"].append(new_action)
        self.action_ids.add(action_id)
        
        print(f"➕ Создано новое действие: {action_name} ({action_id})")
        return action_id, new_action

    def add_connection(self, connection_out: str, connection_in: str):
        """Добавляет связь в модель, если ее еще нет"""
        # Проверяем, нет ли уже такой связи
        for conn in self.model["model_connections"]:
            if conn["connection_out"] == connection_out and conn["connection_in"] == connection_in:
                return False
        
        # Добавляем новую связь
        new_connection = {
            "connection_out": connection_out,
            "connection_in": connection_in
        }
        self.model["model_connections"].append(new_connection)
        print(f"   🔗 Добавлена связь: {connection_out} → {connection_in}")
        return True

    def analyze_sentence(self, sentence: str):
        """Анализирует одно предложение из ТЗ"""
        print(f"\n📝 Анализ предложения: {sentence}")
        
        # Паттерны для поиска действий
        action_patterns = [
            (r"Регистрация(?: по email/паролю)?", "Регистрация пользователя"),
            (r"Авторизация", "Авторизация пользователя"),
            (r"восстановление пароля", "Восстановление пароля"),
            (r"вход через социальные сети", "Вход через социальные сети"),
            (r"Настройка Профиля", "Настройка профиля пользователя"),
            (r"Ввод личных данных", "Ввод личных данных"),
            (r"Расчет базовой нормы калорий", "Расчет нормы калорий"),
            (r"Отображение недельного календаря", "Отображение календаря"),
            (r"добавления/удаления/редактирования приемов пищи", "Управление приемами пищи"),
            (r"Поиск и добавление блюд/продуктов", "Поиск и добавление продуктов"),
            (r"Отображение суммарного потребления калорий", "Отображение статистики"),
            (r"Функция \"Сгенерировать план\"", "Генерация плана питания"),
            (r"Поиск по названию, ингредиентам", "Поиск рецептов"),
            (r"добавления собственных рецептов", "Добавление рецептов"),
            (r"Просмотр подробной информации о блюде", "Просмотр информации о блюде"),
            (r"Автоматическая генерация списка покупок", "Генерация списка покупок"),
            (r"ручного редактирования списка", "Редактирование списка покупок"),
            (r"Разработка RESTful API", "Разработка API"),
            (r"управления пользователями", "Управление пользователями"),
            (r"управления планами питания", "Управление планами питания"),
            (r"работы с базой рецептов", "Управление рецептами"),
            (r"Хранение данных пользователей", "Хранение данных"),
            (r"Алгоритм расчета суточной нормы", "Расчет нормы питания")
        ]
        
        # Паттерны для поиска объектов
        object_patterns = [
            (r"пользовател[ьяей]", "Пользователь"),
            (r"профил[ьяей]", "Профиль"),
            (r"данн[ыеых]", "Данные"),
            (r"email", "Email"),
            (r"парол[ьяей]", "Пароль"),
            (r"календар[ьяей]", "Календарь"),
            (r"прием[аов] пищи", "Прием пищи"),
            (r"блюд[ао]", "Блюдо"),
            (r"продукт[аов]", "Продукт"),
            (r"калори[йи]", "Калории"),
            (r"БЖУ", "БЖУ"),
            (r"план[аов] питани[я]", "План питания"),
            (r"рецепт[аов]", "Рецепт"),
            (r"ингредиент[аов]", "Ингредиент"),
            (r"список[аов] покупок", "Список покупок"),
            (r"API", "API"),
            (r"баз[аы] данн[ых]", "База данных"),
            (r"систем[аы]", "Система")
        ]
        
        found_actions = []
        found_objects = []
        
        # Ищем действия
        for pattern, action_name in action_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                found_actions.append(action_name)
        
        # Ищем объекты
        for pattern, object_name in object_patterns:
            if re.search(pattern, sentence, re.IGNORECASE):
                found_objects.append(object_name)
        
        # Если нашли действия, обрабатываем их
        if found_actions:
            for action_name in found_actions:
                action_id, action = self.find_or_create_action(action_name)
                
                # Для каждого действия определяем начальные и конечные условия
                # Это упрощенная логика - в реальности нужно более сложное определение
                
                if "регистрация" in action_name.lower():
                    # Регистрация: пользователь незарегистрирован -> зарегистрирован
                    user_id, user_obj = self.find_or_create_object("Пользователь")
                    start_state_id = self.find_or_create_state(user_id, "Пользователь", "незарегистрирован")
                    end_state_id = self.find_or_create_state(user_id, "Пользователь", "зарегистрирован")
                    
                    # Добавляем связи
                    self.add_connection(f"{user_id}{start_state_id}", action_id)
                    self.add_connection(action_id, f"{user_id}{end_state_id}")
                    
                    # Также может потребоваться email и пароль
                    email_id, email_obj = self.find_or_create_object("Email")
                    email_start_state = self.find_or_create_state(email_id, "Email", "не подтвержден")
                    email_end_state = self.find_or_create_state(email_id, "Email", "подтвержден")
                    
                    self.add_connection(f"{email_id}{email_start_state}", action_id)
                    self.add_connection(action_id, f"{email_id}{email_end_state}")
                    
                elif "авторизация" in action_name.lower():
                    # Авторизация: пользователь неавторизован -> авторизован
                    user_id, user_obj = self.find_or_create_object("Пользователь")
                    # Проверяем, есть ли состояние "зарегистрирован"
                    registered_state = None
                    for state in user_obj["resource_state"]:
                        if state["state_name"] == "зарегистрирован":
                            registered_state = state["state_id"]
                            break
                    
                    if not registered_state:
                        registered_state = self.find_or_create_state(user_id, "Пользователь", "зарегистрирован")
                    
                    auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
                    
                    self.add_connection(f"{user_id}{registered_state}", action_id)
                    self.add_connection(action_id, f"{user_id}{auth_state}")
                    
                elif "настройка профиля" in action_name.lower():
                    # Настройка профиля: профиль не настроен -> настроен
                    profile_id, profile_obj = self.find_or_create_object("Профиль")
                    start_state = self.find_or_create_state(profile_id, "Профиль", "не настроен")
                    end_state = self.find_or_create_state(profile_id, "Профиль", "настроен")
                    
                    # Пользователь должен быть авторизован
                    user_id, user_obj = self.find_or_create_object("Пользователь")
                    auth_state = None
                    for state in user_obj["resource_state"]:
                        if state["state_name"] == "авторизован":
                            auth_state = state["state_id"]
                            break
                    
                    if not auth_state:
                        auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
                    
                    self.add_connection(f"{user_id}{auth_state}", action_id)
                    self.add_connection(f"{profile_id}{start_state}", action_id)
                    self.add_connection(action_id, f"{profile_id}{end_state}")
        
        return len(found_actions) > 0 or len(found_objects) > 0

    def analyze_tz_file(self, tz_file: str):
        """Анализирует весь файл ТЗ"""
        print(f"📖 Начинаю анализ ТЗ из файла: {tz_file}")
        
        try:
            with open(tz_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разбиваем на предложения (упрощенная версия)
            sentences = re.split(r'[.!?]+', content)
            
            total_sentences = len(sentences)
            processed_count = 0
            
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if len(sentence) > 10:  # Игнорируем очень короткие "предложения"
                    print(f"\n[{i+1}/{total_sentences}] ", end="")
                    if self.analyze_sentence(sentence):
                        processed_count += 1
                        # Периодически сохраняем модель
                        if processed_count % 5 == 0:
                            self.save_model()
            
            # Финальное сохранение
            self.save_model()
            
            print(f"\n✅ Анализ завершен!")
            print(f"   Обработано предложений: {processed_count}")
            print(f"   Всего действий в модели: {len(self.model['model_actions'])}")
            print(f"   Всего объектов в модели: {len(self.model['model_objects'])}")
            print(f"   Всего связей в модели: {len(self.model['model_connections'])}")
            
        except FileNotFoundError:
            print(f"❌ Файл {tz_file} не найден")
        except Exception as e:
            print(f"❌ Ошибка при анализе файла: {e}")

    def print_summary(self):
        """Выводит сводку по текущей модели"""
        print("\n" + "="*60)
        print("📊 СВОДКА ТЕКУЩЕЙ МОДЕЛИ")
        print("="*60)
        
        print(f"\n📋 Действия ({len(self.model['model_actions'])}):")
        for action in self.model['model_actions']:
            print(f"  • {action['action_name']} ({action['action_id']})")
        
        print(f"\n🏛️ Объекты ({len(self.model['model_objects'])}):")
        for obj in self.model['model_objects']:
            states = ", ".join([f"{s['state_name']} ({s['state_id']})" for s in obj['resource_state']])
            print(f"  • {obj['object_name']} ({obj['object_id']}): {states}")
        
        print(f"\n🔗 Связи ({len(self.model['model_connections'])}):")
        for conn in self.model['model_connections']:
            print(f"  • {conn['connection_out']} → {conn['connection_in']}")
        
        print("\n" + "="*60)

def main():
    """Основная функция"""
    builder = IncrementalModelBuilder("mindful_meals_model.json")
    
    # Анализируем ТЗ
    builder.analyze_tz_file("exam.txt")
    
    # Выводим сводку
    builder.print_summary()
    
    print(f"\n🎯 Модель сохранена в файле: mindful_meals_model.json")
    print("💡 Для визуализации графа используйте инструменты Graphviz или аналогичные")

if __name__ == "__main__":
    main()