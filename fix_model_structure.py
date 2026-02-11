#!/usr/bin/env python3
"""
Исправление структуры модели для совместимости с graph-manager.js
"""

import json
import os
import datetime

def fix_action_structure(action_data):
    """
    Исправляет структуру действия для совместимости с graph-manager.js
    
    Вход: {"action_actor": "...", "action_action": "...", "action_place": "...", ...}
    Выход: Действие с полем "action_name" для графа
    """
    # Создаем метку для графа: "актор действие (место)"
    action_label = f"{action_data['action_actor']} {action_data['action_action']}"
    if action_data.get("action_place"):
        action_label += f" ({action_data['action_place']})"
    
    return {
        # Новая структура (основная)
        "action_actor": action_data["action_actor"],
        "action_action": action_data["action_action"],
        "action_place": action_data.get("action_place", ""),
        
        # Совместимость с graph-manager.js
        "action_name": action_label,
        
        # Остальные поля
        "action_links": action_data.get("action_links", {
            "manual": "Из LLM анализа",
            "API": "",
            "UI": ""
        })
    }

def fix_model_file(model_filename):
    """
    Исправляет существующий файл модели для совместимости
    """
    if not os.path.exists(model_filename):
        print(f"❌ Файл не найден: {model_filename}")
        return False
    
    try:
        with open(model_filename, 'r', encoding='utf-8') as f:
            model = json.load(f)
        
        # Исправляем действия
        if "model_actions" in model:
            fixed_actions = []
            for action in model["model_actions"]:
                # Если уже есть action_name, оставляем как есть
                if "action_name" not in action:
                    # Если есть новая структура, создаем action_name
                    if "action_actor" in action and "action_action" in action:
                        action_label = f"{action['action_actor']} {action['action_action']}"
                        if action.get("action_place"):
                            action_label += f" ({action['action_place']})"
                        action["action_name"] = action_label
                
                fixed_actions.append(action)
            
            model["model_actions"] = fixed_actions
            print(f"✅ Исправлено {len(fixed_actions)} действий")
        
        # Сохраняем обратно
        with open(model_filename, 'w', encoding='utf-8') as f:
            json.dump(model, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Файл исправлен: {model_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении файла: {e}")
        return False

# Тестируем
if __name__ == "__main__":
    print("🔧 ИСПРАВЛЕНИЕ СТРУКТУРЫ МОДЕЛИ")
    print("=" * 50)
    
    # Проверяем папку models
    if os.path.exists("models"):
        for file in os.listdir("models"):
            if file.endswith(".json"):
                filepath = os.path.join("models", file)
                print(f"📄 Проверяю: {file}")
                fix_model_file(filepath)
    else:
        print("📁 Папка models/ не существует")