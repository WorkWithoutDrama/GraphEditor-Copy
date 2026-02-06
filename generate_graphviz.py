#!/usr/bin/env python3
"""
Генератор графа в формате DOT для Graphviz
Создает визуализацию модели процессов
"""

import json
import re

class GraphvizGenerator:
    def __init__(self, model_file: str = "mindful_meals_advanced.json"):
        self.model_file = model_file
        self.model = None
        self.load_model()
        
    def load_model(self):
        """Загружает модель из JSON файла"""
        try:
            with open(self.model_file, 'r', encoding='utf-8') as f:
                self.model = json.load(f)
            print(f"✅ Модель загружена из {self.model_file}")
            return True
        except FileNotFoundError:
            print(f"❌ Файл {self.model_file} не найден")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка чтения JSON: {e}")
            return False
    
    def generate_dot(self, output_file: str = "model_graph.dot"):
        """Генерирует граф в формате DOT"""
        if not self.model:
            print("❌ Модель не загружена")
            return False
        
        dot_lines = []
        
        # Заголовок графа
        dot_lines.append("digraph ProcessModel {")
        dot_lines.append("  rankdir=LR;")
        dot_lines.append("  node [fontname=\"Helvetica\", fontsize=10];")
        dot_lines.append("  edge [fontname=\"Helvetica\", fontsize=8];")
        dot_lines.append("")
        
        # Создаем узлы для действий (прямоугольники)
        dot_lines.append("  // Действия (прямоугольники)")
        for action in self.model.get("model_actions", []):
            action_id = action["action_id"]
            action_name = action["action_name"]
            # Экранируем кавычки и переносы строк
            action_name_escaped = action_name.replace('"', '\\"').replace('\n', '\\n')
            dot_lines.append(f'  {action_id} [label="{action_name_escaped}", shape=rectangle, style=filled, fillcolor=lightblue];')
        dot_lines.append("")
        
        # Создаем узлы для объектов+состояний (овалы)
        dot_lines.append("  // Объекты и состояния (овалы)")
        object_state_nodes = {}
        
        for obj in self.model.get("model_objects", []):
            object_id = obj["object_id"]
            object_name = obj["object_name"]
            
            for state in obj.get("resource_state", []):
                state_id = state["state_id"]
                state_name = state["state_name"]
                
                # Создаем узел для комбинации объект+состояние
                node_id = f"{object_id}{state_id}"
                label = f"{object_name}\\n{state_name}"
                label_escaped = label.replace('"', '\\"')
                
                dot_lines.append(f'  {node_id} [label="{label_escaped}", shape=oval, style=filled, fillcolor=lightyellow];')
                
                # Сохраняем для использования в связях
                object_state_nodes[node_id] = {
                    "object": object_name,
                    "state": state_name
                }
        dot_lines.append("")
        
        # Создаем связи
        dot_lines.append("  // Связи между узлами")
        for connection in self.model.get("model_connections", []):
            source = connection["connection_out"]
            target = connection["connection_in"]
            
            # Определяем типы узлов для форматирования
            source_type = "action" if source.startswith("a") else "state"
            target_type = "action" if target.startswith("a") else "state"
            
            # Добавляем стрелку
            dot_lines.append(f"  {source} -> {target};")
        dot_lines.append("")
        
        # Добавляем легенду
        dot_lines.append("  // Легенда")
        dot_lines.append("  subgraph cluster_legend {")
        dot_lines.append("    label=\"Легенда\";")
        dot_lines.append("    style=dashed;")
        dot_lines.append("    rankdir=TB;")
        dot_lines.append("    ")
        dot_lines.append("    legend_action [label=\"Действие\", shape=rectangle, style=filled, fillcolor=lightblue];")
        dot_lines.append("    legend_state [label=\"Объект+Состояние\", shape=oval, style=filled, fillcolor=lightyellow];")
        dot_lines.append("  }")
        
        # Завершаем граф
        dot_lines.append("}")
        
        # Сохраняем в файл
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(dot_lines))
            
            print(f"✅ Граф сохранен в {output_file}")
            print(f"📊 Статистика:")
            print(f"   • Действий: {len(self.model.get('model_actions', []))}")
            print(f"   • Объектов: {len(self.model.get('model_objects', []))}")
            print(f"   • Состояний: {sum(len(obj.get('resource_state', [])) for obj in self.model.get('model_objects', []))}")
            print(f"   • Связей: {len(self.model.get('model_connections', []))}")
            print(f"\n🎯 Для визуализации выполните:")
            print(f"   dot -Tpng {output_file} -o model_graph.png")
            print(f"   Или откройте в Graphviz Online")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения графа: {e}")
            return False
    
    def generate_mermaid(self, output_file: str = "model_mermaid.md"):
        """Генерирует граф в формате Mermaid.js"""
        if not self.model:
            print("❌ Модель не загружена")
            return False
        
        mermaid_lines = []
        
        # Заголовок Mermaid
        mermaid_lines.append("```mermaid")
        mermaid_lines.append("graph LR")
        mermaid_lines.append("")
        
        # Определяем стили
        mermaid_lines.append("  %% Стили")
        mermaid_lines.append("  classDef action fill:#e1f5fe,stroke:#01579b,stroke-width:2px")
        mermaid_lines.append("  classDef state fill:#fff3e0,stroke:#e65100,stroke-width:2px,rounded")
        mermaid_lines.append("")
        
        # Создаем узлы
        node_definitions = []
        
        # Действия
        for action in self.model.get("model_actions", []):
            action_id = action["action_id"]
            action_name = action["action_name"].replace('"', '&quot;')
            node_definitions.append(f"  {action_id}[{action_name}]")
        
        # Объекты+состояния
        for obj in self.model.get("model_objects", []):
            object_id = obj["object_id"]
            
            for state in obj.get("resource_state", []):
                state_id = state["state_id"]
                state_name = state["state_name"]
                
                node_id = f"{object_id}{state_id}"
                label = f"{obj['object_name']}<br/>{state_name}".replace('"', '&quot;')
                node_definitions.append(f"  {node_id}({label})")
        
        mermaid_lines.extend(node_definitions)
        mermaid_lines.append("")
        
        # Применяем стили
        mermaid_lines.append("  %% Применяем стили")
        for action in self.model.get("model_actions", []):
            mermaid_lines.append(f"  class {action['action_id']} action")
        
        for obj in self.model.get("model_objects", []):
            for state in obj.get("resource_state", []):
                node_id = f"{obj['object_id']}{state['state_id']}"
                mermaid_lines.append(f"  class {node_id} state")
        
        mermaid_lines.append("")
        
        # Создаем связи
        mermaid_lines.append("  %% Связи")
        for connection in self.model.get("model_connections", []):
            source = connection["connection_out"]
            target = connection["connection_in"]
            mermaid_lines.append(f"  {source} --> {target}")
        
        mermaid_lines.append("```")
        
        # Сохраняем в файл
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(mermaid_lines))
            
            print(f"✅ Mermaid граф сохранен в {output_file}")
            print(f"📊 Для использования:")
            print(f"   1. Скопируйте содержимое файла в Markdown-документ")
            print(f"   2. Или используйте на Mermaid Live Editor")
            print(f"   3. Или вставьте в GitHub/GitLab Markdown")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения Mermaid графа: {e}")
            return False
    
    def generate_simple_html(self, output_file: str = "model_viewer.html"):
        """Генерирует простой HTML для просмотра модели"""
        if not self.model:
            print("❌ Модель не загружена")
            return False
        
        html_template = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Модель процессов: Mindful Meals</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true
            }
        });
    </script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #4CAF50;
        }
        .stat-card h3 {
            margin: 0;
            color: #333;
            font-size: 14px;
            text-transform: uppercase;
        }
        .stat-card .number {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
            margin: 10px 0;
        }
        .graph-container {
            margin: 30px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background-color: #fafafa;
        }
        .details {
            margin-top: 30px;
        }
        .section {
            margin-bottom: 20px;
        }
        .section h3 {
            color: #333;
            padding: 10px;
            background-color: #e8f5e8;
            border-radius: 5px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .connection {
            font-family: monospace;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Модель процессов: Mindful Meals</h1>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Действий</h3>
                <div class="number">ACTIONS_COUNT</div>
                <p>Процессы системы</p>
            </div>
            <div class="stat-card">
                <h3>Объектов</h3>
                <div class="number">OBJECTS_COUNT</div>
                <p>Сущности системы</p>
            </div>
            <div class="stat-card">
                <h3>Состояний</h3>
                <div class="number">STATES_COUNT</div>
                <p>Статусы объектов</p>
            </div>
            <div class="stat-card">
                <h3>Связей</h3>
                <div class="number">CONNECTIONS_COUNT</div>
                <p>Взаимодействия</p>
            </div>
        </div>
        
        <div class="graph-container">
            <h2>Визуализация модели</h2>
            <div class="mermaid">
MERMAID_GRAPH
            </div>
        </div>
        
        <div class="details">
            <div class="section">
                <h3>📋 Действия</h3>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Название</th>
                            <th>API</th>
                            <th>UI</th>
                        </tr>
                    </thead>
                    <tbody>
                        ACTIONS_TABLE
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h3>🏛️ Объекты и состояния</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Объект</th>
                            <th>ID</th>
                            <th>Состояния</th>
                        </tr>
                    </thead>
                    <tbody>
                        OBJECTS_TABLE
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h3>🔗 Связи</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Источник</th>
                            <th>Направление</th>
                            <th>Цель</th>
                        </tr>
                    </thead>
                    <tbody>
                        CONNECTIONS_TABLE
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        # Подготавливаем данные
        actions_count = len(self.model.get("model_actions", []))
        objects_count = len(self.model.get("model_objects", []))
        states_count = sum(len(obj.get("resource_state", [])) for obj in self.model.get("model_objects", []))
        connections_count = len(self.model.get("model_connections", []))
        
        # Генерируем Mermaid граф
        mermaid_graph = self._generate_mermaid_for_html()
        
        # Генерируем таблицу действий
        actions_table = ""
        for action in self.model.get("model_actions", []):
            actions_table += f"""
                        <tr>
                            <td><code>{action['action_id']}</code></td>
                            <td>{action['action_name']}</td>
                            <td><code>{action.get('action_links', {}).get('API', '')}</code></td>
                            <td><code>{action.get('action_links', {}).get('UI', '')}</code></td>
                        </tr>"""
        
        # Генерируем таблицу объектов
        objects_table = ""
        for obj in self.model.get("model_objects", []):
            states_list = "<br>".join([f"{state['state_name']} ({state['state_id']})" 
                                      for state in obj.get("resource_state", [])])
            objects_table += f"""
                        <tr>
                            <td>{obj['object_name']}</td>
                            <td><code>{obj['object_id']}</code></td>
                            <td>{states_list}</td>
                        </tr>"""
        
        # Генерируем таблицу связей
        connections_table = ""
        for conn in self.model.get("model_connections", []):
            connections_table += f"""
                        <tr>
                            <td class="connection">{conn['connection_out']}</td>
                            <td>→</td>
                            <td class="connection">{conn['connection_in']}</td>
                        </tr>"""
        
        # Заменяем плейсхолдеры
        html_content = html_template
        html_content = html_content.replace("ACTIONS_COUNT", str(actions_count))
        html_content = html_content.replace("OBJECTS_COUNT", str(objects_count))
        html_content = html_content.replace("STATES_COUNT", str(states_count))
        html_content = html_content.replace("CONNECTIONS_COUNT", str(connections_count))
        html_content = html_content.replace("MERMAID_GRAPH", mermaid_graph)
        html_content = html_content.replace("ACTIONS_TABLE", actions_table)
        html_content = html_content.replace("OBJECTS_TABLE", objects_table)
        html_content = html_content.replace("CONNECTIONS_TABLE", connections_table)
        
        # Сохраняем HTML
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML просмотрщик сохранен в {output_file}")
            print(f"📊 Откройте файл в браузере для просмотра модели")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения HTML: {e}")
            return False
    
    def _generate_mermaid_for_html(self):
        """Генерирует Mermaid граф для HTML"""
        lines = ["graph LR"]
        lines.append("")
        
        # Стили
        lines.append("  classDef action fill:#e1f5fe,stroke:#01579b,stroke-width:2px")
        lines.append("  classDef state fill:#fff3e0,stroke:#e65100,stroke-width:2px,rounded")
        lines.append("")
        
        # Узлы (ограничим количество для читаемости)
        action_nodes = self.model.get("model_actions", [])[:15]  # Первые 15 действий
        for action in action_nodes:
            action_id = action["action_id"]
            action_name = action["action_name"].replace('"', '&quot;')
            lines.append(f"  {action_id}[\"{action_name}\"]")
            lines.append(f"  class {action_id} action")
        
        lines.append("")
        
        # Примерные связи (ограничим для читаемости)
        connections = self.model.get("model_connections", [])[:30]  # Первые 30 связей
        for conn in connections:
            lines.append(f"  {conn['connection_out']} --> {conn['connection_in']}")
        
        return "\n".join(lines)

def main():
    """Основная функция"""
    generator = GraphvizGenerator("mindful_meals_advanced.json")
    
    # Генерируем DOT файл для Graphviz
    generator.generate_dot("process_model.dot")
    
    # Генерируем Mermaid граф
    generator.generate_mermaid("process_model_mermaid.md")
    
    # Генерируем HTML просмотрщик
    generator.generate_simple_html("model_viewer.html")
    
    print("\n" + "="*60)
    print("🎯 ФАЙЛЫ ДЛЯ ВИЗУАЛИЗАЦИИ СОЗДАНЫ:")
    print("="*60)
    print("1. process_model.dot - Граф для Graphviz")
    print("   Команда для PNG: dot -Tpng process_model.dot -o model.png")
    print("")
    print("2. process_model_mermaid.md - Mermaid граф")
    print("   Можно вставить в GitHub/GitLab Markdown")
    print("")
    print("3. model_viewer.html - HTML просмотрщик")
    print("   Откройте в браузере для интерактивного просмотра")
    print("")
    print("📌 Для быстрого просмотра Mermaid графа:")
    print("   • Скопируйте содержимое process_model_mermaid.md")
    print("   • Вставьте на https://mermaid.live")
    print("="*60)

if __name__ == "__main__":
    main()