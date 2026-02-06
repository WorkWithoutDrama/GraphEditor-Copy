#!/usr/bin/env python3
"""
Генерация модели через API и вывод в консоль
"""

import json
import urllib.request
import urllib.error
import sys

def generate_and_print_model(text):
    """Генерирует модель и выводит её в консоль"""
    
    print("🚀 ЗАПУСК ГЕНЕРАЦИИ МОДЕЛИ")
    print("=" * 60)
    print(f"📝 Текст запроса: \"{text}\"")
    print()
    
    try:
        # Отправляем запрос к API
        url = "http://localhost:5005/api/generate-model"
        data = {
            "text": text,
            "provider": "ollama"
        }
        
        print("📤 Отправляю запрос к API...")
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                result = json.loads(response.read().decode('utf-8'))
                print(f"✅ Ответ получен (статус: {response.status})")
                print()
                
                # Проверяем успешность
                if result.get("success"):
                    print("🎉 ГЕНЕРАЦИЯ УСПЕШНА!")
                    print("=" * 60)
                    
                    # Получаем модель
                    model = result.get("model", {})
                    
                    # Выводим полную модель в консоль
                    print("📊 ПОЛНАЯ СГЕНЕРИРОВАННАЯ МОДЕЛЬ:")
                    print(json.dumps(model, ensure_ascii=False, indent=2))
                    print()
                    
                    # Выводим статистику
                    print("📈 СТАТИСТИКА МОДЕЛИ:")
                    print(f"   • Действий: {len(model.get('model_actions', []))}")
                    print(f"   • Объектов: {len(model.get('model_objects', []))}")
                    print(f"   • Связей: {len(model.get('model_connections', []))}")
                    print()
                    
                    # Выводим детали
                    print("🔍 ДЕТАЛИ МОДЕЛИ:")
                    
                    # Действия
                    if model.get('model_actions'):
                        print("\n   📋 ДЕЙСТВИЯ (прямоугольники):")
                        for action in model['model_actions']:
                            print(f"      • {action.get('action_name', 'Без названия')} (ID: {action.get('action_id', 'N/A')})")
                    
                    # Объекты
                    if model.get('model_objects'):
                        print("\n   🎯 ОБЪЕКТЫ (овалы):")
                        for obj in model['model_objects']:
                            print(f"      • {obj.get('object_name', 'Без названия')} (ID: {obj.get('object_id', 'N/A')})")
                            if obj.get('resource_state'):
                                for state in obj['resource_state']:
                                    if state.get('state_name') != 'null':
                                        print(f"        ◦ Состояние: {state.get('state_name', 'N/A')} (ID: {state.get('state_id', 'N/A')})")
                    
                    # Связи
                    if model.get('model_connections'):
                        print("\n   🔗 СВЯЗИ (стрелки):")
                        for conn in model['model_connections']:
                            source = conn.get('connection_out', 'N/A')
                            target = conn.get('connection_in', 'N/A')
                            print(f"      • {source} → {target}")
                    
                    print()
                    print("🎨 ПРАВИЛА ОТРИСОВКИ:")
                    print("   • Действия → прямоугольники")
                    print("   • Объект+состояние → овалы")
                    print("   • Стрелки: connection_in → connection_out")
                    
                else:
                    print("❌ Ошибка генерации:")
                    print(f"   {result.get('error', 'Неизвестная ошибка')}")
                    return False
                    
            else:
                print(f"❌ Ошибка API: {response.status}")
                print(f"   Ответ: {response.read().decode('utf-8')}")
                return False
                
    except urllib.error.URLError as e:
        print(f"❌ Ошибка сети: {e}")
        print("   Проверьте, запущен ли API сервер")
        return False
    except Exception as e:
        print(f"❌ Ошибка при генерации: {e}")
        return False
    
    return True

def main():
    """Основная функция"""
    
    # Тестовые запросы
    test_cases = [
        "Пользователь регистрируется в системе",
        "Оплата заказа через платежную систему",
        "Создание документа с заполнением полей"
    ]
    
    print("🧪 ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ МОДЕЛЕЙ")
    print("=" * 60)
    
    # Проверяем API
    try:
        print("🔍 Проверяю доступность API...")
        req = urllib.request.Request("http://localhost:5005/api/status")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                print("✅ API доступен")
            else:
                print("❌ API недоступен")
                return 1
    except Exception as e:
        print(f"❌ API недоступен: {e}")
        print("\n💡 Для запуска API выполните:")
        print("   python3 api-fixed-new-structure.py")
        return 1
    
    print()
    
    # Запускаем генерацию для каждого тестового случая
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"ТЕСТ {i}/{len(test_cases)}")
        print(f"{'='*60}")
        
        success = generate_and_print_model(test_text)
        
        if not success:
            print(f"\n⚠️  Тест {i} завершен с ошибкой")
        
        if i < len(test_cases):
            input("\n⏎ Нажмите Enter для следующего теста...")
    
    print("\n" + "=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())