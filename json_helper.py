import json
import time
import random
from datetime import datetime

class NewJsonHelper:
    def __init__(self, json_file="new_project_model.json"):
        self.json_file = json_file
        self.data = {"model_actions": [], "model_objects": [], "model_connections": []}
        
        # Загружаем существующий файл, если он есть
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            # Создаем новый файл с базовой структурой
            self.save_json()
    
    def generate_id(self, prefix):
        """Генерация ID по правилам: префикс + timestamp + 4 случайных цифры"""
        timestamp = int(time.time())
        random_digits = str(random.randint(1000, 9999))
        return f"{prefix}{timestamp}{random_digits}"
    
    def add_action(self, action_name, action_links=None):
        """Добавление нового действия"""
        action_id = self.generate_id("a")
        
        action = {
            "action_id": action_id,
            "action_name": action_name,
            "action_links": action_links or {}
        }
        
        self.data["model_actions"].append(action)
        self.save_json()
        return action_id
    
    def add_object(self, object_name, state_name="null"):
        """Добавление нового объекта с состоянием"""
        object_id = self.generate_id("o")
        state_id = "s00000" if state_name == "null" else self.generate_id("s")
        
        obj = {
            "object_id": object_id,
            "object_name": object_name,
            "resource_state": {
                "state_id": state_id,
                "state_name": state_name
            },
            "object_links": {}
        }
        
        self.data["model_objects"].append(obj)
        self.save_json()
        return f"{object_id}{state_id}"
    
    def add_connection(self, connection_out, connection_in):
        """Добавление связи между элементами"""
        connection = {
            "connection_out": connection_out,
            "connection_in": connection_in
        }
        
        self.data["model_connections"].append(connection)
        self.save_json()
        return True
    
    def save_json(self):
        """Сохранение JSON в файл"""
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def print_structure(self):
        """Вывод текущей структуры"""
        print(f"Количество действий: {len(self.data['model_actions'])}")
        print(f"Количество объектов: {len(self.data['model_objects'])}")
        print(f"Количество связей: {len(self.data['model_connections'])}")
        
        print("\nДействия:")
        for action in self.data["model_actions"]:
            print(f"  - {action['action_name']} (ID: {action['action_id']})")
        
        print("\nОбъекты:")
        for obj in self.data["model_objects"]:
            print(f"  - {obj['object_name']} (ID: {obj['object_id']})")
        
        print("\nСвязи:")
        for conn in self.data["model_connections"]:
            print(f"  - {conn['connection_out']} → {conn['connection_in']}")

# Пример использования:
if __name__ == "__main__":
    helper = NewJsonHelper()
    
    # Пример добавления элементов
    print("Добавляем элементы в новую структуру JSON...")
    
    # Добавляем действия
    action1_id = helper.add_action("Аутентификация пользователя")
    action2_id = helper.add_action("Планирование питания")
    action3_id = helper.add_action("Генерация списка покупок")
    
    # Добавляем объекты
    object1_id = helper.add_object("Пользователь")
    object2_id = helper.add_object("Рецепт", "опубликован")
    object3_id = helper.add_object("План питания", "активен")
    
    # Добавляем связи
    helper.add_connection(action1_id, object1_id + "s00000")
    helper.add_connection(object1_id + "s00000", action2_id)
    helper.add_connection(action2_id, object3_id + "s00000")
    helper.add_connection(object2_id, action3_id)
    
    print("\nТекущая структура:")
    helper.print_structure()
    
    print(f"\nJSON сохранен в файл: {helper.json_file}")