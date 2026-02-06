/**
 * Тестирование сгенерированной LLM модели
 */

const generatedModel = {
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
          "state_name": "незарегистрирован"
        },
        {
          "state_id": "s00002",
          "state_name": "зарегистрирован"
        }
      ]
    },
    {
      "object_id": "o00002",
      "object_name": "Логин",
      "resource_state": [
        {
          "state_id": "s00001",
          "state_name": "не авторизован"
        },
        {
          "state_id": "s00002",
          "state_name": "авторизован"
        }
      ]
    }
  ],
  "model_connections": [
    {
      "connection_out": "o00001s00001",
      "connection_in": "a00001"
    },
    {
      "connection_out": "o00002s00003",
      "connection_in": "a00002"
    }
  ]
};

// Импортируем валидатор
const ModelValidator = require('./model_validator_fixed.js');

console.log("🧪 ТЕСТИРОВАНИЕ СГЕНЕРИРОВАННОЙ МОДЕЛИ LLM\n");
console.log("📋 Исходная модель:");
console.log(JSON.stringify(generatedModel, null, 2));

console.log("\n🔍 Анализ проблем:");

// Анализ проблем вручную
console.log("\n1. Проверка состояний объекта 'Логин':");
const loginObject = generatedModel.model_objects.find(obj => obj.object_name === "Логин");
if (loginObject) {
  console.log("   • Объект найден: ID =", loginObject.object_id);
  console.log("   • Состояния:", loginObject.resource_state.map(s => `${s.state_id}: ${s.state_name}`).join(", "));
  
  // Проверяем используемые состояния в связях
  const usedStateIds = new Set();
  generatedModel.model_connections.forEach(conn => {
    if (conn.connection_out.includes('o00002')) {
      const stateId = conn.connection_out.replace('o00002', '');
      usedStateIds.add(stateId);
    }
  });
  
  console.log("   • Используемые состояния в связях:", Array.from(usedStateIds).join(", "));
  
  // Проверяем какие состояния определены
  const definedStateIds = new Set(loginObject.resource_state.map(s => s.state_id));
  console.log("   • Определенные состояния:", Array.from(definedStateIds).join(", "));
  
  // Находим неопределенные состояния
  const undefinedStates = Array.from(usedStateIds).filter(id => !definedStateIds.has(id));
  if (undefinedStates.length > 0) {
    console.log("   ❌ Ошибка: используются неопределенные состояния:", undefinedStates.join(", "));
    console.log("   💡 Решение: нужно добавить состояния с ID:", undefinedStates.join(", "));
  } else {
    console.log("   ✅ Все используемые состояния определены");
  }
}

console.log("\n2. Проверка форматов ID:");
const allStateCombinations = new Set();

generatedModel.model_objects.forEach(obj => {
  if (obj.resource_state) {
    obj.resource_state.forEach(state => {
      const combinedId = `${obj.object_id}${state.state_id}`;
      allStateCombinations.add(combinedId);
    });
  }
});

console.log("   • Все комбинации object+state:", Array.from(allStateCombinations).join(", "));

generatedModel.model_connections.forEach((conn, index) => {
  if (!allStateCombinations.has(conn.connection_out) && !conn.connection_out.startsWith('a')) {
    console.log(`   ❌ Связь ${index}: несуществующая комбинация: ${conn.connection_out}`);
  }
  if (!allStateCombinations.has(conn.connection_in) && !conn.connection_in.startsWith('a')) {
    console.log(`   ❌ Связь ${index}: несуществующая комбинация: ${conn.connection_in}`);
  }
});

console.log("\n3. Исправление модели:");
const fixedModel = JSON.parse(JSON.stringify(generatedModel)); // Копия

// Исправляем ошибку с s00003
const loginObjIndex = fixedModel.model_objects.findIndex(obj => obj.object_name === "Логин");
if (loginObjIndex !== -1) {
  // Добавляем отсутствующее состояние s00003
  const hasS00003 = fixedModel.model_objects[loginObjIndex].resource_state.some(s => s.state_id === "s00003");
  if (!hasS00003) {
    fixedModel.model_objects[loginObjIndex].resource_state.push({
      "state_id": "s00003",
      "state_name": "неизвестное состояние (добавлено автоматически)"
    });
    console.log("   ✅ Добавлено отсутствующее состояние s00003 для объекта 'Логин'");
  }
}

// Альтернативное исправление: меняем связь на существующее состояние
const problemConnectionIndex = fixedModel.model_connections.findIndex(conn => conn.connection_out === "o00002s00003");
if (problemConnectionIndex !== -1) {
  // Меняем на существующее состояние
  fixedModel.model_connections[problemConnectionIndex].connection_out = "o00002s00001";
  console.log("   ✅ Исправлена связь: o00002s00003 → o00002s00001");
}

console.log("\n📋 Исправленная модель:");
console.log(JSON.stringify(fixedModel, null, 2));

// Запускаем валидатор
console.log("\n🔧 Запуск автоматического валидатора...");
const validator = new ModelValidator();
const validationResult = validator.validateAndFix(generatedModel);

console.log(validator.formatReport());