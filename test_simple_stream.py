#!/usr/bin/env python3
"""
Простой тест потокового анализа
"""

import sys
import os
import json

# Добавляем текущую директорию в путь
sys.path.append(".")

# Импортируем напрямую метод
import api_main

def test_stream_analysis():
    """Тестируем потоковый анализ"""
    print("🧪 ТЕСТ ПОТОКОВОГО АНАЛИЗА")
    print("=" * 50)
    
    # Читаем test_tz.txt
    with open("test_tz.txt", "r", encoding="utf-8") as f:
        text = f.read()
    
    paragraph_count = text.count("

") + 1
    print(f"📄 Длина ТЗ: {len(text)} символов")
    print(f"📋 Абзацев: {paragraph_count}")
    
    # Создаем экземпляр handler
    handler = api_main.TestAPIHandler(None, ("127.0.0.1", 8080), None)
    
    # Запускаем потоковый анализ
    try:
        result = handler.stream_text_analysis(text, "test_stream")
        
        print(f"✅ Анализ завершен!")
        print(f"📊 Результаты:")
        print(f"   • Действий: {len(result.get(\"model_actions\", []))}")
        print(f"   • Объектов: {len(result.get(\"model_objects\", []))}")
        print(f"   • Связей: {len(result.get(\"model_connections\", []))}")
        
        # Проверяем файл
        if os.path.exists("models/test_stream.json"):
            with open("models/test_stream.json", "r", encoding="utf-8") as f:
                model = json.load(f)
            print(f"💾 Файл сохранен: models/test_stream.json")
            print(f"📏 Размер: {os.path.getsize(\"models/test_stream.json\")} байт")
            print(f"🔄 Чанков обработано: {model.get(\"metadata\", {}).get(\"chunks_processed\", 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_models():
    """Показываем содержимое папки models"""
    print("
📁 СОДЕРЖИМОЕ ПАПКИ models/:")
    if os.path.exists("models"):
        for file in sorted(os.listdir("models")):
            if file.endswith(".json"):
                filepath = os.path.join("models", file)
                size = os.path.getsize(filepath)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    chunks = data.get("metadata", {}).get("chunks_processed", "?")
                    actions = len(data.get("model_actions", []))
                    print(f"   - {file} ({size} байт, {chunks} чанков, {actions} действий)")
                except:
                    print(f"   - {file} ({size} байт, ошибка чтения)")
    else:
        print("   Папка models/ не существует")

if __name__ == "__main__":
    # Создаем папку models если ее нет
    if not os.path.exists("models"):
        os.makedirs("models")
        print("📁 Создана папка models")
    
    print("🚀 ЗАПУСК ТЕСТА ПОТОКОВОГО АНАЛИЗА")
    print("=" * 60)
    
    # Запускаем тест
    success = test_stream_analysis()
    
    # Показываем результат
    print("
" + "=" * 60)
    if success:
        print("✅ ТЕСТ УСПЕШНО ЗАВЕРШЕН!")
    else:
        print("❌ ТЕСТ ЗАВЕРШИЛСЯ С ОШИБКАМИ")
    
    show_models()
