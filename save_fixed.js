/**
 * Исправленная функция сохранения JSON
 * Сохраняет исходные ID узлов из сгенерированной модели
 */

function setupFixedSaveButton() {
    document.getElementById('saveButton').addEventListener('click', () => {
        let name = prompt("Имя проекта:", "model") || "project";
        
        const output = {
            model_actions: [],
            model_objects: [],
            model_connections: []
        };

        // 1. Сохраняем действия - используем ID узлов как есть
        const actionNodes = cy.nodes('[type="action"]');
        
        actionNodes.forEach(node => {
            // Используем ID узла как action_id
            const nodeId = node.id();
            
            output.model_actions.push({
                action_id: nodeId,
                action_name: node.data('label') || `Действие ${nodeId}`,
                action_links: {
                    manual: "",
                    API: "",
                    UI: ""
                }
            });
        });

        // 2. Сохраняем объекты и состояния
        // Сначала собираем все состояния
        const stateNodes = cy.nodes('[type="state"]');
        const stateMap = new Map();
        
        stateNodes.forEach(stateNode => {
            stateMap.set(stateNode.id(), {
                id: stateNode.id(),
                label: stateNode.data('label') || `Состояние ${stateNode.id()}`
            });
        });

        // Теперь объекты
        const objectNodes = cy.nodes('[type="object"]');
        
        objectNodes.forEach(node => {
            const nodeId = node.id();
            const resourceState = [];
            
            // Ищем связанные состояния
            const connectedEdges = node.connectedEdges();
            connectedEdges.forEach(edge => {
                const sourceId = edge.source().id();
                const targetId = edge.target().id();
                
                // Если это связь с состоянием
                if (stateMap.has(sourceId) && targetId === nodeId) {
                    const stateInfo = stateMap.get(sourceId);
                    resourceState.push({
                        state_id: stateInfo.id,
                        state_name: stateInfo.label
                    });
                } else if (stateMap.has(targetId) && sourceId === nodeId) {
                    const stateInfo = stateMap.get(targetId);
                    resourceState.push({
                        state_id: stateInfo.id,
                        state_name: stateInfo.label
                    });
                }
            });

            // Если нет состояний, добавляем null
            if (resourceState.length === 0) {
                resourceState.push({
                    state_id: "s00000",
                    state_name: "null"
                });
            }

            output.model_objects.push({
                object_id: nodeId,
                object_name: node.data('label') || `Объект ${nodeId}`,
                resource_state: resourceState,
                object_links: {
                    manual: "",
                    API: "",
                    UI: ""
                }
            });
        });

        // 3. Сохраняем связи (кроме связей объект-состояние)
        const edges = cy.edges();
        
        edges.forEach(edge => {
            const sourceId = edge.source().id();
            const targetId = edge.target().id();
            const sourceType = edge.source().data('type');
            const targetType = edge.target().data('type');
            
            // Пропускаем связи объект-состояние (они уже в resource_state)
            if ((sourceType === 'object' && targetType === 'state') ||
                (sourceType === 'state' && targetType === 'object')) {
                return;
            }
            
            output.model_connections.push({
                connection_out: sourceId,
                connection_in: targetId
            });
        });

        // Преобразуем в JSON и скачиваем
        const jsonStr = JSON.stringify(output, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${name}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        console.log('💾 Сохранено:', output);
    });
}

// Заменяем оригинальный обработчик
document.addEventListener('DOMContentLoaded', function() {
    // Удаляем старый обработчик
    const oldSaveButton = document.getElementById('saveButton');
    const newSaveButton = oldSaveButton.cloneNode(true);
    oldSaveButton.parentNode.replaceChild(newSaveButton, oldSaveButton);
    
    // Устанавливаем новый обработчик
    setupFixedSaveButton();
});