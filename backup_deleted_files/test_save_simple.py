#!/usr/bin/env python3
"""
Простой тест исправленного сохранения
"""

import json

# Тестовый JSON который создается
created_json = {
    "model_actions": [
        {
            "action_id": "a00001",
            "action_name": "Регистрация по email",
            "action_links": {"manual": "", "API": "", "UI": ""}
        },
        {
            "action_id": "a00002",
            "action_name": "Авторизация и восстановление пароля",
            "action_links": {"manual": "", "API": "", "UI": ""}
        }
    ],
    "model_objects": [
        {
            "object_id": "o12345",
            "object_name": "Пользователь",
            "resource_state": [
                {"state_id": "s00000", "state_name": "null"},
                {"state_id": "s12345", "state_name": "зарегистрирован"}
            ],
            "object_links": {"manual": "", "API": "", "UI": ""}
        }
    ],
    "model_connections": [
        {
            "connection_out": "a00001",
            "connection_in": "o12345s12345"
        }
    ]
}

# JSON который сохраняется (проблемный)
saved_json = {
    "model_actions": [
        {
            "action_id": "a00001",
            "action_name": "Регистрация по email",
            "action_links": {"manual": "", "API": "", "UI": ""}
        },
        {
            "action_id": "a00002",
            "action_name": "Авторизация и восстановление пароля",
            "action_links": {"manual": "", "API": "", "UI": ""}
        }
    ],
    "model_objects": [],  # ПУСТО! Проблема
    "model_connections": []  # ПУСТО! Проблема
}

print("🔍 АНАЛИЗ ПРОБЛЕМЫ:")
print("=" * 60)

print("1. ✅ JSON который СОЗДАЕТСЯ:")
print(f"   • Действий: {len(created_json['model_actions'])}")
print(f"   • Объектов: {len(created_json['model_objects'])}")
print(f"   • Связей: {len(created_json['model_connections'])}")

print("\n2. ❌ JSON который СОХРАНЯЕТСЯ:")
print(f"   • Действий: {len(saved_json['model_actions'])}")
print(f"   • Объектов: {len(saved_json['model_objects'])} ← ПУСТО!")
print(f"   • Связей: {len(saved_json['model_connections'])} ← ПУСТО!")

print("\n3. 🎯 ПРИЧИНА ПРОБЛЕМЫ:")
print("   Функция сохранения создает НОВЫЕ ID вместо использования существующих:")
print("   - Действия: создает a00001, a00002 вместо использования исходных ID")
print("   - Объекты: не сохраняет объекты из сгенерированного JSON")
print("   - Связи: не сохраняет связи из сгенерированного JSON")

print("\n4. ✅ РЕШЕНИЕ:")
print("   Исправленная функция сохранения должна:")
print("   - Использовать ID узлов как есть (не создавать новые)")
print("   - Сохранять ВСЕ объекты из графа")
print("   - Сохранять ВСЕ связи из графа")
print("   - Для состояний создавать составные ID: object_id + state_id")

print("\n5. 📋 ИСПРАВЛЕННЫЙ КОД:")
print("""
document.getElementById('saveButton').addEventListener('click', () => {
    // 1. Сохраняем действия - используем ID узлов напрямую
    const actionNodes = cy.nodes('[type="action"]');
    actionNodes.forEach(node => {
        output.model_actions.push({
            action_id: node.id(),  // ← ИСПОЛЬЗУЕМ РЕАЛЬНЫЙ ID
            action_name: node.data('label'),
            action_links: {...}
        });
    });
    
    // 2. Сохраняем объекты и состояния
    const objectNodes = cy.nodes('[type="object"]');
    objectNodes.forEach(objectNode => {
        const objectId = objectNode.id();  // ← ИСПОЛЬЗУЕМ РЕАЛЬНЫЙ ID
        
        // Находим связанные состояния
        const resourceState = [];
        const connectedEdges = objectNode.connectedEdges();
        // ... собираем состояния
        
        output.model_objects.push({
            object_id: objectId,  // ← ИСПОЛЬЗУЕМ РЕАЛЬНЫЙ ID
            object_name: objectNode.data('label'),
            resource_state: resourceState,
            object_links: {...}
        });
    });
    
    // 3. Сохраняем связи
    const edges = cy.edges();
    edges.forEach(edge => {
        const sourceId = edge.source().id();  // ← ИСПОЛЬЗУЕМ РЕАЛЬНЫЕ ID
        const targetId = edge.target().id();  // ← ИСПОЛЬЗУЕМ РЕАЛЬНЫЕ ID
        
        // Для состояний создаем составные ID
        let finalTargetId = targetId;
        if (edge.target().data('type') === 'state') {
            // Находим родительский объект
            finalTargetId = parentObjectId + targetId;
        }
        
        output.model_connections.push({
            connection_out: sourceId,
            connection_in: finalTargetId
        });
    });
});
""")

print("\n6. 🚀 РЕКОМЕНДАЦИИ:")
print("   • Используйте script_fixed_save.js для замены функции сохранения")
print("   • Убедитесь, что узлы имеют правильные ID при загрузке JSON")
print("   • Проверьте, что связи правильно определяют тип (действие-объект, объект-состояние)")

# Сохраняем тестовые файлы
with open('created_json.json', 'w', encoding='utf-8') as f:
    json.dump(created_json, f, ensure_ascii=False, indent=2)

with open('saved_json.json', 'w', encoding='utf-8') as f:
    json.dump(saved_json, f, ensure_ascii=False, indent=2)

print("\n💾 Файлы сохранены:")
print("   • created_json.json - правильный JSON")
print("   • saved_json.json - проблемный JSON (пустые objects и connections)")
print("\n✅ Используйте script_fixed_save.js для исправления проблемы")