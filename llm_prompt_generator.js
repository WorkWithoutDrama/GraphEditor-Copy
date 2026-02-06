/**
 * Генератор промптов для LLM
 * Формирует структурированные промпты для генерации моделей из ТЗ
 */

class LLMPromptGenerator {
    constructor() {
        this.promptTemplate = `Ты - аналитик процессов. Твоя задача - проанализировать техническое задание и создать формализованную модель процессов.

АНАЛИЗИРУЙ следующее техническое задание:

[[TEXT]]

ИНСТРУКЦИИ ПО АНАЛИЗУ:

1. ИДЕНТИФИЦИРУЙ ДЕЙСТВИЯ:
   - Найдите все ключевые действия/процессы в ТЗ
   - Каждое действие должно иметь уникальный ID в формате "a" + 5 цифр (например: a00001)
   - Название действия должно кратко описывать процесс

2. ИДЕНТИФИЦИРУЙ ОБЪЕКТЫ И ИХ СОСТОЯНИЯ:
   - Найдите все объекты системы (сущности, ресурсы)
   - Для каждого объекта определите возможные состояния
   - Каждый объект должен иметь уникальный ID в формате "o" + 5 цифр (например: o00001)
   - Каждое состояние должно иметь уникальный ID в формате "s" + 5 цифр (например: s00001)
   - Объект+состояние представляется как единое целое (например: "Пользователь: неактивен")

3. ОПРЕДЕЛИ СВЯЗИ:
   - Для каждого действия найдите:
     * Какие объекты в каких состояниях необходимы для выполнения действия (начальные условия)
     * В какие состояния переходят объекты после выполнения действия (конечные условия)
   - Связи имеют формат: "объект+состояние" → "действие" → "объект+состояние"
   - connection_out - ID источника (начальное состояние или действие)
   - connection_in - ID цели (действие или конечное состояние)

4. ФОРМАТ ВЫВОДА:
   - Выведи ТОЛЬКО валидный JSON без дополнительного текста
   - JSON должен содержать три массива: model_actions, model_objects, model_connections
   - Все ID должны быть в правильном формате
   - Если объекта/действия/состояния нет в модели - добавь его

5. ПРИМЕР ДЛЯ ТЗ "Регистрация пользователя":
   - Действие: "Регистрация пользователя" (a00001)
   - Объект: "Пользователь" (o00001) с состояниями: "незарегистрирован" (s00001), "зарегистрирован" (s00002)
   - Связь: o00001s00001 → a00001 → o00001s00002

ВЕРНИ ТОЛЬКО JSON ОТВЕТ:`;
    }

    /**
     * Генерирует промпт для LLM на основе текста ТЗ
     * @param {string} text - Текст технического задания
     * @returns {string} - Полный промпт для LLM
     */
    generatePrompt(text) {
        return this.promptTemplate.replace('[[TEXT]]', text);
    }

    /**
     * Генерирует промпт с примером для обучения LLM
     * @param {string} text - Текст ТЗ
     * @param {Object} example - Пример правильного ответа
     * @returns {string} - Промпт с примером
     */
    generatePromptWithExample(text, example = null) {
        let prompt = this.promptTemplate.replace('[[TEXT]]', text);
        
        if (example) {
            prompt += '\n\nПРИМЕР ПРАВИЛЬНОГО ОТВЕТА:\n';
            prompt += JSON.stringify(example, null, 2);
            prompt += '\n\nНА ОСНОВЕ ВЫШЕПРИВЕДЕННОГО ПРИМЕРА, ПРОАНАЛИЗИРУЙ ТЗ И ВЕРНИ JSON:';
        }
        
        return prompt;
    }

    /**
     * Генерирует промпт для конкретного типа ТЗ
     * @param {string} text - Текст ТЗ
     * @param {string} domain - Домен (например: "веб-приложение", "бизнес-процесс", "IoT")
     * @returns {string} - Специализированный промпт
     */
    generateDomainSpecificPrompt(text, domain = "веб-приложение") {
        const domainSpecificInstructions = this.getDomainInstructions(domain);
        
        let prompt = `Ты - аналитик процессов со специализацией в области "${domain}". `;
        prompt += `Твоя задача - проанализировать техническое задание и создать формализованную модель процессов.\n\n`;
        prompt += `АНАЛИЗИРУЙ следующее техническое задание (домен: ${domain}):\n\n`;
        prompt += `[[TEXT]]\n\n`;
        prompt += domainSpecificInstructions;
        prompt += `\n\nВЕРНИ ТОЛЬКО JSON ОТВЕТ:`;
        
        return prompt.replace('[[TEXT]]', text);
    }

