/**
 * Валидатор и исправитель моделей, сгенерированных LLM
 * Исправляет ошибки в формате и непоследовательности
 */

class ModelValidator {
    constructor() {
        this.errors = [];
        this.warnings = [];
    }

    /**
     * Проверяет и исправляет модель
     * @param {Object} model - Модель для проверки
     * @returns {Object} - Исправленная модель
     */
    validateAndFix(model) {
        this.errors = [];
        this.warnings = [];

        // Базовые проверки структуры
        this.validateStructure(model);

        // Проверка и исправление форматов ID
        this.fixIDFormats(model);

        // Проверка и исправление состояний объектов
        this.fixObjectStates(model);

        // Проверка и исправление связей
        this.fixConnections(model);

        // Проверка на целостность
        this.checkIntegrity(model);

        return {
            model: model,
            valid: this.errors.length === 0,
            errors: this.errors,
            warnings: this.warnings
        };
    }

    /**
     * Проверяет базовую структуру модели
     */
    validateStructure(model) {
        if (!model) {
            this.errors.push("❌ Модель не определена или null");
            return;
        }

        const requiredArrays = ['model_actions', 'model_objects', 'model_connections'];
        
        for (const arrayName of requiredArrays) {
            if (!model[arrayName]) {
                this.errors.push(`❌ Отсутствует массив: ${arrayName}`);
            } else if (!Array.isArray(model[arrayName])) {
                this.errors.push(`❌ ${arrayName} должен быть массивом`);
            }
        }
    }

    /**
     * Исправляет форматы ID в модели
     */
    fixIDFormats(model) {
        // Исправление ID действий
        if (model.model_actions) {
            model.model_actions.forEach((action, index) => {
                if (!action.action_id) {
                    // Генерируем ID если его нет
                    const newId = `a${String(index + 1).padStart(5, '0')}`;
                    action.action_id = newId;
                    this.warnings.push(`⚠️ Действие "${action.action_name}": сгенерирован action_id: ${newId}`);
                } else if (!/^a\d{5}$/.test(action.action_id)) {
                    // Исправляем неправильный формат
                    const match = action.action_id.match(/a(\d+)/);
                    if (match) {
                        const num = match[1].padStart(5, '0');
                        const oldId = action.action_id;
                        action.action_id = `a${num}`;
                        this.warnings.push(`⚠️ Действие "${action.action_name}": исправлен action_id: ${oldId} -> ${action.action_id}`);
                    }
                }
            });
        }

        // Исправление ID объектов и состояний
        if (model.model_objects) {
            model.model_objects.forEach((obj, objIndex) => {
                if (!obj.object_id) {
                    // Генерируем ID если его нет
                    const newId = `o${String(objIndex + 1).padStart(5, '0')}`;
                    obj.object_id = newId;
                    this.warnings.push(`⚠️ Объект "${obj.object_name}": сгенерирован object_id: ${newId}`);
                } else if (!/^o\d{5}$/.test(obj.object_id)) {
                    // Исправляем неправильный формат
                    const match = obj.object_id.match(/o(\d+)/);
                    if (match) {
                        const num = match[1].padStart(5, '0');
                        const oldId = obj.object_id;
                        obj.object_id = `o${num}`;
                        this.warnings.push(`⚠️ Объект "${obj.object_name}": исправлен object_id: ${oldId} -> ${obj.object_id}`);
                    }
                }

                // Исправление ID состояний
                if (obj.resource_state && Array.isArray(obj.resource_state)) {
                    obj.resource_state.forEach((state, stateIndex) => {
                        if (!state.state_id) {
                            // Генерируем ID если его нет
                            const newId = `s${String(stateIndex + 1).padStart(5, '0')}`;
                            state.state_id = newId;
                            this.warnings.push(`⚠️ Объект "${obj.object_name}", состояние: сгенерирован state_id: ${newId}`);
                        } else if (!/^s\d{5}$/.test(state.state_id)) {
                            // Исправляем неправильный формат
                            const match = state.state_id.match(/s(\d+)/);
                            if (match) {
                                const num = match[1].padStart(5, '0');
                                const oldId = state.state_id;
                                state.state_id = `s${num}`;
                                this.warnings.push(`⚠️ Объект "${obj.object_name}", состояние: исправлен state_id: ${oldId} -> ${state.state_id}`);
                            }
                        }
                    });
                }
            });
        }
    }

