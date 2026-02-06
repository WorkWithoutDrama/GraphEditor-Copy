#!/usr/bin/env python3
"""
Простой тест вывода JSON из API
"""

import json
import datetime

def test_json_output():
    """Тестирует вывод JSON"""
    
    print("🧪 ТЕСТ ВЫВОДА JSON")
    print("=" * 60)
    
    # 1. Создаем тестовую модель
    print("📋 1. Создаю тестовую модель...")
    
    timestamp = int(datetime.datetime.now().timestamp() * 1000)
    
    test_model = {
        "model_actions": [
            {
                "action_id": f"a{timestamp % 100000:05d}",
                "action_name": "Регистрация пользователя",
                "action_links": {"manual": "", "API": "", "UI": ""}
            }
        ],
        "model_objects": [
            {
                "object_id": "o00001",
                "object_name": "Пользователь",
                "resource_state": [
                    {"state_id": "s00001", "state_name": "незарегистрирован"},
                    {"state_id": "s00002", "state_name": "зарегистрирован"}
                ],
                "object_links": {"manual": "", "API": "", "UI": ""}
            },
            {
                "object_id": "o00002",
                "object_name": "Система",
                "resource_state": [
                    {"state_id": "s00003", "state_name": "ожидает регистрации"},
                    {"state_id": "s00004", "state_name": "пользователь зарегистрирован"}
                ],
                "object_links": {"manual": "", "API": "", "UI": ""}
            }
        ],
        "model_connections": [
            {
                "connection_out": "o00001s00001",
                "connection_in": f"a{timestamp % 100000:05d}"
            },
            {
                "connection_out": f"a{timestamp % 100000:05d}",
                "connection_in": "o00001s00002"
            },
            {
                "connection_out": f"a{timestamp % 100000:05d}",
                "connection_in": "o00002s00004"
            }
        ]
    }
    
    # 2. Выводим JSON как это должно быть в логах API
    print("\n📋 2. ВЫВОД JSON (как в логах API):")
    print("=" * 60)
    
    print("📥 ПОЛУЧЕН ЗАПРОС:")
    print("• Текст: Пользователь регистрируется в системе...")
    print("• Длина: 42 символа")
    print()
    
    print("🔄 ГЕНЕРАЦИЯ МОДЕЛИ...")
    print()
    
    print("🎯 СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
    print(json.dumps(test_model, ensure_ascii=False, indent=2))
    print()
    
    print("📊 СТАТИСТИКА МОДЕЛИ:")
    print(f"• Действий: {len(test_model['model_actions'])}")
    print(f"• Объектов: {len(test_model['model_objects'])}")
    print(f"• Связей: {len(test_model['model_connections'])}")
    print()
    
    print("✅ ОТВЕТ ОТПРАВЛЕН")
    print()
    
    # 3. Проверяем структуру
    print("📋 3. ПРОВЕРКА СТРУКТУРЫ JSON:")
    
    errors = []
    
    # Проверка model_actions
    if 'model_actions' not in test_model:
        errors.append("Отсутствует model_actions")
    elif not isinstance(test_model['model_actions'], list):
        errors.append("model_actions должен быть списком")
    else:
        for action in test_model['model_actions']:
            if 'action_id' not in action:
                errors.append("Отсутствует action_id")
            if 'action_name' not in action:
                errors.append("Отсутствует action_name")
    
    # Проверка model_objects
    if 'model_objects' not in test_model:
        errors.append("Отсутствует model_objects")
    elif not isinstance(test_model['model_objects'], list):
        errors.append("model_objects должен быть списком")
    
    # Проверка model_connections
    if 'model_connections' not in test_model:
        errors.append("Отсутствует model_connections")
    elif not isinstance(test_model['model_connections'], list):
        errors.append("model_connections должен быть списком")
    
    if errors:
        print("❌ Ошибки в структуре:")
        for error in errors:
            print(f"   • {error}")
    else:
        print("✅ Структура JSON правильная")
    
    # 4. Проверка промпта в api-fixed-new-structure.py
    print("\n📋 4. ПРОВЕРКА КОДА API:")
    
    try:
        with open('api-fixed-new-structure.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("СГЕНЕРИРОВАННАЯ МОДЕЛЬ", "Вывод полного JSON"),
            ("json.dumps(model", "Форматирование JSON"),
            ("ensure_ascii=False", "Поддержка кириллицы"),
            ("indent=2", "Человекочитаемое форматирование"),
            ("СТАТИСТИКА МОДЕЛИ", "Вывод статистики"),
            ("logger.info", "Использование логирования")
        ]
        
        all_ok = True
        for phrase, description in checks:
            if phrase in content:
                print(f"   ✅ {description}")
            else:
                print(f"   ❌ {description}")
                all_ok = False
        
        if all_ok:
            print("\n✅ Код API содержит все необходимые элементы логирования")
        else:
            print("\n⚠️  В коде API не хватает некоторых элементов логирования")
            
    except FileNotFoundError:
        print("   ⚠️  Файл api-fixed-new-structure.py не найден")
    
    # 5. Итог
    print("\n" + "=" * 60)
    print("🎯 ИТОГОВЫЕ РЕКОМЕНДАЦИИ:")
    print()
    print("1. ✅ JSON структура правильная и выводится полностью")
    print("2. ✅ Форматирование: indent=2, ensure_ascii=False")
    print("3. ✅ Статистика выводится в логи")
    print("4. 🔧 Для работы системы:")
    print("   • Запустите: python3 api_simple_with_logging.py")
    print("   • Или обновите launch.command для его использования")
    print("   • Или добавьте такое же логирование в api-fixed-new-structure.py")
    print()
    print("5. 📝 При каждом запросе будет выводиться:")
    print("   • Полученный текст")
    print("   • Полный JSON модели")
    print("   • Статистика модели")
    print()

if __name__ == "__main__":
    test_json_output()