    /**
     * Получает доменно-специфичные инструкции
     * @param {string} domain - Домен
     * @returns {string} - Инструкции
     */
    getDomainInstructions(domain) {
        const instructions = {
            "веб-приложение": `ОСОБЕННОСТИ АНАЛИЗА ВЕБ-ПРИЛОЖЕНИЙ:
1. ОБЪЕКТЫ ВЕБ-ПРИЛОЖЕНИЙ:
   - Пользователь (состояния: неавторизован, авторизован, заблокирован)
   - Сессия (состояния: активна, истекла)
   - Данные (состояния: несохранены, сохранены, проверены)
   - Интерфейс (состояния: загружается, отображается, скрыт)

2. ТИПИЧНЫЕ ДЕЙСТВИЯ:
   - Авторизация/регистрация
   - CRUD операции (создание, чтение, обновление, удаление)
   - Валидация данных
   - Навигация по интерфейсу

3. СПЕЦИФИЧНЫЕ СВЯЗИ:
   - Пользователь → Действие → Данные
   - Интерфейс → Действие → Состояние интерфейса`,

            "бизнес-процесс": `ОСОБЕННОСТИ АНАЛИЗА БИЗНЕС-ПРОЦЕССОВ:
1. ОБЪЕКТЫ БИЗНЕС-ПРОЦЕССОВ:
   - Заказ (состояния: создан, в обработке, выполнен, отменен)
   - Платеж (состояния: ожидает, проведен, отклонен)
   - Товар (состояния: на складе, резервируется, продан)
   - Клиент (состояния: новый, постоянный, неактивный)

2. ТИПИЧНЫЕ ДЕЙСТВИЯ:
   - Создание заказа
   - Обработка платежа
   - Отгрузка товара
   - Обслуживание клиента

3. СПЕЦИФИЧНЫЕ СВЯЗИ:
   - Клиент → Создание заказа → Заказ
   - Заказ → Обработка → Платеж`,

            "iot": `ОСОБЕННОСТИ АНАЛИЗА IoT СИСТЕМ:
1. ОБЪЕКТЫ IoT:
   - Устройство (состояния: выключено, активно, спит, ошибка)
   - Данные сенсоров (состояния: невалидны, валидны, обрабатываются)
   - Команда (состояния: отправлена, выполнена, отклонена)

2. ТИПИЧНЫЕ ДЕЙСТВИЯ:
   - Сбор данных
   - Отправка команд
   - Обработка событий
   - Диагностика

3. СПЕЦИФИЧНЫЕ СВЯЗИ:
   - Устройство → Сбор данных → Данные
   - Команда → Исполнение → Состояние устройства`
        };

        return instructions[domain] || instructions["веб-приложение"];
    }

    /**
     * Валидирует ответ LLM
     * @param {string} response - Ответ от LLM
     * @returns {Object|null} - Парсированный JSON или null при ошибке
     */
    validateResponse(response) {
        try {
            // Пытаемся найти JSON в ответе (LLM может добавить текст вокруг)
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (!jsonMatch) {
                console.error('❌ Не найден JSON в ответе LLM');
                return null;
            }

            const parsed = JSON.parse(jsonMatch[0]);
            
            // Базовая валидация структуры
            if (!parsed.model_actions || !Array.isArray(parsed.model_actions)) {
                console.error('❌ Отсутствует или некорректен массив model_actions');
                return null;
            }
            
            if (!parsed.model_objects || !Array.isArray(parsed.model_objects)) {
                console.error('❌ Отсутствует или некорректен массив model_objects');
                return null;
            }
            
            if (!parsed.model_connections || !Array.isArray(parsed.model_connections)) {
                console.error('❌ Отсутствует или некорректен массив model_connections');
                return null;
            }

            // Валидация форматов ID
            const validationResult = this.validateIDs(parsed);
            if (!validationResult.valid) {
                console.error('❌ Ошибки валидации ID:', validationResult.errors);
                return null;
            }

            console.log('✅ Ответ LLM прошел валидацию');
            return parsed;

        } catch (error) {
            console.error('❌ Ошибка парсинга ответа LLM:', error);
            return null;
        }
    }