    /**
     * Исправляет состояния объектов (проверяет уникальность)
     */
    fixObjectStates(model) {
        if (!model.model_objects) return;

        const allStateIds = new Map(); // Map для отслеживания использованных ID состояний

        model.model_objects.forEach((obj) => {
            if (!obj.resource_state || !Array.isArray(obj.resource_state)) {
                obj.resource_state = [];
                this.warnings.push(`⚠️ Объект "${obj.object_name}": добавлен пустой массив состояний`);
                return;
            }

            // Проверка уникальности состояний по ID в рамках объекта
            const stateIdsInObject = new Set();
            const duplicateStateNames = new Set();

            obj.resource_state.forEach((state) => {
                if (!state.state_id || !state.state_name) {
                    this.errors.push(`❌ Объект "${obj.object_name}": состояние без ID или названия`);
                    return;
                }

                // Проверяем уникальность state_id в рамках объекта
                if (stateIdsInObject.has(state.state_id)) {
                    this.errors.push(`❌ Объект "${obj.object_name}": дублирующийся state_id: ${state.state_id}`);
                } else {
                    stateIdsInObject.add(state.state_id);
                }

                // Проверяем уникальность state_name в рамках объекта
                if (duplicateStateNames.has(state.state_name)) {
                    this.warnings.push(`⚠️ Объект "${obj.object_name}": дублирующееся название состояния: ${state.state_name}`);
                } else {
                    duplicateStateNames.add(state.state_name);
                }

                // Проверяем глобальную уникальность комбинации object_id + state_id
                const combinedId = `${obj.object_id}${state.state_id}`;
                if (allStateIds.has(combinedId)) {
                    this.errors.push(`❌ Дублирующаяся комбинация object+state: ${combinedId}`);
                } else {
                    allStateIds.set(combinedId, {
                        object: obj.object_name,
                        state: state.state_name
                    });
                }
            });
        });
    }

    /**
     * Исправляет связи в модели
     */
    fixConnections(model) {
        if (!model.model_connections || !Array.isArray(model.model_connections)) {
            model.model_connections = [];
            this.warnings.push("⚠️ Добавлен пустой массив связей");
            return;
        }

        // Создаем карту существующих ID
        const existingActionIds = new Set();
        const existingStateCombinations = new Set();

        // Собираем существующие action_id
        if (model.model_actions) {
            model.model_actions.forEach(action => {
                if (action.action_id) {
                    existingActionIds.add(action.action_id);
                }
            });
        }

        // Собираем существующие комбинации object_id + state_id
        if (model.model_objects) {
            model.model_objects.forEach(obj => {
                if (obj.object_id && obj.resource_state) {
                    obj.resource_state.forEach(state => {
                        if (state.state_id) {
                            existingStateCombinations.add(`${obj.object_id}${state.state_id}`);
                        }
                    });
                }
            });
        }

        // Проверяем и исправляем связи
        model.model_connections.forEach((conn, index) => {
            if (!conn.connection_out || !conn.connection_in) {
                this.errors.push(`❌ Связь ${index}: отсутствует connection_out или connection_in`);
                return;
            }

            // Проверяем, является ли connection_out действием или состоянием
            if (conn.connection_out.startsWith('a')) {
                // Проверяем существование действия
                if (!existingActionIds.has(conn.connection_out)) {
                    this.errors.push(`❌ Связь ${index}: несуществующее действие: ${conn.connection_out}`);
                }
            } else if (conn.connection_out.includes('s')) {
                // Проверяем существование состояния
                if (!existingStateCombinations.has(conn.connection_out)) {
                    this.errors.push(`❌ Связь ${index}: несуществующее состояние: ${conn.connection_out}`);
                }
            }

            // Проверяем, является ли connection_in действием или состоянием
            if (conn.connection_in.startsWith('a')) {
                // Проверяем существование действия
                if (!existingActionIds.has(conn.connection_in)) {
                    this.errors.push(`❌ Связь ${index}: несуществующее действие: ${conn.connection_in}`);
                }
            } else if (conn.connection_in.includes('s')) {
                // Проверяем существование состояния
                if (!existingStateCombinations.has(conn.connection_in)) {
                    this.errors.push(`❌ Связь ${index}: несуществующее состояние: ${conn.connection_in}`);
                }
            }
        });
    }

