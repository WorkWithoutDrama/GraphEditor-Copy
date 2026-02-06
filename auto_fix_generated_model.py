#!/usr/bin/env python3
"""
Автоматический исправитель сгенерированных LLM моделей
Обнаруживает и исправляет типовые ошибки
"""

import json
import re
import sys
from typing import Dict, List, Set, Tuple, Optional

class ModelAutoFixer:
    def __init__(self):
        self.fixes_applied = []
        self.warnings = []
        self.errors = []
    
    def analyze_model(self, model: Dict) -> Dict:
        """Анализирует модель и возвращает отчет о проблемах"""
        report = {
            "problems_found": 0,
            "fixes_needed": [],
            "warnings": [],
            "errors": []
        }
        
        # Проверка структуры
        if not isinstance(model, dict):
            report["errors"].append("❌ Модель должна быть словарем JSON")
            return report
        
        # Проверка обязательных полей
        required_arrays = ["model_actions", "model_objects", "model_connections"]
        for field in required_arrays:
            if field not in model:
                report["errors"].append(f"❌ Отсутствует обязательное поле: {field}")
                report["problems_found"] += 1
        
        if report["errors"]:
            return report
        
        # Анализ действий
        report.update(self.analyze_actions(model.get("model_actions", [])))
        
        # Анализ объектов
        report.update(self.analyze_objects(model.get("model_objects", [])))
        
        # Анализ связей
        report.update(self.analyze_connections(
            model.get("model_connections", []),
            model.get("model_actions", []),
            model.get("model_objects", [])
        ))
        
        report["problems_found"] = len(report["fixes_needed"]) + len(report["warnings"]) + len(report["errors"])
        
        return report
    
    def analyze_actions(self, actions: List) -> Dict:
        """Анализирует действия"""
        result = {
            "fixes_needed": [],
            "warnings": [],
            "errors": []
        }
        
        if not actions:
            result["warnings"].append("⚠️ Модель не содержит действий")
            return result
        
        action_names = set()
        action_ids = set()
        
        for i, action in enumerate(actions):
            # Проверка обязательных полей
            if "action_name" not in action:
                result["errors"].append(f"❌ Действие {i}: отсутствует action_name")
                continue
            
            action_name = action["action_name"]
            
            # Проверка полноты названия
            if len(action_name.split()) < 2:
                result["fixes_needed"].append({
                    "type": "incomplete_action_name",
                    "action_index": i,
                    "current_name": action_name,
                    "suggested_name": self.suggest_action_name(action_name)
                })
            
            # Проверка дубликатов
            if action_name in action_names:
                result["errors"].append(f"❌ Дублирующееся название действия: {action_name}")
            
            action_names.add(action_name)
            
            # Проверка ID
            if "action_id" in action:
                if action["action_id"] in action_ids:
                    result["errors"].append(f"❌ Дублирующийся action_id: {action['action_id']}")
                action_ids.add(action["action_id"])
            else:
                result["fixes_needed"].append({
                    "type": "missing_action_id",
                    "action_index": i,
                    "action_name": action_name
                })
        
        return result
    
    def analyze_objects(self, objects: List) -> Dict:
        """Анализирует объекты"""
        result = {
            "fixes_needed": [],
            "warnings": [],
            "errors": []
        }
        
        if not objects:
            result["warnings"].append("⚠️ Модель не содержит объектов")
            return result
        
        object_names = set()
        object_ids = set()
        
        for i, obj in enumerate(objects):
            # Проверка обязательных полей
            if "object_name" not in obj:
                result["errors"].append(f"❌ Объект {i}: отсутствует object_name")
                continue
            
            object_name = obj["object_name"]
            
            # Проверка семантических ошибок
            if object_name.lower() in ["логин", "сервер", "клиент"] and "пользователь" not in object_name.lower():
                result["fixes_needed"].append({
                    "type": "semantic_object_error",
                    "object_index": i,
                    "current_name": object_name,
                    "suggested_name": self.suggest_object_name(object_name)
                })
            
            # Проверка дубликатов
            if object_name in object_names:
                result["errors"].append(f"❌ Дублирующееся название объекта: {object_name}")
            
            object_names.add(object_name)
            
            # Проверка ID
            if "object_id" in obj:
                if obj["object_id"] in object_ids:
                    result["errors"].append(f"❌ Дублирующийся object_id: {obj['object_id']}")
                object_ids.add(obj["object_id"])
            else:
                result["fixes_needed"].append({
                    "type": "missing_object_id",
                    "object_index": i,
                    "object_name": object_name
                })
            
            # Проверка состояний
            if "resource_state" in obj and isinstance(obj["resource_state"], list):
                state_names = set()
                for j, state in enumerate(obj["resource_state"]):
                    if "state_name" not in state:
                        result["fixes_needed"].append({
                            "type": "missing_state_name",
                            "object_index": i,
                            "object_name": object_name,
                            "state_index": j
                        })
                    elif state["state_name"] in state_names:
                        result["errors"].append(f"❌ Объект '{object_name}': дублирующееся состояние: {state['state_name']}")
                    else:
                        state_names.add(state["state_name"])
        
        return result
    
    def analyze_connections(self, connections: List, actions: List, objects: List) -> Dict:
        """Анализирует связи"""
        result = {
            "fixes_needed": [],
            "warnings": [],
            "errors": []
        }
        
        if not connections:
            result["warnings"].append("⚠️ Модель не содержит связей")
            return result
        
        # Собираем существующие ID
        action_ids = {a["action_id"] for a in actions if "action_id" in a}
        
        # Собираем комбинации объект+состояние
        object_state_combinations = set()
        for obj in objects:
            if "object_id" in obj and "resource_state" in obj:
                for state in obj["resource_state"]:
                    if "state_id" in state:
                        object_state_combinations.add(f"{obj['object_id']}{state['state_id']}")
        
        for i, conn in enumerate(connections):
            # Проверка обязательных полей
            if "connection_out" not in conn or "connection_in" not in conn:
                result["errors"].append(f"❌ Связь {i}: отсутствует connection_out или connection_in")
                continue
            
            out = conn["connection_out"]
            inc = conn["connection_in"]
            
            # Проверка форматов
            if not self.is_valid_connection_format(out, inc):
                result["fixes_needed"].append({
                    "type": "invalid_connection_format",
                    "connection_index": i,
                    "connection_out": out,
                    "connection_in": inc
                })
            
            # Проверка существования элементов
            if out.startswith("a") and out not in action_ids:
                result["errors"].append(f"❌ Связь {i}: несуществующее действие: {out}")
            
            if inc.startswith("a") and inc not in action_ids:
                result["errors"].append(f"❌ Связь {i}: несуществующее действие: {inc}")
            
            # Проверка пропущенных действий
            if not out.startswith("a") and not inc.startswith("a"):
                result["fixes_needed"].append({
                    "type": "missing_action_in_connection",
                    "connection_index": i,
                    "connection": f"{out} → {inc}",
                    "message": "Связь должна содержать действие"
                })
        
        return result
    
    def suggest_action_name(self, current_name: str) -> str:
        """Предлагает полное название действия"""
        suggestions = {
            "регистрация": "Регистрация пользователя",
            "авторизация": "Авторизация пользователя",
            "настройка": "Настройка профиля",
            "ввод": "Ввод личных данных",
            "расчет": "Расчет нормы калорий",
            "генерация": "Генерация плана питания",
            "добавление": "Добавление рецепта",
            "создание": "Создание плана питания"
        }
        
        for key, suggestion in suggestions.items():
            if key in current_name.lower():
                return suggestion
        
        return f"{current_name} пользователя"
    
    def suggest_object_name(self, current_name: str) -> str:
        """Предлагает правильное название объекта"""
        suggestions = {
            "логин": "Сессия",
            "сервер": "Система",
            "клиент": "Пользователь",
            "план": "План питания"
        }
        
        for key, suggestion in suggestions.items():
            if key in current_name.lower():
                return suggestion
        
        return current_name
    
    def is_valid_connection_format(self, out: str, inc: str) -> bool:
        """Проверяет формат связи"""
        # Допустимые форматы:
        # - oXXXXXsXXXXX → aXXXXX (состояние → действие)
        # - aXXXXX → oXXXXXsXXXXX (действие → состояние)
        # - oXXXXXsXXXXX → oXXXXXsXXXXX (состояние → состояние) - НЕДОПУСТИМО без действия
        
        # Проверяем, что хотя бы один элемент - действие
        if not (out.startswith("a") or inc.startswith("a")):
            return False
        
        # Проверяем форматы ID
        if out.startswith("o") and "s" in out:
            if not re.match(r'^o\d{5}s\d{5}$', out):
                return False
        
        if inc.startswith("o") and "s" in inc:
            if not re.match(r'^o\d{5}s\d{5}$', inc):
                return False
        
        if out.startswith("a") and not re.match(r'^a\d{5}$', out):
            return False
        
        if inc.startswith("a") and not re.match(r'^a\d{5}$', inc):
            return False
        
        return True
    
    def fix_model(self, model: Dict) -> Tuple[Dict, List[str]]:
        """Исправляет модель и возвращает исправленную версию"""
        fixed_model = json.loads(json.dumps(model))  # Глубокая копия
        applied_fixes = []
        
        # Исправление действий
        if "model_actions" in fixed_model:
            for i, action in enumerate(fixed_model["model_actions"]):
                # Добавляем ID если нет
                if "action_id" not in action:
                    action["action_id"] = f"a{i+1:05d}"
                    applied_fixes.append(f"✅ Добавлен action_id для действия '{action.get('action_name', '?')}'")
                
                # Исправляем неполные названия
                if "action_name" in action and len(action["action_name"].split()) < 2:
                    suggested = self.suggest_action_name(action["action_name"])
                    if suggested != action["action_name"]:
                        old_name = action["action_name"]
                        action["action_name"] = suggested
                        applied_fixes.append(f"✅ Исправлено название действия: '{old_name}' → '{suggested}'")
                
                # Добавляем ссылки если нет
                if "action_links" not in action:
                    action["action_links"] = {"manual": "", "API": "", "UI": ""}
        
        # Исправление объектов
        if "model_objects" in fixed_model:
            for i, obj in enumerate(fixed_model["model_objects"]):
                # Добавляем ID если нет
                if "object_id" not in obj:
                    obj["object_id"] = f"o{i+1:05d}"
                    applied_fixes.append(f"✅ Добавлен object_id для объекта '{obj.get('object_name', '?')}'")
                
                # Исправляем семантические ошибки
                if "object_name" in obj:
                    current_name = obj["object_name"]
                    if current_name.lower() in ["логин", "сервер", "клиент"] and "пользователь" not in current_name.lower():
                        suggested = self.suggest_object_name(current_name)
                        if suggested != current_name:
                            obj["object_name"] = suggested
                            applied_fixes.append(f"✅ Исправлено название объекта: '{current_name}' → '{suggested}'")
                
                # Добавляем состояния если нет
                if "resource_state" not in obj:
                    obj["resource_state"] = []
                    applied_fixes.append(f"✅ Добавлен resource_state для объекта '{obj.get('object_name', '?')}'")
                
                # Исправляем ID состояний
                if "resource_state" in obj and isinstance(obj["resource_state"], list):
                    for j, state in enumerate(obj["resource_state"]):
                        if "state_id" not in state:
                            state["state_id"] = f"s{j+1:05d}"
                            applied_fixes.append(f"✅ Добавлен state_id для состояния объекта '{obj.get('object_name', '?')}'")
        
        # Исправление связей
        if "model_connections" in fixed_model:
            # Находим связи без действий
            for i, conn in enumerate(fixed_model["model_connections"]):
                if "connection_out" in conn and "connection_in" in conn:
                    out = conn["connection_out"]
                    inc = conn["connection_in"]
                    
                    # Если связь состояние → состояние, добавляем действие
                    if not out.startswith("a") and not inc.startswith("a"):
                        # Создаем новое действие
                        action_id = f"a{len(fixed_model.get('model_actions', [])) + 1:05d}"
                        action_name = "Действие"
                        
                        # Пытаемся определить тип действия из состояний
                        if "s00001" in out and "s00002" in inc:
                            action_name = "Регистрация пользователя"
                        elif "s00002" in out and "s00003" in inc:
                            action_name = "Авторизация пользователя"
                        
                        # Добавляем действие
                        fixed_model.setdefault("model_actions", []).append({
                            "action_id": action_id,
                            "action_name": action_name,
                            "action_links": {"manual": "", "API": "", "UI": ""}
                        })
                        
                        # Исправляем связь
                        conn["connection_in"] = action_id
                        fixed_model["model_connections"].append({
                            "connection_out": action_id,
                            "connection_in": inc
                        })
                        
                        applied_fixes.append(f"✅ Исправлена связь: добавлено действие '{action_name}' между {out} и {inc}")
        
        return fixed_model, applied_fixes
    
    def generate_report(self, model: Dict) -> str:
        """Генерирует отчет по модели"""
        analysis = self.analyze_model(model)
        
        report = []
        report.append("📊 ОТЧЕТ АНАЛИЗА МОДЕЛИ")
        report.append("=" * 50)
        
        if analysis["problems_found"] == 0:
            report.append("✅ Модель корректна, ошибок не обнаружено")
            return "\n".join(report)
        
        # Ошибки
        if analysis["errors"]:
            report.append("\n❌ КРИТИЧЕСКИЕ ОШИБКИ:")
            for error in analysis["errors"]:
                report.append(f"  • {error}")
        
        # Необходимые исправления
        if analysis["fixes_needed"]:
            report.append("\n🔧 НЕОБХОДИМЫЕ ИСПРАВЛЕНИЯ:")
            for fix in analysis["fixes_needed"]:
                if fix["type"] == "incomplete_action_name":
                    report.append(f"  • Неполное название действия: '{fix['current_name']}' → '{fix['suggested_name']}'")
                elif fix["type"] == "semantic_object_error":
                    report.append(f"  • Семантическая ошибка объекта: '{fix['current_name']}' → '{fix['suggested_name']}'")
                elif fix["type"] == "missing_action_in_connection":
                    report.append(f"  • Пропущено действие в связи: {fix['connection']}")
        
        # Предупреждения
        if analysis["warnings"]:
            report.append("\n⚠️ ПРЕДУПРЕЖДЕНИЯ:")
            for warning in analysis["warnings"]:
                report.append(f"  • {warning}")
        
        report.append(f"\n📈 Всего проблем: {analysis['problems_found']}")
        
        return "\n".join(report)

