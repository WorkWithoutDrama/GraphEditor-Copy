let cy;
let selectionOrder = []; // Очередь выбора узлов
let graphManager;

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
                { selector: 'node[type="object"]', style: {
                    'shape': 'round-hexagon',
                    'background-color': '#fff0f6',
                    'border-color': '#eb2f96',
                    'width': '180px',
                    'height': '80px',
                    'text-wrap': 'wrap',
                    'text-max-width': '180px',
                    'padding': '12px',
                    'min-width': '80px',
                    'min-height': '60px',
                    'font-size': '13px',
                    'font-weight': '500'
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

    cy.on('dblclick', 'node', function(event) {
        const node = event.target;
        const newLabel = prompt('Введите новое название:', node.data('label'));
        if (newLabel) {
            node.data('label', newLabel);
            node.data('id', newLabel);
        }
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

// Остальные функции
document.getElementById('addActionButton').addEventListener('click', () => {
    const name = prompt("Имя действия:");
    if (name) cy.add({ group: 'nodes', data: { id: name, label: name, type: 'action' }, position: { x: 100, y: 100 } });
});

document.getElementById('addStateButton').addEventListener('click', () => {
    const name = prompt("Имя объекта:");
    if (name) cy.add({ group: 'nodes', data: { id: name, label: name, type: 'state' }, position: { x: 100, y: 100 } });
});

document.getElementById('saveButton').addEventListener('click', () => {
    let name = prompt("Имя проекта:", "model") || "project";

    const output = {
        model_actions: [],
        model_objects: [],
        model_connections: []
    };

    // 1. Сохраняем действия - используем реальные ID узлов
    const actionNodes = cy.nodes('[type="action"]');

    actionNodes.forEach(node => {
        // Используем реальный ID узла из графа
        const nodeId = node.id();

        output.model_actions.push({
            action_id: nodeId,  // ← ВАЖНО: используем реальный ID
            action_name: node.data('label') || `Действие ${nodeId}`,
            action_links: {
                manual: "",
                API: "",
                UI: ""
            }
        });
    });

    // 2. Сохраняем объекты и их состояния
    const stateNodes = cy.nodes('[type="state"]');

    // Группируем состояния по объектам
    const objectMap = new Map(); // object_id -> {object_name, states: []}

    stateNodes.forEach(stateNode => {
        const stateId = stateNode.id();
        const stateLabel = stateNode.data('label') || `Состояние ${stateId}`;

        // Парсим ID состояния вида "o00001s00001"
        // Ищем 'o' в начале и 's' для разделения object_id и state_id
        let objectId = "";
        let statePart = "";

        if (stateId.includes('s')) {
            const sIndex = stateId.indexOf('s');
            objectId = stateId.substring(0, sIndex);
            statePart = stateId.substring(sIndex);
        } else {
            // Если формат неправильный, используем первую часть
            objectId = stateId.length > 6 ? stateId.substring(0, 6) : stateId;
            statePart = "s00001";
        }

        // Парсим метку вида "Пользователь: неактивен"
        let objectName = "Объект";
        let stateName = "состояние";

        if (stateLabel.includes(':')) {
            const parts = stateLabel.split(':');
            objectName = parts[0].trim();
            stateName = parts[1].trim();
        } else {
            objectName = stateLabel;
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
            state_id: statePart,
            state_name: stateName
        });
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

    // 3. Сохраняем связи - используем реальные ID
    const edges = cy.edges();

    edges.forEach(edge => {
        const sourceId = edge.source().id();  // ← Реальный ID источника
        const targetId = edge.target().id();  // ← Реальный ID цели
        const sourceType = edge.source().data('type');
        const targetType = edge.target().data('type');

        // Пропускаем связи объект-состояние (они уже в resource_state)
        if ((sourceType === 'object' && targetType === 'state') ||
            (sourceType === 'state' && targetType === 'object')) {
            return;
        }

        // Для состояний создаем составные ID: object_id + state_id
        let finalTargetId = targetId;
        if (targetType === 'state') {
            // Находим родительский объект
            const parentEdges = edge.target().connectedEdges();
            parentEdges.forEach(parentEdge => {
                const parentSource = parentEdge.source();
                const parentTarget = parentEdge.target();
                if (parentSource.data('type') === 'object' && parentTarget.id() === targetId) {
                    finalTargetId = parentSource.id() + targetId;
                } else if (parentTarget.data('type') === 'object' && parentSource.id() === targetId) {
                    finalTargetId = parentTarget.id() + targetId;
                }
            });
        }

        output.model_connections.push({
            connection_out: sourceId,    // ← Реальный ID
            connection_in: finalTargetId // ← Составной ID для состояний
        });
    });

    // 4. Создаем и скачиваем файл
    const jsonStr = JSON.stringify(output, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${name}.json`;
    a.click();
    URL.revokeObjectURL(url);

    console.log('💾 Сохранено:', output);
    console.log(`✅ Действий: ${output.model_actions.length}`);
    console.log(`✅ Объектов: ${output.model_objects.length}`);
    console.log(`✅ Связей: ${output.model_connections.length}`);
});

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

// Загрузка файла через кнопку
document.getElementById('loadButton').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const json = JSON.parse(e.target.result);
        const nodes = [], edges = [], ids = new Set();

        const add = (id, label, type) => {
            if (!ids.has(id)) {
                nodes.push({ data: { id, label: label || id, type } });
                ids.add(id);
            }
        };

        // Определяем формат: новый или старый
        const isNewFormat = json.model_actions && json.model_objects && json.model_connections;
        const isOldFormat = Object.keys(json).some(key =>
            json[key] &&
            typeof json[key] === 'object' &&
            ('init_states' in json[key] || 'final_states' in json[key])
        );

        if (isNewFormat) {
            // НОВЫЙ формат: {model_actions: [...], model_objects: [...], model_connections: [...]}
            console.log('📂 Загружаю файл в НОВОМ формате');

            // 1. Добавляем действия
            json.model_actions.forEach(action => {
                if (action.action_id && action.action_name) {
                    add(action.action_id, action.action_name, 'action');
                }
            });

            // 2. Добавляем объекты и состояния
            json.model_objects.forEach(obj => {
                if (obj.object_id && obj.object_name) {
                    add(obj.object_id, obj.object_name, 'object');

                    // Добавляем состояния
                    if (obj.resource_state && Array.isArray(obj.resource_state)) {
                        obj.resource_state.forEach(state => {
                            if (state.state_id && state.state_name && state.state_name !== 'null') {
                                const stateId = obj.object_id + state.state_id; // составной ID
                                add(stateId, `${obj.object_name}: ${state.state_name}`, 'state');

                                // Связь объект->состояние
                                edges.push({
                                    data: {
                                        id: `${obj.object_id}->${stateId}`,
                                        source: obj.object_id,
                                        target: stateId,
                                        type: 'has_state'
                                    }
                                });
                            }
                        });
                    }
                }
            });

            // 3. Добавляем связи
            json.model_connections.forEach(conn => {
                if (conn.connection_out && conn.connection_in) {
                    edges.push({
                        data: {
                            id: `${conn.connection_out}->${conn.connection_in}`,
                            source: conn.connection_out,
                            target: conn.connection_in
                        }
                    });
                }
            });

        } else if (isOldFormat) {
            // СТАРЫЙ формат: {"Действие": {"init_states": [], "final_states": []}}
            console.log('📂 Загружаю файл в СТАРОМ формате (конвертирую в новый)');

            let actionCounter = 1;
            let objectCounter = 1;
            let stateCounter = 1;
            const objectMap = new Map();

            for (const actionName in json) {
                const actionData = json[actionName];
                const actionId = `a${actionCounter.toString().padStart(5, '0')}`;
                actionCounter++;

                add(actionId, actionName, 'action');

                // Обрабатываем final_states
                if (actionData.final_states && Array.isArray(actionData.final_states)) {
                    actionData.final_states.forEach(stateStr => {
                        if (stateStr && typeof stateStr === 'string') {
                            // Парсим "Объект: состояние"
                            let objName, stateName;
                            if (stateStr.includes(':')) {
                                const parts = stateStr.split(':');
                                objName = parts[0].trim();
                                stateName = parts.slice(1).join(':').trim();
                            } else {
                                objName = stateStr;
                                stateName = "состояние";
                            }

                            // Создаем объект если еще не существует
                            if (!objectMap.has(objName)) {
                                const objectId = `o${objectCounter.toString().padStart(5, '0')}`;
                                objectCounter++;

                                objectMap.set(objName, {
                                    id: objectId,
                                    states: []
                                });

                                add(objectId, objName, 'object');
                            }

                            const objInfo = objectMap.get(objName);
                            const stateId = `s${stateCounter.toString().padStart(5, '0')}`;
                            stateCounter++;

                            const fullStateId = objInfo.id + stateId;
                            add(fullStateId, `${objName}: ${stateName}`, 'state');

                            // Связь объект->состояние
                            edges.push({
                                data: {
                                    id: `${objInfo.id}->${fullStateId}`,
                                    source: objInfo.id,
                                    target: fullStateId,
                                    type: 'has_state'
                                }
                            });

                            // Связь действие->состояние
                            edges.push({
                                data: {
                                    id: `${actionId}->${fullStateId}`,
                                    source: actionId,
                                    target: fullStateId
                                }
                            });
                        }
                    });
                }
            }
        } else {
            console.error('❌ Неизвестный формат файла');
            alert('Неизвестный формат файла. Ожидается новая структура {model_actions, model_objects, model_connections} или старая {действие: {init_states, final_states}}');
            return;
        }

        renderGraph({ nodes, edges });
        console.log(`✅ Загружено: ${nodes.length} узлов, ${edges.length} связей`);
    };
    reader.readAsText(file);
});

// Делаем renderGraph доступной глобально для GraphManager
window.renderGraph = renderGraph;