    /**
     * Проверяет целостность модели
     */
    checkIntegrity(model) {
        // Проверяем, что все действия имеют уникальные ID
        const actionIds = new Set();
        if (model.model_actions) {
            model.model_actions.forEach((action, index) => {
                if (action.action_id) {
                    if (actionIds.has(action.action_id)) {
                        this.errors.push(`❌ Дублирующийся action_id: ${action.action_id} (действие: ${action.action_name})`);
                    } else {
                        actionIds.add(action.action_id);
                    }
                }
            });
        }

        // Проверяем, что все объекты имеют уникальные ID
        const objectIds = new Set();
        if (model.model_objects) {
            model.model_objects.forEach((obj, index) => {
                if (obj.object_id) {
                    if (objectIds.has(obj.object_id)) {
                        this.errors.push(`❌ Дублирующийся object_id: ${obj.object_id} (объект: ${obj.object_name})`);
                    } else {
                        objectIds.add(obj.object_id);
                    }
                }
            });
        }

        // Проверяем, что нет циклических связей
        this.checkForCycles(model);
    }

    /**
     * Проверяет наличие циклических связей
     */
    checkForCycles(model) {
        if (!model.model_connections) return;

        // Строим граф связей
        const graph = new Map();

        model.model_connections.forEach(conn => {
            if (!graph.has(conn.connection_out)) {
                graph.set(conn.connection_out, new Set());
            }
            graph.get(conn.connection_out).add(conn.connection_in);
        });

        // Проверяем наличие циклов с помощью DFS
        const visited = new Set();
        const recursionStack = new Set();

        const hasCycle = (node) => {
            if (!graph.has(node)) return false;

            if (recursionStack.has(node)) return true;
            if (visited.has(node)) return false;

            visited.add(node);
            recursionStack.add(node);

            const neighbors = graph.get(node);
            for (const neighbor of neighbors) {
                if (hasCycle(neighbor)) {
                    return true;
                }
            }

            recursionStack.delete(node);
            return false;
        };

        for (const node of graph.keys()) {
            if (hasCycle(node)) {
                this.warnings.push("⚠️ Обнаружены возможные циклические связи в модели");
                break;
            }
        }
    }

    /**
     * Форматирует отчет о проверке
     */
    formatReport() {
        let report = "📋 ОТЧЕТ О ПРОВЕРКЕ МОДЕЛИ\n\n";

        if (this.errors.length > 0) {
            report += "❌ ОШИБКИ:\n";
            this.errors.forEach(error => {
                report += `  • ${error}\n`;
            });
            report += "\n";
        } else {
            report += "✅ Ошибок не обнаружено\n\n";
        }

        if (this.warnings.length > 0) {
            report += "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n";
            this.warnings.forEach(warning => {
                report += `  • ${warning}\n`;
            });
        } else {
            report += "ℹ️ Предупреждений нет\n";
        }

        return report;
    }
}

// Пример использования
const exampleModel = {
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
      "connection_out": "o00002s00003",  // Ошибка: s00003 не существует
      "connection_in": "a00002"
    }
  ]
};

const validator = new ModelValidator();
const result = validator.validateAndFix(exampleModel);

console.log(validator.formatReport());
console.log("Исправленная модель:", JSON.stringify(result.model, null, 2));

module.exports = ModelValidator;