#!/bin/bash

# Скрипт для создания репозитория через GitHub API
# Нужен personal access token с правами repo

echo "Создание репозитория GraphEditor для WorkWithoutDrama через GitHub API"
echo "======================================================================"

# Запрос токена
read -p "Введите GitHub Personal Access Token (с правами repo): " TOKEN

if [ -z "$TOKEN" ]; then
    echo "❌ Токен не введен"
    exit 1
fi

# Проверяем, существует ли репозиторий
echo "🔍 Проверяю существование репозитория..."
RESPONSE=$(curl -s -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/WorkWithoutDrama/GraphEditor)

if echo "$RESPONSE" | grep -q '"message":"Not Found"'; then
    echo "📦 Репозиторий не существует, создаю..."
    
    # Создаем репозиторий
    CREATE_RESPONSE=$(curl -s -X POST \
      -H "Authorization: token $TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      -d '{"name":"GraphEditor","description":"Graph Editor with AI model generation","private":false}' \
      https://api.github.com/user/repos)
    
    if echo "$CREATE_RESPONSE" | grep -q '"id"'; then
        echo "✅ Репозиторий создан успешно!"
        
        # Настраиваем remote
        git remote set-url origin https://github.com/WorkWithoutDrama/GraphEditor.git
        
        # Отправляем изменения
        echo "🚀 Отправляю изменения..."
        git push -u origin main
        
        # Отправляем теги
        git push --tags
        
        echo "🎉 Готово! Репозиторий: https://github.com/WorkWithoutDrama/GraphEditor"
    else
        echo "❌ Ошибка при создании репозитория:"
        echo "$CREATE_RESPONSE"
    fi
else
    echo "✅ Репозиторий уже существует!"
    
    # Настраиваем remote
    git remote set-url origin https://github.com/WorkWithoutDrama/GraphEditor.git
    
    # Отправляем изменения
    echo "🚀 Отправляю изменения..."
    git push -u origin main --force
    
    # Отправляем теги
    git push --tags --force
    
    echo "🎉 Готово! Репозиторий: https://github.com/WorkWithoutDrama/GraphEditor"
fi