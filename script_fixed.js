let cy;
let selectionOrder = []; // Очередь выбора узлов
let graphManager;

// Счетчики для генерации ID
let actionCounter = 1;
let objectCounter = 1;
let stateCounter = 1;

window.addEventListener('DOMContentLoaded', () => {
    renderGraph({ nodes: [], edges: [] });
    // Инициализируем GraphManager
    graphManager = new GraphManager();
});

function renderGraph(elements) {
    if (cy) cy.destroy();
    cy = cytoscape({
        container: document.getElementById('cy'),
        elements: elements,
        style: [
            { selector: 'node', style: {
                'label': 'data(label)',
                'text-valign': 'center',
                'text-halign': 'center',
                'text-wrap': 'wrap',
                'text-max-width': '180px',
                'font-size': '14px',
                'font-family': 'Arial, sans-serif',
                'line-height': 1.4,
                'padding': '12px',
                'border-width': 2,
                'border-color': '#007bff',
                'background-color': '#fff',
                'color': '#333'
            } },
            { selector: 'node[type="action"]', style: {
                'shape': 'rectangle',
                'background-color': '#e6f7ff',
                'border-color': '#1890ff',
                'width': '180px',
                'height': '60px',
                'text-wrap': 'wrap',
                'text-max-width': '200px',
                'padding': '10px',
                'min-width': '80px',
                'min-height': '40px',
                'font-size': '13px',
                'font-weight': '500'
            } },
            { selector: 'node[type="state"]', style: {
                'shape': 'ellipse',
                'background-color': '#f6ffed',
                'border-color': '#52c41a',
                'width': '160px',
                'height': '70px',
                'text-wrap': 'wrap',
                'text-max-width': '160px',
                'padding': '12px',
                'min-width': '70px',
                'min-height': '70px',
                'font-size': '13px'
            } },
            { selector: 'edge', style: {
                'width': 3,
                'line-color': '#666',
                'target-arrow-shape': 'triangle',
                'target-arrow-color': '#666',
                'target-arrow-fill': 'filled',
                'curve-style': 'bezier',
                'arrow-scale': 1.5
            } },
            { selector: ':selected', style: {
                'border-width': 4,
                'border-color': '#ffc107'
            } }
        ],
        layout: { name: 'dagre', rankDir: 'TB' }
    });

    // Отслеживание порядка выбора
    cy.on('select', 'node', function(evt){
        const id = evt.target.id();
        if (!selectionOrder.includes(id)) selectionOrder.push(id);
    });

    cy.on('unselect', 'node', function(evt){
        const id = evt.target.id();
        selectionOrder = selectionOrder.filter(item => item !== id);
    });
}

// Логика кнопки связи по порядку нажатия
document.getElementById('addLinkButton').addEventListener('click', () => {
    if (selectionOrder.length < 2) {
        alert("Выберите сначала узел-источник, а затем узел-цель.");
        return;
    }

    const sourceId = selectionOrder[0];
    const targetId = selectionOrder[1];

    const sourceNode = cy.getElementById(sourceId);
    const targetNode = cy.getElementById(targetId);

    // Валидация типов (Объект <-> Действие)
    if (sourceNode.data('type') === targetNode.data('type')) {
        alert("Нельзя связывать узлы одного типа (нужно: Объект -> Действие или Действие -> Объект).");
    } else {
        const edgeId = `${sourceId}->${targetId}`;
        if (cy.getElementById(edgeId).length === 0) {
            cy.add({ group: 'edges', data: { id: edgeId, source: sourceId, target: targetId } });
        }
    }

    // Очистка выбора
    cy.elements().unselect();
    selectionOrder = [];
});

// Функция для добавления действия с правильным ID
document.getElementById('addActionButton').addEventListener('click', () => {
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
            original_name: actionName
        }, 
        position: { x: Math.random() * 400, y: Math.random() * 300 } 
    });

    console.log(`➕ Добавлено действие: ${actionId} (${actionName})`);
});

// Функция для добавления объекта с состоянием
document.getElementById('addStateButton').addEventListener('click', () => {
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
            state_name: stateName
        }, 
        position: { x: Math.random() * 400, y: Math.random() * 300 + 200 } 
    });

    console.log(`➕ Добавлен объект+состояние: ${objectId} (${objectName}) - ${stateId} (${stateName})`);
});

