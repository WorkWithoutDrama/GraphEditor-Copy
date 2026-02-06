#!/usr/bin/env python3
"""
Продвинутый построитель модели из ТЗ
Создает более точные связи между действиями и состояниями
"""

import json
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

class AdvancedModelBuilder:
    def __init__(self, output_file: str = "advanced_model.json"):
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
        
        # База знаний о типах действий и их эффектах
        self.action_templates = {
            "регистрация": {
                "required_objects": ["Пользователь", "Email", "Пароль"],
                "input_states": {
                    "Пользователь": "незарегистрирован",
                    "Email": "не подтвержден",
                    "Пароль": "не установлен"
                },
                "output_states": {
                    "Пользователь": "зарегистрирован",
                    "Email": "подтвержден", 
                    "Пароль": "установлен"
                }
            },
            "авторизация": {
                "required_objects": ["Пользователь", "Сессия"],
                "input_states": {
                    "Пользователь": "зарегистрирован",
                    "Сессия": "не активна"
                },
                "output_states": {
                    "Пользователь": "авторизован",
                    "Сессия": "активна"
                }
            },
            "настройка профиля": {
                "required_objects": ["Пользователь", "Профиль"],
                "input_states": {
                    "Пользователь": "авторизован",
                    "Профиль": "не настроен"
                },
                "output_states": {
                    "Профиль": "настроен"
                }
            },
            "расчет нормы": {
                "required_objects": ["Профиль", "Данные"],
                "input_states": {
                    "Профиль": "настроен"
                },
                "output_states": {
                    "Данные": "расчитаны"
                }
            },
            "добавление рецепта": {
                "required_objects": ["Пользователь", "Рецепт"],
                "input_states": {
                    "Пользователь": "авторизован"
                },
                "output_states": {
                    "Рецепт": "добавлен"
                }
            },
            "генерация плана": {
                "required_objects": ["Пользователь", "План питания"],
                "input_states": {
                    "Пользователь": "авторизован",
                    "Профиль": "настроен"
                },
                "output_states": {
                    "План питания": "сгенерирован"
                }
            },
            "генерация списка": {
                "required_objects": ["План питания", "Список покупок"],
                "input_states": {
                    "План питания": "сгенерирован"
                },
                "output_states": {
                    "Список покупок": "сгенерирован"
                }
            }
        }

    def generate_id(self, prefix: str, number: int) -> str:
        """Генерирует ID с префиксом"""
        return f"{prefix}{number:05d}"

    def find_or_create_object(self, object_name: str) -> Tuple[str, Dict]:
        """Находит или создает объект"""
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
            "resource_state": []
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
                
                return state_id
        
        return ""

    def find_or_create_action(self, action_name: str) -> Tuple[str, Dict]:
        """Находит или создает действие"""
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
        """Добавляет связь"""
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

    def process_action(self, action_name: str, context: Dict = None):
        """Обрабатывает действие с использованием шаблонов"""
        action_name_lower = action_name.lower()
        
        # Ищем подходящий шаблон
        template = None
        for key in self.action_templates:
            if key in action_name_lower:
                template = self.action_templates[key]
                break
        
        if not template:
            # Используем общий шаблон
            template = {
                "required_objects": ["Пользователь", "Система"],
                "input_states": {
                    "Пользователь": "активен"
                },
                "output_states": {
                    "Система": "обработано"
                }
            }
        
        # Создаем действие
        action_id, action = self.find_or_create_action(action_name)
        
        # Обрабатываем входные состояния
        for obj_name in template["input_states"]:
            state_name = template["input_states"][obj_name]
            obj_id, obj = self.find_or_create_object(obj_name)
            state_id = self.find_or_create_state(obj_id, obj_name, state_name)
            
            # Добавляем связь: состояние → действие
            self.add_connection(f"{obj_id}{state_id}", action_id)
        
        # Обрабатываем выходные состояния
        for obj_name in template["output_states"]:
            state_name = template["output_states"][obj_name]
            obj_id, obj = self.find_or_create_object(obj_name)
            state_id = self.find_or_create_state(obj_id, obj_name, state_name)
            
            # Добавляем связь: действие → состояние
            self.add_connection(action_id, f"{obj_id}{state_id}")
        
        # Если в контексте есть дополнительные объекты
        if context and "objects" in context:
            for obj_name in context["objects"]:
                obj_id, obj = self.find_or_create_object(obj_name)
                # По умолчанию добавляем связь от действия к объекту
                state_id = self.find_or_create_state(obj_id, obj_name, "затронут")
                self.add_connection(action_id, f"{obj_id}{state_id}")

    def analyze_tz_by_sections(self, tz_file: str):
        """Анализирует ТЗ по разделам"""
        print(f"📖 Анализ ТЗ: {tz_file}")
        
        try:
            with open(tz_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Разделяем на основные разделы
            sections = re.split(r'\n\d+\.\s+', content)
            
            for section in sections:
                if not section.strip():
                    continue
                
                # Определяем тип раздела
                first_line = section.split('\n')[0].strip()
                
                if "ОБЩИЕ СВЕДЕНИЯ" in first_line:
                    print(f"\n📋 Раздел: {first_line}")
                    self.process_general_info(section)
                
                elif "ТРЕБОВАНИЯ К ФУНКЦИОНАЛУ" in first_line:
                    print(f"\n🎯 Раздел: {first_line}")
                    self.process_functional_requirements(section)
                
                elif "ТЕХНОЛОГИЧЕСКИЕ ТРЕБОВАНИЯ" in first_line:
                    print(f"\n⚙️ Раздел: {first_line}")
                    self.process_tech_requirements(section)
                
                elif "ДИЗАЙН" in first_line or "ИНТЕРФЕЙС" in first_line:
                    print(f"\n🎨 Раздел: {first_line}")
                    self.process_design_requirements(section)
                
                elif "ПРИЕМКА" in first_line or "ТЕСТИРОВАНИЕ" in first_line:
                    print(f"\n🧪 Раздел: {first_line}")
                    self.process_testing_requirements(section)
            
            # Сохраняем модель
            self.save_model()
            print(f"\n✅ Модель сохранена в {self.output_file}")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def process_general_info(self, section: str):
        """Обрабатывает общие сведения"""
        lines = section.split('\n')
        for line in lines:
            if "Название проекта:" in line:
                print(f"   📛 {line.strip()}")
            elif "Цель проекта:" in line:
                print(f"   🎯 {line.strip()}")
                # Создаем объект "Проект"
                self.find_or_create_object("Проект")
                self.find_or_create_state(self.object_names_to_ids["Проект"], "Проект", "определен")

    def process_functional_requirements(self, section: str):
        """Обрабатывает функциональные требования"""
        lines = section.split('\n')
        current_subsection = None
        
        for line in lines:
            line = line.strip()
            
            # Определяем подразделы
            if "Регистрация и Авторизация:" in line:
                current_subsection = "auth"
                print(f"   🔐 {line}")
                
                # Обрабатываем регистрацию
                self.process_action("Регистрация пользователя")
                
                # Обрабатываем авторизацию
                self.process_action("Авторизация пользователя")
                
                # Обрабатываем восстановление пароля
                self.process_action("Восстановление пароля")
                
            elif "Настройка Профиля:" in line:
                current_subsection = "profile"
                print(f"   👤 {line}")
                
                self.process_action("Настройка профиля пользователя")
                
                # Дополнительные действия
                self.process_action("Ввод личных данных")
                self.process_action("Расчет нормы калорий")
                
            elif "Планировщик Питания" in line:
                current_subsection = "planner"
                print(f"   🍽️ {line}")
                
                # Создаем объекты
                self.find_or_create_object("Календарь")
                self.find_or_create_object("Прием пищи")
                self.find_or_create_object("Блюдо")
                self.find_or_create_object("Продукт")
                
                # Действия
                self.process_action("Отображение календаря")
                self.process_action("Управление приемами пищи")
                self.process_action("Поиск продуктов")
                self.process_action("Отображение статистики")
                self.process_action("Генерация плана питания")
                
            elif "База Рецептов" in line:
                current_subsection = "recipes"
                print(f"   📚 {line}")
                
                self.find_or_create_object("Рецепт")
                self.find_or_create_object("Ингредиент")
                
                self.process_action("Поиск рецептов")
                self.process_action("Добавление рецептов")
                self.process_action("Просмотр информации о рецепте")
                
            elif "Список Покупок" in line:
                current_subsection = "shopping"
                print(f"   🛒 {line}")
                
                self.find_or_create_object("Список покупок")
                
                self.process_action("Генерация списка покупок")
                self.process_action("Редактирование списка покупок")

    def process_tech_requirements(self, section: str):
        """Обрабатывает технологические требования"""
        lines = section.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if "API:" in line:
                print(f"   🔌 {line}")
                self.find_or_create_object("API")
                self.process_action("Разработка API")
                
            elif "База Данных:" in line:
                print(f"   🗄️ {line}")
                self.find_or_create_object("База данных")
                self.process_action("Хранение данных")

    def process_design_requirements(self, section: str):
        """Обрабатывает требования к дизайну"""
        print("   🎨 Требования к интерфейсу")
        self.find_or_create_object("Интерфейс")
        self.find_or_create_state(self.object_names_to_ids["Интерфейс"], "Интерфейс", "спроектирован")

    def process_testing_requirements(self, section: str):
        """Обрабатывает требования к тестированию"""
        print("   🧪 Требования к тестированию")
        self.find_or_create_object("Тестирование")
        self.find_or_create_state(self.object_names_to_ids["Тестирование"], "Тестирование", "выполнено")

    def save_model(self):
        """Сохраняет модель"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.model, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            return False

    def print_summary(self):
        """Выводит сводку"""
        print("\n" + "="*60)
        print("📊 СВОДКА МОДЕЛИ")
        print("="*60)
        
        print(f"\n🎯 Действий: {len(self.model['model_actions'])}")
        for action in self.model['model_actions'][:10]:  # Показываем первые 10
            print(f"  • {action['action_name']} ({action['action_id']})")
        if len(self.model['model_actions']) > 10:
            print(f"  ... и еще {len(self.model['model_actions']) - 10}")
        
        print(f"\n🏛️ Объектов: {len(self.model['model_objects'])}")
        for obj in self.model['model_objects'][:10]:
            states = ", ".join([s['state_name'] for s in obj['resource_state'][:2]])
            if len(obj['resource_state']) > 2:
                states += f" (+{len(obj['resource_state'])-2})"
            print(f"  • {obj['object_name']}: {states}")
        
        print(f"\n🔗 Связей: {len(self.model['model_connections'])}")
        
        print("\n" + "="*60)

def main():
    """Основная функция"""
    builder = AdvancedModelBuilder("mindful_meals_advanced.json")
    
    # Анализируем ТЗ
    builder.analyze_tz_by_sections("exam.txt")
    
    # Выводим сводку
    builder.print_summary()
    
    print(f"\n🎯 Для визуализации графа используйте:")
    print("   • Graphviz с DOT форматом")
    print("   • Mermaid.js для веб-визуализации")
    print("   • PlantUML для UML-диаграмм")

if __name__ == "__main__":
    main()