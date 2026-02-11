#!/usr/bin/env python3
"""
Тест потокового анализа ТЗ
"""

import sys
import os
import json

# Добавляем текущую директорию в путь
sys.path.append('.')

# Импортируем напрямую
import api_main

def create_test_handler():
    """Создает тестовый handler"""
    # Создаем минимальные mock объекты
    class MockRequest:
        pass
    
    class MockClientAddress:
        def __init__(self):
            self.host = '127.0.0.1'
            self.port = 8080
    
    class MockServer:
        pass
    
    # Создаем handler
    return api_main.TestAPIHandler(MockRequest(), MockClientAddress(), MockServer())

def test_basic():
    """Базовый тест"""
    print("🧪 БАЗОВЫЙ ТЕСТ ПОТОКОВОГО АНАЛИЗА")
    print("=" * 50)
    
    # Создаем handler
    handler = create_test_handler()
    
    # Простой тестовый текст
    text = """1. Создать систему
2. Добавить пользователей
3. Настроить права"""
    
    print(f"📏 Длина текста: {len(text)} символов")
    
    try:
        # Тестируем stream_text_analysis
        result = handler.stream_text_analysis(text, "test_basic")
        print(f"✅ Успех! Найдено действий: {len(result.get('model_actions', []))}")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_with_file():
    """Тест с файлом test_tz.txt"""
    print("\n🧪 ТЕСТ С ФАЙЛОМ test_tz.txt")
    print("=" * 50)
    
    # Читаем файл
    try:
        with open("test_tz.txt", "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print("❌ Файл test_tz.txt не найден")
        return False
    
    print(f"📄 Длина файла: {len(text)} символов")
    
    # Создаем handler
    handler = create_test_handler()
    
    try:
        # Запускаем потоковый анализ
        result = handler.stream_text_analysis(text, "system_tasks")
        
        print(f"✅ Анализ завершен!")
        print(f"📊 Результаты:")
        print(f"   • Действий: {len(result.get('model_actions', []))}")
        print(f"   • Объектов: {len(result.get('model_objects', []))}")
        print(f"   • Связей: {len(result.get('model_connections', []))}")
        
        # Проверяем сохранение
        if os.path.exists("models/system_tasks.json"):
            size = os.path.getsize("models/system_tasks.json")
            print(f"💾 Файл сохранен: models/system_tasks.json ({size} байт)")
            
            # Читаем и показываем метаданные
            with open("models/system_tasks.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            chunks = data.get("metadata", {}).get("chunks_processed", 0)
            print(f"🔄 Обработано чанков: {chunks}")
            
            # Показываем действия
            actions = data.get("model_actions", [])
            if actions:
                print(f"📝 Найденные действия:")
                for action in actions[:5]:  # Первые 5 действий
                    print(f"   - {action.get('action_name', '?')}")
                if len(actions) > 5:
                    print(f"   ... и еще {len(actions) - 5} действий")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_models_folder():
    """Показывает содержимое папки models"""
    print("\n📁 СОДЕРЖИМОЕ ПАПКИ models/:")
    if not os.path.exists("models"):
        print("   Папка не существует")
        return
    
    files = os.listdir("models")
    if not files:
        print("   Папка пуста")
        return
    
    for file in sorted(files):
        if file.endswith(".json"):
            filepath = os.path.join("models", file)
            size = os.path.getsize(filepath)
            print(f"   - {file} ({size} байт)")

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТОВ ПОТОКОВОГО АНАЛИЗА")
    print("=" * 60)
    
    # Создаем папку models если ее нет
    if not os.path.exists("models"):
        os.makedirs("models")
        print("📁 Создана папка models")
    
    # Запускаем тесты
    success1 = test_basic()
    success2 = test_with_file()
    
    # Показываем результаты
    print("\n" + "=" * 60)
    if success1 and success2:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
    
    # Показываем папку models
    show_models_folder()