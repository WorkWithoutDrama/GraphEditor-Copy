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
                    'width': '80px',
                    'height': '40px',
                    'padding': '15px',
                    'border-width': 2,
                    'border-color': '#007bff',
                    'background-color': '#fff'
                } },
                { selector: 'node[type="action"]', style: {
                    'shape': 'rectangle',
                    'background-color': '#e6f7ff',
                    'width': '100px',
                    'height': '50px'
                } },
                { selector: 'node[type="state"]', style: {
                    'shape': 'ellipse',
                    'background-color': '#f6ffed',
                    'border-color': '#52c41a',
                    'width': '80px',
                    'height': '80px'
                } },
                { selector: 'edge', style: {
                    'width': 2,
                    'line-color': '#ccc',
                    'target-arrow-shape': 'triangle',
                    'target-arrow-color': '#ccc',
                    'curve-style': 'bezier'
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
    const output = {};
    cy.nodes('[type="action"]').forEach(node => {
        output[node.data('label')] = {
            init_states: node.incomers('edge').sources().map(n => n.data('label')),
            final_states: node.outgoers('edge').targets().map(n => n.data('label'))
        };
    });
    const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${name}.json`;
    a.click();
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
        const add = (id, type) => {
            if (!ids.has(id)) { nodes.push({ data: { id, label: id, type } }); ids.add(id); }
        };
        for (const act in json) {
            add(act, 'action');
            (json[act].init_states || []).forEach(s => { add(s, 'state'); edges.push({ data: { id: `${s}->${act}`, source: s, target: act } }); });
            (json[act].final_states || []).forEach(s => { add(s, 'state'); edges.push({ data: { id: `${act}->${s}`, source: act, target: s } }); });
        }
        renderGraph({ nodes, edges });
    };
    reader.readAsText(file);
});

// Делаем renderGraph доступной глобально для GraphManager
window.renderGraph = renderGraph;
