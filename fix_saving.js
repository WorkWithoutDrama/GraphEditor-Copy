/**
 * Файл для исправления сохранения модели с правильными ID
 */

// Переопределяем функцию сохранения с правильными ID
document.getElementById('saveButton').addEventListener('click', function() {
    saveModelWithCorrectIDs();
});

function saveModelWithCorrectIDs() {
    let name = prompt("Имя проекта:", "model") || "project";
    
    const output = {
        model_actions: [],
        model_objects: [],
        model_connections: []
    };
    
    // 1. Сохраняем действия - генерируем правильные ID
    const actionNodes = cy.nodes('[type="action"]');
    let actionIdCounter = 1;
    
    actionNodes.forEach(node => {
        // Используем правильный ID: a00001, a00002, etc
        const actionId = `a${actionIdCounter.toString().padStart(5, '0')}`;
        actionIdCounter++;
        
        // Сохраняем оригинальное имя из данных или метки
        const actionName = node.data('original_name') || node.data('label') || `Действие ${actionId}`;
        
        output.model_actions.push({
            action_id: actionId,
            action_name: actionName,
            action_links: {
                manual: "",
                API: "", 
                UI: ""
            }
        });
        
        // Сохраняем маппинг старый ID -> новый ID
        node.data('corrected_id', actionId);
    });
    
    // 2. Сохраняем объекты и их состояния - генерируем правильные ID
    const stateNodes = cy.nodes('[type="state"]');
    let objectIdCounter = 1;
    let stateIdCounter = 1;
    
    // Группируем состояния по объектам
    const objectMap = new Map(); // object_id -> {object_name, states: []}
    
    stateNodes.forEach(stateNode => {
        const nodeId = stateNode.id();
        const label = stateNode.data('label') || `Состояние ${nodeId}`;
        
        // Извлекаем данные из узла или парсим из label
        let objectName = stateNode.data('object_name');
        let stateName = stateNode.data('state_name');
        let objectId = stateNode.data('object_id');
        let stateId = stateNode.data('state_id');
        
        if (!objectName || !stateName) {
            // Парсим из label: "Объект: Состояние"
            if (label.includes(':')) {
                const parts = label.split(':');
                objectName = parts[0].trim();
                stateName = parts[1].trim();
            } else {
                objectName = label;
                stateName = "состояние";
            }
        }
        
        // Генерируем правильные ID если их нет
        if (!objectId) {
            objectId = `o${objectIdCounter.toString().padStart(5, '0')}`;
            objectIdCounter++;
        }
        
        if (!stateId) {
            stateId = `s${stateIdCounter.toString().padStart(5, '0')}`;
            stateIdCounter++;
        }
        
        // Добавляем в карту объектов
        if (!objectMap.has(objectId)) {
            objectMap.set(objectId, {
                object_id: objectId,
                object_name: objectName,
                resource_state: []
            });
        }
        
        const obj = objectMap.get(objectId);
        obj.resource_state.push({
            state_id: stateId,
            state_name: stateName
        });
        
        // Сохраняем составной ID для узла
        const fullStateId = `${objectId}${stateId}`;
        stateNode.data('corrected_id', fullStateId);
        stateNode.data('object_id', objectId);
        stateNode.data('state_id', stateId);
        stateNode.data('object_name', objectName);
        stateNode.data('state_name', stateName);
    });
    
    // Сохраняем объекты
    objectMap.forEach(obj => {
        output.model_objects.push({
            object_id: obj.object_id,
            object_name: obj.object_name,
            resource_state: obj.resource_state,
            object_links: {
                manual: "",
                API: "",
                UI: ""
            }
        });
    });
    
    // 3. Сохраняем связи - используем исправленные ID
    const edges = cy.edges();
    
    edges.forEach(edge => {
        let sourceId = edge.source().id();
        let targetId = edge.target().id();
        
        // Используем исправленные ID если есть
        const sourceNode = edge.source();
        const targetNode = edge.target();
        
        if (sourceNode.data('corrected_id')) {
            sourceId = sourceNode.data('corrected_id');
        }
        
        if (targetNode.data('corrected_id')) {
            targetId = targetNode.data('corrected_id');
        }
        
        // Для узлов состояния проверяем, нужно ли добавить state_id
        if (targetNode.data('type') === 'state') {
            const objectId = targetNode.data('object_id');
            const stateId = targetNode.data('state_id');
            if (objectId && stateId) {
                // Проверяем, не является ли это уже составным ID
                if (!targetId.includes('s')) {
                    targetId = `${objectId}${stateId}`;
                }
            }
        }
        
        output.model_connections.push({
            connection_out: sourceId,
            connection_in: targetId
        });
    });
    
    // 4. Создаем и скачиваем файл
    const jsonStr = JSON.stringify(output, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log('💾 Сохранено с правильными ID:', output);
    console.log(`✅ Действий: ${output.model_actions.length}`);
    console.log(`✅ Объектов: ${output.model_objects.length}`);
    console.log(`✅ Связей: ${output.model_connections.length}`);
    
    // Показываем результат
    alert(`Модель сохранена как ${name}.json\n\n` +
          `Действий: ${output.model_actions.length}\n` +
          `Объектов: ${output.model_objects.length}\n` +
          `Связей: ${output.model_connections.length}\n\n` +
          `ID исправлены на правильный формат: a00001, o00001s00001`);
}

// Также переопределяем обработчики для добавления с правильными ID
document.getElementById('addActionButton').addEventListener('click', function() {
    addActionWithCorrectID();
});

document.getElementById('addStateButton').addEventListener('click', function() {
    addObjectWithStateWithCorrectID();
});

// Счетчики
let actionCounter = 1;
let objectCounter = 1;
let stateCounter = 1;

function addActionWithCorrectID() {
    const actionName = prompt("Имя действия:");
    if (!actionName) return;
    
    const actionId = `a${actionCounter.toString().padStart(5, '0')}`;
    actionCounter++;
    
    cy.add({ 
        group: 'nodes', 
        data: { 
            id: actionId, 
            label: actionName, 
            type: 'action',
            original_name: actionName,
            corrected_id: actionId
        }, 
        position: { x: Math.random() * 400, y: Math.random() * 300 } 
    });
    
    console.log(`➕ Добавлено действие: ${actionId} (${actionName})`);
}

function addObjectWithStateWithCorrectID() {
    const objectName = prompt("Имя объекта:");
    if (!objectName) return;
    
    const stateName = prompt("Состояние объекта:", "неактивен");
    if (!stateName) return;
    
    const objectId = `o${objectCounter.toString().padStart(5, '0')}`;
    const stateId = `s${stateCounter.toString().padStart(5, '0')}`;
    const fullStateId = `${objectId}${stateId}`;
    
    objectCounter++;
    stateCounter++;
    
    cy.add({ 
        group: 'nodes', 
        data: { 
            id: fullStateId, 
            label: `${objectName}: ${stateName}`, 
            type: 'state',
            object_id: objectId,
            object_name: objectName,
            state_id: stateId,
            state_name: stateName,
            corrected_id: fullStateId
        }, 
        position: { x: Math.random() * 400, y: Math.random() * 300 + 200 } 
    });
    
    console.log(`➕ Добавлен объект+состояние: ${objectId} (${objectName}) - ${stateId} (${stateName})`);
}