def main():
    """Основная функция"""
    # Пример некорректной модели
    incorrect_model = {
      "model_actions": [
        {
          "action_id": "a00001",
          "action_name": "Регистрация пользователя",
          "action_links": {
            "manual": "",
            "API": "",
            "UI": ""
          }
        },
        {
          "action_id": "a00002",
          "action_name": "Авторизация пользователя",
          "action_links": {
            "manual": "",
            "API": "",
            "UI": ""
          }
        }
      ],
      "model_objects": [
        {
          "object_id": "o00001",
          "object_name": "Пользователь",
          "resource_state": [
            {
              "state_id": "s00001",
              "state_name": "Незарегистрирован"
            },
            {
              "state_id": "s00002",
              "state_name": "Зарегистрирован"
            }
          ]
        },
        {
          "object_id": "o00002",
          "object_name": "Логин",
          "resource_state": [
            {
              "state_id": "s00001",
              "state_name": "Недавно авторизован"
            }
          ]
        }
      ],
      "model_connections": [
        {
          "connection_out": "o00001s00001",
          "connection_in": "o00001s00002"
        }
      ]
    }
    
    fixer = ModelAutoFixer()
    
    print("🧪 ТЕСТИРОВАНИЕ АВТОИСПРАВИТЕЛЯ")
    print("=" * 50)
    
    # Анализ модели
    print("\n🔍 АНАЛИЗ МОДЕЛИ:")
    print(fixer.generate_report(incorrect_model))
    
    # Исправление модели
    print("\n🛠️ ИСПРАВЛЕНИЕ МОДЕЛИ:")
    fixed_model, applied_fixes = fixer.fix_model(incorrect_model)
    
    for fix in applied_fixes:
        print(f"  {fix}")
    
    # Сохранение исправленной модели
    with open("auto_fixed_model.json", "w", encoding="utf-8") as f:
        json.dump(fixed_model, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Исправленная модель сохранена в auto_fixed_model.json")
    
    # Показываем исправленную модель
    print("\n📋 ИСПРАВЛЕННАЯ МОДЕЛЬ:")
    print(json.dumps(fixed_model, ensure_ascii=False, indent=2)[:500] + "...")

if __name__ == "__main__":
    main()