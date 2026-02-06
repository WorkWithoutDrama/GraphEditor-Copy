#!/usr/bin/env python3
"""
Детальный анализатор ТЗ по абзацам
Тщательно анализирует каждый абзац для создания полной модели
"""

import json
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

class DetailedParagraphAnalyzer:
    def __init__(self, output_file: str = "detailed_model.json"):
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
        
        # База знаний для анализа
        self.domain_knowledge = {
            "веб-приложение": {
                "объекты": ["Пользователь", "Сессия", "Профиль", "Данные", "Интерфейс"],
                "действия": ["регистрация", "авторизация", "настройка", "просмотр", "редактирование"]
            },
            "планировщик питания": {
                "объекты": ["План питания", "Рецепт", "Продукт", "Ингредиент", "Список покупок"],
                "действия": ["планирование", "генерация", "поиск", "добавление", "расчет"]
            }
        }

    def generate_id(self, prefix: str, number: int) -> str:
        """Генерирует ID с префиксом"""
        return f"{prefix}{number:05d}"

    def extract_paragraph_content(self, paragraph: str) -> Dict:
        """Извлекает структурированную информацию из абзаца"""
        result = {
            "тип": "неизвестно",
            "действия": [],
            "объекты": [],
            "условия": {},
            "связи": []
        }
        
        # Определяем тип абзаца
        paragraph_lower = paragraph.lower()
        
        if re.search(r'регистрация|авторизация|вход|логин', paragraph_lower):
            result["тип"] = "аутентификация"
            result["действия"].extend(["регистрация", "авторизация"])
            result["объекты"].extend(["пользователь", "email", "пароль", "сессия"])
        
        elif re.search(r'профиль|данные.*личные|возраст.*рост.*вес', paragraph_lower):
            result["тип"] = "профиль"
            result["действия"].append("настройка профиля")
            result["объекты"].extend(["профиль", "данные"])
            
            if re.search(r'расчет.*калори|норм[аы].*БЖУ', paragraph_lower):
                result["действия"].append("расчет нормы")
                result["объекты"].append("расчет")
        
        elif re.search(r'планирован.*питани[яе]|календар[ья]|прием[аов] пищи', paragraph_lower):
            result["тип"] = "планирование"
            result["действия"].extend(["отображение календаря", "управление приемами пищи"])
            result["объекты"].extend(["календарь", "прием пищи", "блюдо", "продукт"])
            
            if re.search(r'генераци[яи].*план', paragraph_lower):
                result["действия"].append("генерация плана")
                result["объекты"].append("план питания")
        
        elif re.search(r'рецепт[аы]|ингредиент', paragraph_lower):
            result["тип"] = "рецепты"
            result["действия"].extend(["поиск рецептов", "добавление рецептов", "просмотр информации"])
            result["объекты"].extend(["рецепт", "ингредиент"])
        
        elif re.search(r'список.*покупок|покуп[ки]', paragraph_lower):
            result["тип"] = "покупки"
            result["действия"].extend(["генерация списка", "редактирование списка"])
            result["объекты"].append("список покупок")
        
        elif re.search(r'API|эндпоинт', paragraph_lower):
            result["тип"] = "API"
            result["действия"].append("разработка API")
            result["объекты"].append("API")
        
        elif re.search(r'баз[аы].*данн', paragraph_lower):
            result["тип"] = "база данных"
            result["действия"].append("хранение данных")
            result["объекты"].append("база данных")
        
        elif re.search(r'тестирован|проверк', paragraph_lower):
            result["тип"] = "тестирование"
            result["действия"].append("тестирование")
            result["объекты"].append("тестирование")
        
        return result

    def find_or_create_object(self, object_name: str) -> Tuple[str, Dict]:
        """Находит или создает объект"""
        # Приводим к стандартному виду
        object_name = object_name.strip().title()
        
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
        """Находит или создает состояние"""
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
                
                print(f"   ➕ Состояние: {object_name} - {state_name} ({state_id})")
                return state_id
        
        return ""

    def create_action_name(self, base_action: str, context: str = "") -> str:
        """Создает полное название действия"""
        action = base_action.strip().title()
        
        # Добавляем объект, если нужно
        if context and not any(word in action.lower() for word in ["пользователь", "профиль", "рецепт", "план"]):
            if "регистрация" in action.lower():
                return f"{action} пользователя"
            elif "настройка" in action.lower():
                return f"{action} профиля"
            elif "добавление" in action.lower():
                return f"{action} рецепта"
            elif "генерация" in action.lower() and "список" in context.lower():
                return f"{action} списка покупок"
            elif "генерация" in action.lower():
                return f"{action} плана питания"
        
        return action

    def find_or_create_action(self, action_name: str, context: str = "") -> Tuple[str, Dict]:
        """Находит или создает действие с полным названием"""
        # Создаем полное название
        full_action_name = self.create_action_name(action_name, context)
        
        # Проверяем существование
        for action in self.model["model_actions"]:
            if action["action_name"] == full_action_name:
                return action["action_id"], action
        
        # Создаем новое действие
        action_id = self.generate_id("a", self.next_action_id)
        self.next_action_id += 1
        
        new_action = {
            "action_id": action_id,
            "action_name": full_action_name,
            "action_links": {
                "manual": f"инструкция по {full_action_name.lower()}",
                "API": f"/api/{full_action_name.lower().replace(' ', '-')}",
                "UI": f"/{full_action_name.lower().replace(' ', '-')}"
            }
        }
        
        self.model["model_actions"].append(new_action)
        self.action_ids.add(action_id)
        
        print(f"➕ Действие: {full_action_name} ({action_id})")
        return action_id, new_action

    def add_connection(self, connection_out: str, connection_in: str, description: str = ""):
        """Добавляет уникальную связь с описанием"""
        # Проверяем на дубликаты
        for conn in self.model["model_connections"]:
            if conn["connection_out"] == connection_out and conn["connection_in"] == connection_in:
                return
        
        new_connection = {
            "connection_out": connection_out,
            "connection_in": connection_in
        }
        
        self.model["model_connections"].append(new_connection)
        
        if description:
            print(f"   🔗 Связь: {connection_out} → {connection_in} ({description})")
        else:
            print(f"   🔗 Связь: {connection_out} → {connection_in}")

    def process_paragraph(self, paragraph: str, paragraph_num: int):
        """Обрабатывает один абзац ТЗ"""
        paragraph = paragraph.strip()
        if not paragraph or len(paragraph) < 10:
            return
        
        print(f"\n📄 Абзац {paragraph_num}: {paragraph[:80]}...")
        
        # Извлекаем структурированную информацию
        analysis = self.extract_paragraph_content(paragraph)
        
        if analysis["тип"] == "неизвестно":
            print("   ℹ️ Не удалось определить тип абзаца")
            return
        
        print(f"   🏷️ Тип: {analysis['тип'].title()}")
        
        # Обрабатываем в зависимости от типа
        if analysis["тип"] == "аутентификация":
            self.process_auth_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "профиль":
            self.process_profile_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "планирование":
            self.process_planning_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "рецепты":
            self.process_recipes_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "покупки":
            self.process_shopping_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "API":
            self.process_api_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "база данных":
            self.process_database_paragraph(analysis, paragraph)
        
        elif analysis["тип"] == "тестирование":
            self.process_testing_paragraph(analysis, paragraph)

    def process_auth_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про аутентификацию"""
        # Регистрация
        reg_action_id, _ = self.find_or_create_action("Регистрация", "пользователь")
        
        # Объекты для регистрации
        user_id, user_obj = self.find_or_create_object("Пользователь")
        email_id, email_obj = self.find_or_create_object("Email")
        pass_id, pass_obj = self.find_or_create_object("Пароль")
        
        # Состояния до регистрации
        user_start = self.find_or_create_state(user_id, "Пользователь", "незарегистрирован")
        email_start = self.find_or_create_state(email_id, "Email", "не подтвержден")
        pass_start = self.find_or_create_state(pass_id, "Пароль", "не установлен")
        
        # Состояния после регистрации
        user_end = self.find_or_create_state(user_id, "Пользователь", "зарегистрирован")
        email_end = self.find_or_create_state(email_id, "Email", "подтвержден")
        pass_end = self.find_or_create_state(pass_id, "Пароль", "установлен")
        
        # Связи: начальные состояния → действие
        self.add_connection(f"{user_id}{user_start}", reg_action_id, "незарегистрированный пользователь начинает регистрацию")
        self.add_connection(f"{email_id}{email_start}", reg_action_id, "неподтвержденный email участвует в регистрации")
        self.add_connection(f"{pass_id}{pass_start}", reg_action_id, "неустановленный пароль участвует в регистрации")
        
        # Связи: действие → конечные состояния
        self.add_connection(reg_action_id, f"{user_id}{user_end}", "регистрация завершена - пользователь зарегистрирован")
        self.add_connection(reg_action_id, f"{email_id}{email_end}", "регистрация завершена - email подтвержден")
        self.add_connection(reg_action_id, f"{pass_id}{pass_end}", "регистрация завершена - пароль установлен")
        
        # Авторизация
        if "авторизация" in [a.lower() for a in analysis["действия"]]:
            auth_action_id, _ = self.find_or_create_action("Авторизация", "пользователь")
            session_id, session_obj = self.find_or_create_object("Сессия")
            
            # Состояния для авторизации
            session_start = self.find_or_create_state(session_id, "Сессия", "не активна")
            session_end = self.find_or_create_state(session_id, "Сессия", "активна")
            user_auth = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            
            # Связи: зарегистрированный пользователь → авторизация
            self.add_connection(f"{user_id}{user_end}", auth_action_id, "зарегистрированный пользователь начинает авторизацию")
            self.add_connection(f"{session_id}{session_start}", auth_action_id, "неактивная сессия участвует в авторизации")
            
            # Связи: авторизация → конечные состояния
            self.add_connection(auth_action_id, f"{user_id}{user_auth}", "авторизация завершена - пользователь авторизован")
            self.add_connection(auth_action_id, f"{session_id}{session_end}", "авторизация завершена - сессия активна")
        
        # Восстановление пароля
        if re.search(r'восстановлени[ея]|забыл.*парол', paragraph, re.IGNORECASE):
            recover_action_id, _ = self.find_or_create_action("Восстановление", "пароль")
            pass_recovered = self.find_or_create_state(pass_id, "Пароль", "восстановлен")
            
            self.add_connection(f"{user_id}{user_end}", recover_action_id, "зарегистрированный пользователь восстанавливает пароль")
            self.add_connection(recover_action_id, f"{pass_id}{pass_recovered}", "восстановление пароля завершено")

    def process_profile_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про профиль"""
        # Настройка профиля
        profile_action_id, _ = self.find_or_create_action("Настройка", "профиль")
        profile_id, profile_obj = self.find_or_create_object("Профиль")
        user_id, _ = self.find_or_create_object("Пользователь")
        
        # Пользователь должен быть авторизован
        user_auth_state = None
        for state in self.model["model_objects"]:
            if state["object_name"] == "Пользователь":
                for s in state["resource_state"]:
                    if s["state_name"] == "авторизован":
                        user_auth_state = s["state_id"]
                        break
        
        if not user_auth_state:
            user_auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
        
        # Состояния профиля
        profile_start = self.find_or_create_state(profile_id, "Профиль", "не настроен")
        profile_end = self.find_or_create_state(profile_id, "Профиль", "настроен")
        
        # Связи
        self.add_connection(f"{user_id}{user_auth_state}", profile_action_id, "авторизованный пользователь настраивает профиль")
        self.add_connection(f"{profile_id}{profile_start}", profile_action_id, "нененастроенный профиль участвует в настройке")
        self.add_connection(profile_action_id, f"{profile_id}{profile_end}", "настройка профиля завершена")
        
        # Ввод личных данных
        if re.search(r'ввод.*данных|личные данные', paragraph, re.IGNORECASE):
            data_action_id, _ = self.find_or_create_action("Ввод", "личные данные")
            data_id, data_obj = self.find_or_create_object("Данные")
            data_start = self.find_or_create_state(data_id, "Данные", "не заполнены")
            data_end = self.find_or_create_state(data_id, "Данные", "заполнены")
            
            self.add_connection(f"{profile_id}{profile_start}", data_action_id, "нененастроенный профиль требует ввода данных")
            self.add_connection(data_action_id, f"{data_id}{data_end}", "ввод данных завершен")
        
        # Расчет нормы
        if re.search(r'расчет.*калори|норм[аы].*БЖУ', paragraph, re.IGNORECASE):
            calc_action_id, _ = self.find_or_create_action("Расчет", "норма калорий")
            calc_id, calc_obj = self.find_or_create_object("Расчет")
            calc_start = self.find_or_create_state(calc_id, "Расчет", "не выполнен")
            calc_end = self.find_or_create_state(calc_id, "Расчет", "выполнен")
            
            self.add_connection(f"{profile_id}{profile_end}", calc_action_id, "настроенный профиль требует расчета")
            self.add_connection(calc_action_id, f"{calc_id}{calc_end}", "расчет нормы завершен")

    def process_planning_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про планирование"""
        # Основные объекты
        calendar_id, calendar_obj = self.find_or_create_object("Календарь")
        meal_id, meal_obj = self.find_or_create_object("Прием пищи")
        dish_id, dish_obj = self.find_or_create_object("Блюдо")
        product_id, product_obj = self.find_or_create_object("Продукт")
        
        user_id, _ = self.find_or_create_object("Пользователь")
        user_auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
        
        # Отображение календаря
        if re.search(r'отображени[ея].*календар', paragraph, re.IGNORECASE):
            show_action_id, _ = self.find_or_create_action("Отображение", "календарь")
            calendar_state = self.find_or_create_state(calendar_id, "Календарь", "отображен")
            
            self.add_connection(f"{user_id}{user_auth_state}", show_action_id, "авторизованный пользователь просматривает календарь")
            self.add_connection(show_action_id, f"{calendar_id}{calendar_state}", "календарь отображен")
        
        # Управление приемами пищи
        if re.search(r'добавлени[ея].*удалени[ея].*редактировани[ея]', paragraph, re.IGNORECASE):
            manage_action_id, _ = self.find_or_create_action("Управление", "приемы пищи")
            meal_state = self.find_or_create_state(meal_id, "Прием пищи", "управляется")
            
            self.add_connection(f"{user_id}{user_auth_state}", manage_action_id, "авторизованный пользователь управляет приемами пищи")
            self.add_connection(manage_action_id, f"{meal_id}{meal_state}", "управление приемами пищи выполнено")
        
        # Генерация плана
        if re.search(r'генераци[яи].*план', paragraph, re.IGNORECASE):
            gen_action_id, _ = self.find_or_create_action("Генерация", "план питания")
            plan_id, plan_obj = self.find_or_create_object("План питания")
            plan_state = self.find_or_create_state(plan_id, "План питания", "сгенерирован")
            
            profile_id, _ = self.find_or_create_object("Профиль")
            profile_state = self.find_or_create_state(profile_id, "Профиль", "настроен")
            
            self.add_connection(f"{user_id}{user_auth_state}", gen_action_id, "авторизованный пользователь генерирует план")
            self.add_connection(f"{profile_id}{profile_state}", gen_action_id, "настроенный профиль участвует в генерации плана")
            self.add_connection(gen_action_id, f"{plan_id}{plan_state}", "план питания сгенерирован")

    def process_recipes_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про рецепты"""
        recipe_id, recipe_obj = self.find_or_create_object("Рецепт")
        ingredient_id, ingredient_obj = self.find_or_create_object("Ингредиент")
        
        user_id, _ = self.find_or_create_object("Пользователь")
        user_auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
        
        # Поиск рецептов
        if re.search(r'поиск.*рецепт', paragraph, re.IGNORECASE):
            search_action_id, _ = self.find_or_create_action("Поиск", "рецепты")
            recipe_found = self.find_or_create_state(recipe_id, "Рецепт", "найден")
            
            self.add_connection(f"{user_id}{user_auth_state}", search_action_id, "авторизованный пользователь ищет рецепты")
            self.add_connection(search_action_id, f"{recipe_id}{recipe_found}", "рецепты найдены")
        
        # Добавление рецептов
        if re.search(r'добавлени[ея].*рецепт', paragraph, re.IGNORECASE):
            add_action_id, _ = self.find_or_create_action("Добавление", "рецепты")
            recipe_added = self.find_or_create_state(recipe_id, "Рецепт", "добавлен")
            
            self.add_connection(f"{user_id}{user_auth_state}", add_action_id, "авторизованный пользователь добавляет рецепт")
            self.add_connection(add_action_id, f"{recipe_id}{recipe_added}", "рецепт добавлен")

    def process_shopping_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про покупки"""
        list_id, list_obj = self.find_or_create_object("Список покупок")
        
        # Генерация списка
        if re.search(r'генераци[яи].*список', paragraph, re.IGNORECASE):
            gen_action_id, _ = self.find_or_create_action("Генерация", "список покупок")
            list_state = self.find_or_create_state(list_id, "Список покупок", "сгенерирован")
            
            plan_id, _ = self.find_or_create_object("План питания")
            plan_state = self.find_or_create_state(plan_id, "План питания", "сгенерирован")
            
            self.add_connection(f"{plan_id}{plan_state}", gen_action_id, "сгенерированный план питания используется для генерации списка")
            self.add_connection(gen_action_id, f"{list_id}{list_state}", "список покупок сгенерирован")
        
        # Редактирование списка
        if re.search(r'редактировани[ея].*список', paragraph, re.IGNORECASE):
            edit_action_id, _ = self.find_or_create_action("Редактирование", "список покупок")
            list_edited = self.find_or_create_state(list_id, "Список покупок", "отредактирован")
            
            user_id, _ = self.find_or_create_object("Пользователь")
            user_auth_state = self.find_or_create_state(user_id, "Пользователь", "авторизован")
            
            self.add_connection(f"{user_id}{user_auth_state}", edit_action_id, "авторизованный пользователь редактирует список")
            self.add_connection(edit_action_id, f"{list_id}{list_edited}", "список покупок отредактирован")

    def process_api_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про API"""
        api_id, api_obj = self.find_or_create_object("API")
        
        if re.search(r'разработка.*API', paragraph, re.IGNORECASE):
            dev_action_id, _ = self.find_or_create_action("Разработка", "API")
            api_state = self.find_or_create_state(api_id, "API", "разработан")
            
            self.add_connection(dev_action_id, f"{api_id}{api_state}", "API разработан")

    def process_database_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про базу данных"""
        db_id, db_obj = self.find_or_create_object("База данных")
        
        if re.search(r'хранени[ея].*данн', paragraph, re.IGNORECASE):
            store_action_id, _ = self.find_or_create_action("Хранение", "данные")
            db_state = self.find_or_create_state(db_id, "База данных", "настроена")
            
            self.add_connection(store_action_id, f"{db_id}{db_state}", "база данных настроена для хранения")

    def process_testing_paragraph(self, analysis: Dict, paragraph: str):
        """Обрабатывает абзац про тестирование"""
        test_id, test_obj = self.find_or_create_object("Тестирование")
        
        if re.search(r'тестирован', paragraph, re.IGNORECASE):
            test_action_id, _ = self.find_or_create_action("Тестирование", "система")
            test_state = self.find_or_create_state(test_id, "Тестирование", "выполнено")
            
            self.add_connection(test_action_id, f"{test_id}{test_state}", "тестирование выполнено")

    def analyze_tz_file(self, tz_file: str):
        """Анализирует весь файл ТЗ"""
        print(f"📖 Начинаю детальный анализ ТЗ: {tz_file}")
        
        try:
            with open(tz_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разбиваем на абзацы
            paragraphs = re.split(r'\n\s*\n', content)
            
            print(f"📊 Найдено абзацев: {len(paragraphs)}")
            
            for i, paragraph in enumerate(paragraphs):
                self.process_paragraph(paragraph, i+1)
            
            # Сохраняем модель
            self.save_model()
            
            print(f"\n✅ Детальный анализ завершен!")
            self.print_summary()
            
        except Exception as e:
            print(f"❌ Ошибка при анализе файла: {e}")

    def save_model(self):
        """Сохраняет модель в JSON файл"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.model, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Детальная модель сохранена в {self.output_file}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения модели: {e}")
            return False

    def print_summary(self):
        """Выводит сводку по модели"""
        print("\n" + "="*60)
        print("📊 СВОДКА ДЕТАЛЬНОЙ МОДЕЛИ")
        print("="*60)
        
        print(f"\n🎯 Действий: {len(self.model['model_actions'])}")
        for action in self.model['model_actions']:
            print(f"  • {action['action_name']} ({action['action_id']})")
        
        print(f"\n🏛️ Объектов: {len(self.model['model_objects'])}")
        for obj in self.model['model_objects']:
            states = ", ".join([f"{s['state_name']}" for s in obj['resource_state'][:3]])
            if len(obj['resource_state']) > 3:
                states += f" (+{len(obj['resource_state'])-3})"
            print(f"  • {obj['object_name']}: {states}")
        
        print(f"\n🔗 Связей: {len(self.model['model_connections'])}")
        
        # Группируем связи по действиям
        connections_by_action = {}
        for conn in self.model['model_connections']:
            # Определяем действие
            action_id = None
            if conn['connection_out'].startswith('a'):
                action_id = conn['connection_out']
            elif conn['connection_in'].startswith('a'):
                action_id = conn['connection_in']
            
            if action_id:
                if action_id not in connections_by_action:
                    connections_by_action[action_id] = []
                connections_by_action[action_id].append(conn)
        
        print("\n📌 Связи по действиям:")
        for action_id, connections in list(connections_by_action.items())[:5]:  # Показываем первые 5 действий
            action_name = next((a['action_name'] for a in self.model['model_actions'] if a['action_id'] == action_id), action_id)
            print(f"  • {action_name} ({action_id}):")
            for conn in connections[:3]:  # Показываем первые 3 связи
                print(f"    - {conn['connection_out']} → {conn['connection_in']}")
            if len(connections) > 3:
                print(f"    ... и еще {len(connections)-3} связей")
        
        print("\n" + "="*60)

def main():
    """Основная функция"""
    analyzer = DetailedParagraphAnalyzer("mindful_meals_detailed.json")
    
    # Анализируем ТЗ
    analyzer.analyze_tz_file("exam.txt")
    
    print(f"\n🎯 Созданы файлы:")
    print(f"   1. {analyzer.output_file} - Детальная модель")
    print(f"   2. Используйте для генерации графа")
    print(f"   3. Проверьте полноту модели")

if __name__ == "__main__":
    main()