// Функция сохранения с правильными ID
document.getElementById('saveButton').addEventListener('click', () => {
    let name = prompt("Имя проекта:", "model") || "project";

    const output = {
        model_actions: [],
        model_objects: [],
        model_connections: []
    };

    // 1. Сохраняем действия
    const actionNodes = cy.nodes('[type="action"]');
    let actionIdCounter = 1;
    const actionIdMap = new Map(); // старый ID -> новый ID
    
    actionNodes.forEach(node => {
        const oldId = node.id();
        const newId = `a${actionIdCounter.toString().padStart(5, '0')}`;
        actionIdCounter++;
        
        actionIdMap.set(oldId, newId);
        
        output.model_actions.push({
            action_id: newId,
            action_name: node.data('label') || node.data('original_name') || `Действие ${newId}`,
            action_links: {
                manual: "",
                API: "",
                UI: ""
            }
        });
    });
    
    // 2. Сохраняем объекты и состояния
    const stateNodes = cy.nodes('[type="state"]');
    let objectIdCounter = 1;
    let stateIdCounter = 1;
    const objectStateMap = new Map(); // object_id -> {object_name, states: []}
    const stateIdMap = new Map(); // старый ID -> новый составной ID
    
    stateNodes.forEach(stateNode => {
        const oldId = stateNode.id();
        
        // Извлекаем данные из узла
        let objectName = stateNode.data('object_name');
        let stateName = stateNode.data('state_name');
        let existingObjectId = stateNode.data('object_id');
        let existingStateId = stateNode.data('state_id');
        
        // Если данных нет, парсим из label
        if (!objectName || !stateName) {
            const label = stateNode.data('label') || `Состояние ${oldId}`;
            if (label.includes(':')) {
                const parts = label.split(':');
                objectName = parts[0].trim();
                stateName = parts[1].trim();
            } else {
                objectName = label;
                stateName = "состояние";
            }
        }
        
        // Генерируем или используем существующие ID
        const objectId = existingObjectId || `o${objectIdCounter.toString().padStart(5, '0')}`;
        const stateId = existingStateId || `s${stateIdCounter.toString().padStart(5, '0')}`;
        const fullStateId = `${objectId}${stateId}`;
        
        if (!existingObjectId) objectIdCounter++;
        if (!existingStateId) stateIdCounter++;
        
        stateIdMap.set(oldId, fullStateId);
        
        // Добавляем в карту объектов
        if (!objectStateMap.has(objectId)) {
            objectStateMap.set(objectId, {
                object_id: objectId,
                object_name: objectName,
                resource_state: []
            });
        }
        
        const obj = objectStateMap.get(objectId);
        obj.resource_state.push({
            state_id: stateId,
            state_name: stateName
        });
    });
    
    // Сохраняем объекты
    objectStateMap.forEach(obj => {
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
    
    // 3. Сохраняем связи
    const edges = cy.edges();
    
    edges.forEach(edge => {
        let sourceId = edge.source().id();
        let targetId = edge.target().id();
        
        // Заменяем ID на правильные
        if (actionIdMap.has(sourceId)) sourceId = actionIdMap.get(sourceId);
        if (actionIdMap.has(targetId)) targetId = actionIdMap.get(targetId);
        
        if (stateIdMap.has(sourceId)) sourceId = stateIdMap.get(sourceId);
        if (stateIdMap.has(targetId)) targetId = stateIdMap.get(targetId);
        
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
          `Связей: ${output.model_connections.length}`);
});

// Остальные обработчики
document.getElementById('deleteSelectedButton').addEventListener('click', () => cy.elements(':selected').remove());
document.getElementById('runLayoutButton').addEventListener('click', () => cy.layout({ name: 'dagre', rankDir: 'TB' }).run());
document.getElementById('removeLinkButton').addEventListener('click', () => {
    const sel = cy.nodes(':selected');
    if (sel.length === 2) sel[0].edgesWith(sel[1]).remove();
});

document.addEventListener('keydown', (e) => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && document.activeElement.tagName !== 'INPUT') {
        cy.elements(':selected').remove();
    }
});

// Загрузка файла
document.getElementById('loadButton').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const json = JSON.parse(e.target.result);
            // Загружаем модель
            loadModel(json);
        } catch (error) {
            console.error('❌ Ошибка загрузки файла:', error);
            alert('Ошибка загрузки файла: ' + error.message);
        }
    };
    reader.readAsText(file);
});

function loadModel(model) {
    const nodes = [];
    const edges = [];
    
    // Сброс счетчиков
    actionCounter = 1;
    objectCounter = 1;
    stateCounter = 1;
    
    // Загружаем действия
    if (model.model_actions) {
        model.model_actions.forEach(action => {
            nodes.push({
                data: {
                    id: action.action_id,
                    label: action.action_name,
                    type: 'action',
                    original_name: action.action_name
                }
            });
            
            // Обновляем счетчик
            const num = parseInt(action.action_id.substring(1));
            if (num >= actionCounter) actionCounter = num + 1;
        });
    }
    
    // Загружаем объекты и состояния
    if (model.model_objects) {
        model.model_objects.forEach(obj => {
            if (obj.resource_state) {
                obj.resource_state.forEach(state => {
                    const stateId = `${obj.object_id}${state.state_id}`;
                    nodes.push({
                        data: {
                            id: stateId,
                            label: `${obj.object_name}: ${state.state_name}`,
                            type: 'state',
                            object_id: obj.object_id,
                            object_name: obj.object_name,
                            state_id: state.state_id,
                            state_name: state.state_name
                        }
                    });
                    
                    // Обновляем счетчики
                    const objNum = parseInt(obj.object_id.substring(1));
                    const stateNum = parseInt(state.state_id.substring(1));
                    if (objNum >= objectCounter) objectCounter = objNum + 1;
                    if (stateNum >= stateCounter) stateCounter = stateNum + 1;
                });
            }
        });
    }
    
    // Загружаем связи
    if (model.model_connections) {
        model.model_connections.forEach(conn => {
            edges.push({
                data: {
                    id: `${conn.connection_out}->${conn.connection_in}`,
                    source: conn.connection_out,
                    target: conn.connection_in
                }
            });
        });
    }
    
    // Рендерим граф
    renderGraph({ nodes, edges });
    console.log(`✅ Загружено: ${nodes.length} узлов, ${edges.length} связей`);
}

// Делаем renderGraph доступной глобально для GraphManager
window.renderGraph = renderGraph;