    /**
     * Валидирует форматы ID в модели
     * @param {Object} model - Модель для валидации
     * @returns {Object} - Результат валидации
     */
    validateIDs(model) {
        const errors = [];
        const actionIds = new Set();
        const objectIds = new Set();
        const stateIds = new Set();
        const combinedIds = new Set();

        // Валидация действий
        model.model_actions.forEach((action, index) => {
            if (!action.action_id) {
                errors.push(`Действие ${index}: отсутствует action_id`);
            } else if (!/^a\d{5}$/.test(action.action_id)) {
                errors.push(`Действие ${index}: неверный формат action_id: ${action.action_id}`);
            } else if (actionIds.has(action.action_id)) {
                errors.push(`Действие ${index}: дублирующийся action_id: ${action.action_id}`);
            } else {
                actionIds.add(action.action_id);
            }
        });

        // Валидация объектов и состояний
        model.model_objects.forEach((obj, objIndex) => {
            if (!obj.object_id) {
                errors.push(`Объект ${objIndex}: отсутствует object_id`);
            } else if (!/^o\d{5}$/.test(obj.object_id)) {
                errors.push(`Объект ${objIndex}: неверный формат object_id: ${obj.object_id}`);
            } else if (objectIds.has(obj.object_id)) {
                errors.push(`Объект ${objIndex}: дублирующийся object_id: ${obj.object_id}`);
            } else {
                objectIds.add(obj.object_id);
            }

            if (obj.resource_state && Array.isArray(obj.resource_state)) {
                obj.resource_state.forEach((state, stateIndex) => {
                    if (!state.state_id) {
                        errors.push(`Объект ${objIndex}, состояние ${stateIndex}: отсутствует state_id`);
                    } else if (!/^s\d{5}$/.test(state.state_id)) {
                        errors.push(`Объект ${objIndex}, состояние ${stateIndex}: неверный формат state_id: ${state.state_id}`);
                    } else {
                        const combinedId = `${obj.object_id}${state.state_id}`;
                        if (combinedIds.has(combinedId)) {
                            errors.push(`Дублирующееся состояние: ${combinedId}`);
                        } else {
                            combinedIds.add(combinedId);
                        }
                    }
                });
            }
        });

        // Валидация связей
        model.model_connections.forEach((conn, index) => {
            if (!conn.connection_out) {
                errors.push(`Связь ${index}: отсутствует connection_out`);
            }
            if (!conn.connection_in) {
                errors.push(`Связь ${index}: отсутствует connection_in`);
            }
        });

        return {
            valid: errors.length === 0,
            errors: errors
        };
    }

    /**
     * Создает пример правильного ответа на основе простого ТЗ
     * @returns {Object} - Пример модели
     */
    createExampleModel() {
        return {
            model_actions: [
                {
                    action_id: "a00001",
                    action_name: "Регистрация пользователя",
                    action_links: {
                        manual: "",
                        API: "",
                        UI: ""
                    }
                },
                {
                    action_id: "a00002",
                    action_name: "Авторизация пользователя",
                    action_links: {
                        manual: "",
                        API: "",
                        UI: ""
                    }
                }
            ],
            model_objects: [
                {
                    object_id: "o00001",
                    object_name: "Пользователь",
                    resource_state: [
                        { state_id: "s00001", state_name: "незарегистрирован" },
                        { state_id: "s00002", state_name: "зарегистрирован" },
                        { state_id: "s00003", state_name: "авторизован" }
                    ]
                },
                {
                    object_id: "o00002",
                    object_name: "Сессия",
                    resource_state: [
                        { state_id: "s00004", state_name: "неактивна" },
                        { state_id: "s00005", state_name: "активна" }
                    ]
                }
            ],
            model_connections: [
                {
                    connection_out: "o00001s00001",
                    connection_in: "a00001",
                    connection_label: "инициирует регистрацию"
                },
                {
                    connection_out: "a00001",
                    connection_in: "o00001s00002",
                    connection_label: "создает пользователя"
                },
                {
                    connection_out: "o00001s00002",
                    connection_in: "a00002",
                    connection_label: "запрашивает авторизацию"
                },
                {
                    connection_out: "a00002",
                    connection_in: "o00001s00003",
                    connection_label: "авторизует пользователя"
                },
                {
                    connection_out: "a00002",
                    connection_in: "o00002s00005",
                    connection_label: "создает сессию"
                }
            ]
        };
    }
}

// Экспорт для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LLMPromptGenerator;
} else {
    window.LLMPromptGenerator = LLMPromptGenerator;
}