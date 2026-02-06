#!/usr/bin/env python3
"""
Анализатор ТЗ по абзацам
Создает корректную модель с правильными действиями и объектами
"""

import json
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

class ParagraphAnalyzer:
    def __init__(self, output_file: str = "correct_model.json"):
        self.output_file = output_file
        self.model = {
            "model_actions": [],
            "model_objects": [],
            "model_connections": []
        }
        
        # Индексы
        self.action_ids = set()
        self.object_ids = set()
        self.state_combinations = set()
        self.object_names_to_ids = {}
        
        # Счетчики
        self.next_action_id = 1
        self.next_object_id = 1
        self.next_state_id = {}
        
        # Правила для определения действий
        self.action_patterns = {
            "разработка": ["разработка", "создание", "проектирование"],
            "регистрация": ["регистрация", "создание аккаунта"],
            "авторизация": ["авторизация", "вход", "логин"],
            "настройка": ["настройка", "конфигурация"],
            "ввод данных": ["ввод", "заполнение", "указание"],
            "расчет": ["расчет", "вычисление", "подсчет"],
            "планирование": ["планирование", "составление плана"],
            "поиск": ["поиск", "найти"],
            "добавление": ["добавление", "внесение"],
            "просмотр": ["просмотр", "отображение"],
            "генерация": ["генерация", "формирование", "создание"],
            "редактирование": ["редактирование", "изменение"]
        }

    def generate_id(self, prefix: str, number: int) -> str:
        """Генерирует ID с префиксом"""
        return f"{prefix}{number:05d}"

    def find_or_create_object(self, object_name: str) -> Tuple[str, Dict]:
        """Находит или создает объект (без дубликатов)"""
        if object_name in self.object_names_to_ids:
            object_id = self.object_names_to_ids[object_name]
            for obj in self.model["model_objects"]:
                if obj["object_id"] == object_id:
                    return object_id, obj
        
        # Создаем новый объект
        object_id = self.generate_id("o", self.next_object_id)
        self.next_object_id += 1
        
        new_object = {
            "object_id": object_id,
            "object_name": object_name,
            "resource_state": [],
            "object_links": {
                "manual": f"документация по {object_name.lower()}",
                "API": f"/api/{object_name.lower().replace(' ', '-')}",
                "UI": f"/{object_name.lower().replace(' ', '-')}"
            }
        }
        
        self.model["model_objects"].append(new_object)
        self.object_ids.add(object_id)
        self.object_names_to_ids[object_name] = object_id
        self.next_state_id[object_id] = 1
        
        print(f"➕ Объект: {object_name} ({object_id})")
        return object_id, new_object

    def find_or_create_state(self, object_id: str, object_name: str, state_name: str) -> str:
        """Находит или создает состояние объекта"""
        for obj in self.model["model_objects"]:
            if obj["object_id"] == object_id:
                # Ищем существующее состояние
                for state in obj["resource_state"]:
                    if state["state_name"] == state_name:
                        return state["state_id"]
                
                # Создаем новое состояние
                state_id = self.generate_id("s", self.next_state_id[object_id])
                self.next_state_id[object_id] += 1
                
                new_state = {
                    "state_id": state_id,
                    "state_name": state_name
                }
                obj["resource_state"].append(new_state)
                
                combined_id = f"{object_id}{state_id}"
                self.state_combinations.add(combined_id)
                
                return state_id
        
        return ""

    def find_or_create_action(self, action_name: str) -> Tuple[str, Dict]:
        """Находит или создает действие (с проверкой полноты)"""
        # Проверяем, является ли действие полным (кто? что делает?)
        if len(action_name.split()) < 2:
            # Пытаемся дополнить действие
            for pattern, variations in self.action_patterns.items():
                for variation in variations:
                    if variation in action_name.lower():
                        # Нашли базовое действие, дополняем его
                        if "пользователь" not in action_name.lower():
                            action_name = f"{action_name} пользователя"
                        break
        
        # Проверяем существование
        for action in self.model["model_actions"]:
            if action["action_name"] == action_name:
                return action["action_id"], action
        
        # Создаем новое действие
        action_id = self.generate_id("a", self.next_action_id)
        self.next_action_id += 1
        
        new_action = {
            "action_id": action_id,
            "action_name": action_name,
            "action_links": {
                "manual": f"инструкция по {action_name.lower()}",
                "API": f"/api/{action_name.lower().replace(' ', '-')}",
                "UI": f"/{action_name.lower().replace(' ', '-')}"
            }
        }
        
        self.model["model_actions"].append(new_action)
        self.action_ids.add(action_id)
        
        print(f"➕ Действие: {action_name} ({action_id})")
        return action_id, new_action

    def add_connection(self, connection_out: str, connection_in: str):
        """Добавляет уникальную связь"""
        # Проверяем на дубликаты
        for conn in self.model["model_connections"]:
            if conn["connection_out"] == connection_out and conn["connection_in"] == connection_in:
                return
        
        new_connection = {
            "connection_out": connection_out,
            "connection_in": connection_in
        }
        self.model["model_connections"].append(new_connection)
        print(f"   🔗 Связь: {connection_out} → {connection_in}")

    def analyze_paragraph(self, paragraph: str):
        """Анализирует один абзац ТЗ"""
        paragraph = paragraph.strip()
        if not paragraph or len(paragraph) < 20:
            return
        
        print(f"\n📄 Анализ абзаца: {paragraph[:100]}...")
        
        # Определяем тип абзаца
        if re.search(r'регистрация.*авторизация|вход.*систем', paragraph, re.IGNORECASE):
            self.process_auth_paragraph(paragraph)
        elif re.search(r'профил[ья]|данные.*личные', paragraph, re.IGNORECASE):
            self.process_profile_paragraph(paragraph)
        elif re.search(r'план[аирование]*.*питани[яе]|календар[ья]', paragraph, re.IGNORECASE):
            self.process_meal_plan_paragraph(paragraph)
        elif re.search(r'рецепт[аыо]|продукт[аы]|ингредиент', paragraph, re.IGNORECASE):
            self.process_recipes_paragraph(paragraph)
        elif re.search(r'список.*покупок|покуп[киа]', paragraph, re.IGNORECASE):
            self.process_shopping_paragraph(paragraph)
        elif re.search(r'API|эндпоинт|сервер', paragraph, re.IGNORECASE):
            self.process_api_paragraph(paragraph)
        elif re.search(r'баз[аы].*данн|хранилище', paragraph, re.IGNORECASE):
            self.process_database_paragraph(paragraph)
        else:
            self.process_general_paragraph(paragraph)

    def process_auth_paragraph(self, paragraph: str):
        """Обрабатывает абзац про регистрацию/авторизацию"""
        # Регистрация пользователя
        reg_action_id, _ = self.find_or_create_action("Регистрация пользователя")
        user_id, user_obj = self.find_or_create_object("Пользователь")
        
        # Состояния для регистрации
        start_state = self.find_or_create_state(user_id, "Пользователь", "незарегистрирован")
        email_id, email_obj = self.find_or_create_object("Email")
        email_start = self.find_or_create_state(email_id, "Email", "не подтвержден")
        pass_id, pass_obj = self.find_or_create_object("Пароль")
        pass_start = self.find_or_create_state(pass_id, "Пароль", "не установлен")
        
        end_state = self.find_or_create_state(user_id, "Пользователь", "зарегистрирован")
        email_end = self.find_or_create_state(email_id, "Email", "подтвержден")
        pass_end = self.find_or_create_state(pass_id, "Пароль", "установлен")
        
        # Связи для регистрации
        self.add_connection(f"{user_id}{start_state}", reg_action_id)
        self.add_connection(f"{email_id}{email_start}", reg_action_id)
        self.add_connection(f"{pass_id}{pass_start}", reg_action_id)
        self.add_connection(reg_action_id, f"{user_id}{end_state}")
        self.add_connection(reg_action_id, f"{email_id}{email_end}")
        self.add_connection(reg_action_id, f"{pass_id}{pass_end}")
        
        # Авторизация пользователя
        auth_action_id, _ = self.find_or_create_action("Авторизация пользователя")
        session_id, session_obj = self.find_or_create_object("Сессия")
        session_start = self.find_or_create_state(session_id, "Сессия", "не активна")
        session_end = self.find_or_create_state(session_id, "Сессия", "активна")
        auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
        
        self.add_connection(f"{user_id}{end_state}", auth_action_id)
        self.add_connection(f"{session_id}{session_start}", auth_action_id)
        self.add_connection(auth_action_id, f"{user_id}{auth_state}")
        self.add_connection(auth_action_id, f"{session_id}{session_end}")
        
        # Восстановление пароля
        if re.search(r'восстановлени[ея]|забыл.*пароль', paragraph, re.IGNORECASE):
            recover_id, _ = self.find_or_create_action("Восстановление пароля")
            self.add_connection(f"{user_id}{end_state}", recover_id)
            new_pass_state = self.find_or_create_state(pass_id, "Пароль", "сброшен")
            self.add_connection(recover_id, f"{pass_id}{new_pass_state}")

    def process_profile_paragraph(self, paragraph: str):
        """Обрабатывает абзац про настройку профиля"""
        profile_action_id, _ = self.find_or_create_action("Настройка профиля")
        profile_id, profile_obj = self.find_or_create_object("Профиль")
        user_id, _ = self.find_or_create_object("Пользователь")
        
        # Пользователь должен быть авторизован
        auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
        
        # Состояния профиля
        profile_start = self.find_or_create_state(profile_id, "Профиль", "не настроен")
        profile_end = self.find_or_create_state(profile_id, "Профиль", "настроен")
        
        self.add_connection(f"{user_id}{auth_state}", profile_action_id)
        self.add_connection(f"{profile_id}{profile_start}", profile_action_id)
        self.add_connection(profile_action_id, f"{profile_id}{profile_end}")
        
        # Ввод личных данных
        if re.search(r'пол.*возраст.*рост.*вес', paragraph, re.IGNORECASE):
            data_action_id, _ = self.find_or_create_action("Ввод личных данных")
            data_id, data_obj = self.find_or_create_object("Данные")
            data_start = self.find_or_create_state(data_id, "Данные", "не заполнены")
            data_end = self.find_or_create_state(data_id, "Данные", "заполнены")
            
            self.add_connection(f"{profile_id}{profile_start}", data_action_id)
            self.add_connection(data_action_id, f"{data_id}{data_end}")
        
        # Расчет нормы калорий
        if re.search(r'расчет.*калори|норм[аы].*БЖУ', paragraph, re.IGNORECASE):
            calc_action_id, _ = self.find_or_create_action("Расчет нормы калорий")
            calc_id, calc_obj = self.find_or_create_object("Расчет")
            calc_start = self.find_or_create_state(calc_id, "Расчет", "не выполнен")
            calc_end = self.find_or_create_state(calc_id, "Расчет", "выполнен")
            
            self.add_connection(f"{profile_id}{profile_end}", calc_action_id)
            self.add_connection(calc_action_id, f"{calc_id}{calc_end}")

    def process_meal_plan_paragraph(self, paragraph: str):
        """Обрабатывает абзац про планирование питания"""
        # Основные объекты
        plan_id, plan_obj = self.find_or_create_object("План питания")
        calendar_id, calendar_obj = self.find_or_create_object("Календарь")
        meal_id, meal_obj = self.find_or_create_object("Прием пищи")
        
        # Действия
        if re.search(r'отображени[ея].*календар', paragraph, re.IGNORECASE):
            show_action_id, _ = self.find_or_create_action("Отображение календаря")
            calendar_state = self.find_or_create_state(calendar_id, "Календарь", "отображен")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            self.add_connection(f"{user_id}{auth_state}", show_action_id)
            self.add_connection(show_action_id, f"{calendar_id}{calendar_state}")
        
        if re.search(r'добавлени[ея].*удалени[ея].*редактировани[ея]', paragraph, re.IGNORECASE):
            manage_action_id, _ = self.find_or_create_action("Управление приемами пищи")
            meal_state = self.find_or_create_state(meal_id, "Прием пищи", "добавлен")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            self.add_connection(f"{user_id}{auth_state}", manage_action_id)
            self.add_connection(manage_action_id, f"{meal_id}{meal_state}")
        
        if re.search(r'генераци[яи].*план', paragraph, re.IGNORECASE):
            gen_action_id, _ = self.find_or_create_action("Генерация плана питания")
            plan_state = self.find_or_create_state(plan_id, "План питания", "сгенерирован")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            profile_id, _ = self.find_or_create_object("Профиль")
            profile_state = self.find_or_create_state(profile_id, "Профиль", "настроен")
            
            self.add_connection(f"{user_id}{auth_state}", gen_action_id)
            self.add_connection(f"{profile_id}{profile_state}", gen_action_id)
            self.add_connection(gen_action_id, f"{plan_id}{plan_state}")

    def process_recipes_paragraph(self, paragraph: str):
        """Обрабатывает абзац про рецепты"""
        recipe_id, recipe_obj = self.find_or_create_object("Рецепт")
        ingredient_id, ingredient_obj = self.find_or_create_object("Ингредиент")
        
        if re.search(r'поиск.*рецепт', paragraph, re.IGNORECASE):
            search_action_id, _ = self.find_or_create_action("Поиск рецептов")
            recipe_state = self.find_or_create_state(recipe_id, "Рецепт", "найден")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            self.add_connection(f"{user_id}{auth_state}", search_action_id)
            self.add_connection(search_action_id, f"{recipe_id}{recipe_state}")
        
        if re.search(r'добавлени[ея].*рецепт', paragraph, re.IGNORECASE):
            add_action_id, _ = self.find_or_create_action("Добавление рецепта")
            recipe_state = self.find_or_create_state(recipe_id, "Рецепт", "добавлен")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            self.add_connection(f"{user_id}{auth_state}", add_action_id)
            self.add_connection(add_action_id, f"{recipe_id}{recipe_state}")

    def process_shopping_paragraph(self, paragraph: str):
        """Обрабатывает абзац про список покупок"""
        list_id, list_obj = self.find_or_create_object("Список покупок")
        
        if re.search(r'генераци[яи].*список', paragraph, re.IGNORECASE):
            gen_action_id, _ = self.find_or_create_action("Генерация списка покупок")
            list_state = self.find_or_create_state(list_id, "Список покупок", "сгенерирован")
            
            plan_id, _ = self.find_or_create_object("План питания")
            plan_state = self.find_or_create_state(plan_id, "План питания", "сгенерирован")
            self.add_connection(f"{plan_id}{plan_state}", gen_action_id)
            self.add_connection(gen_action_id, f"{list_id}{list_state}")
        
        if re.search(r'редактировани[ея].*список', paragraph, re.IGNORECASE):
            edit_action_id, _ = self.find_or_create_action("Редактирование списка покупок")
            list_edit_state = self.find_or_create_state(list_id, "Список покупок", "отредактирован")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            self.add_connection(f"{user_id}{auth_state}", edit_action_id)
            self.add_connection(edit_action_id, f"{list_id}{list_edit_state}")

    def process_api_paragraph(self, paragraph: str):
        """Обрабатывает абзац про API"""
        api_id, api_obj = self.find_or_create_object("API")
        
        if re.search(r'разработка.*API', paragraph, re.IGNORECASE):
            dev_action_id, _ = self.find_or_create_action("Разработка API")
            api_state = self.find_or_create_state(api_id, "API", "разработан")
            self.add_connection(dev_action_id, f"{api_id}{api_state}")

    def process_database_paragraph(self, paragraph: str):
        """Обрабатывает абзац про базу данных"""
        db_id, db_obj = self.find_or_create_object("База данных")
        
        if re.search(r'хранени[ея].*данн', paragraph, re.IGNORECASE):
            store_action_id, _ = self.find_or_create_action("Хранение данных")
            db_state = self.find_or_create_state(db_id, "База данных", "настроена")
            self.add_connection(store_action_id, f"{db_id}{db_state}")

    def process_general_paragraph(self, paragraph: str):
        """Обрабатывает общий абзац"""
        # Пытаемся найти ключевые слова
        if re.search(r'веб.*приложени[ея]|SPA', paragraph, re.IGNORECASE):
            app_id, app_obj = self.find_or_create_object("Приложение")
            app_state = self.find_or_create_state(app_id, "Приложение", "разработано")
            
            dev_action_id, _ = self.find_or_create_action("Разработка приложения")
            self.add_connection(dev_action_id, f"{app_id}{app_state}")

    def analyze_tz_file(self, tz_file: str):
        """Анализирует весь файл ТЗ по абзацам"""
        print(f"📖 Анализ ТЗ из файла: {tz_file}")
        
        try:
            with open(tz_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разбиваем на абзацы (пустые строки как разделители)
            paragraphs = re.split(r'\n\s*\n', content)
            
            total_paragraphs = len(paragraphs)
            print(f"📊 Найдено абзацев: {total_paragraphs}")
            
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    print(f"\n[{i+1}/{total_paragraphs}] ", end="")
                    self.analyze_paragraph(paragraph)
            
            # Сохраняем модель
            self.save_model()
            
            print(f"\n✅ Анализ завершен!")
            self.print_summary()
            
        except Exception as e:
            print(f"❌ Ошибка при анализе файла: {e}")

    def save_model(self):
        """Сохраняет модель в JSON файл"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.model, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Модель сохранена в {self.output_file}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения модели: {e}")
            return False

    def print_summary(self):
        """Выводит сводку по модели"""
        print("\n" + "="*60)
        print("📊 СВОДКА МОДЕЛИ")
        print("="*60)
        
        print(f"\n🎯 Действий: {len(self.model['model_actions'])}")
        for action in self.model['model_actions']:
            print(f"  • {action['action_name']} ({action['action_id']})")
        
        print(f"\n🏛️ Объектов: {len(self.model['model_objects'])}")
        for obj in self.model['model_objects']:
            states = ", ".join([f"{s['state_name']} ({s['state_id']})" for s in obj['resource_state'][:3]])
            if len(obj['resource_state']) > 3:
                states += f" (+{len(obj['resource_state'])-3})"
            print(f"  • {obj['object_name']}: {states}")
        
        print(f"\n🔗 Связей: {len(self.model['model_connections'])}")
        
        # Показываем примеры связей
        print("\n📌 Примеры связей:")
        for conn in self.model['model_connections'][:10]:
            print(f"  • {conn['connection_out']} → {conn['connection_in']}")
        if len(self.model['model_connections']) > 10:
            print(f"  ... и еще {len(self.model['model_connections']) - 10} связей")
        
        print("\n" + "="*60)

def main():
    """Основная функция"""
    analyzer = ParagraphAnalyzer("correct_mindful_meals_model.json")
    
    # Анализируем ТЗ
    analyzer.analyze_tz_file("exam.txt")
    
    print(f"\n🎯 Для использования модели:")
    print(f"   1. Откройте {analyzer.output_file}")
    print(f"   2. Используйте для визуализации графа")
    print(f"   3. Интегрируйте в процесс разработки")

if __name__ == "__main__":
    main()