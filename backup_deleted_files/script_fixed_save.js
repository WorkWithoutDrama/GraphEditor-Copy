/**
 * Исправленный script.js с правильным сохранением
 * Заменяет только функцию сохранения
 */

// Сохраняем оригинальный код кроме функции сохранения
// Заменяем только обработчик saveButton

// Находим и заменяем обработчик saveButton
document.addEventListener('DOMContentLoaded', function() {
    // Удаляем старый обработчик
    const saveButton = document.getElementById('saveButton');
    const newSaveButton = saveButton.cloneNode(true);
    saveButton.parentNode.replaceChild(newSaveButton, saveButton);
    
    // Устанавливаем новый обработчик
    newSaveButton.addEventListener('click', function() {
        let name = prompt("Имя проекта:", "model") || "project";
        
        const output = {
            model_actions: [],
            model_objects: [],
            model_connections: []
        };

        // 1. Сохраняем действия - используем ID узлов напрямую
        const actionNodes = cy.nodes('[type="action"]');
        actionNodes.forEach(node => {
            output.model_actions.push({
                action_id: node.id(), // Используем реальный ID узла
                action_name: node.data('label') || `Действие ${node.id()}`,
                action_links: {
                    manual: "",
                    API: "",
                    UI: ""
                }
            });
        });

        // 2. Сохраняем объекты и их состояния
        const objectNodes = cy.nodes('[type="object"]');
        const stateNodes = cy.nodes('[type="state"]');
        
        // Собираем все состояния в карту
        const stateMap = new Map();
        stateNodes.forEach(stateNode => {
            stateMap.set(stateNode.id(), {
                id: stateNode.id(),
                label: stateNode.data('label') || `Состояние ${stateNode.id()}`
            });
        });

        // Обрабатываем объекты
        objectNodes.forEach(objectNode => {
            const objectId = objectNode.id();
            const resourceState = [];
            
            // Ищем связанные состояния
            const connectedEdges = objectNode.connectedEdges();
            connectedEdges.forEach(edge => {
                const sourceId = edge.source().id();
                const targetId = edge.target().id();
                
                // Если edge связывает объект с состоянием
                if (sourceId === objectId && stateMap.has(targetId)) {
                    const stateInfo = stateMap.get(targetId);
                    resourceState.push({
                        state_id: stateInfo.id,
                        state_name: stateInfo.label
                    });
                } else if (targetId === objectId && stateMap.has(sourceId)) {
                    const stateInfo = stateMap.get(sourceId);
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
                object_id: objectId,
                object_name: objectNode.data('label') || `Объект ${objectId}`,
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
            
            // Пропускаем связи объект-состояние
            if ((sourceType === 'object' && targetType === 'state') ||
                (sourceType === 'state' && targetType === 'object')) {
                return;
            }
            
            // Для состояний нужно создавать составные ID: object_id + state_id
            let finalTargetId = targetId;
            if (targetType === 'state') {
                // Находим родительский объект для состояния
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
                connection_out: sourceId,
                connection_in: finalTargetId
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
});