# Настройка GitHub репозитория

## Текущее состояние:
- Удаленный репозиторий настроен: `https://github.com/nataliyademina/GraphEditor.git`
- Но репозиторий не существует или нет доступа

## Варианты решения:

### Вариант 1: Создать репозиторий вручную (рекомендуется)
1. Откройте https://github.com/new в браузере
2. Войдите в аккаунт `nataliyademina`
3. Создайте репозиторий с именем `GraphEditor`
4. Не добавляйте README, .gitignore или лицензию
5. После создания выполните в терминале:

```bash
# Убедитесь, что находитесь в папке проекта
cd /Users/nataliyademina/GraphEditor/TestEditor

# Отправьте изменения
git push -u origin main

# Отправьте теги
git push --tags
```

### Вариант 2: Использовать GitHub CLI (если установлен)
```bash
# Проверить установлен ли gh
gh --version

# Если установлен:
gh auth login
gh repo create GraphEditor --public --source=. --remote=origin --push
```

### Вариант 3: Использовать личный токен
1. Создайте personal access token на https://github.com/settings/tokens
2. Дайте права `repo`
3. Используйте:

```bash
git remote set-url origin https://ВАШ_ТОКЕН@github.com/nataliyademina/GraphEditor.git
git push -u origin main
```

### Вариант 4: Проверить существующий репозиторий
Возможно, репозиторий уже существует, но приватный:
```bash
# Попробовать с доступом по SSH
git remote set-url origin git@github.com:nataliyademina/GraphEditor.git
git push -u origin main
```

## Быстрые команды для проверки:
```bash
# Проверить подключение
git remote -v

# Проверить доступ
git fetch origin

# Попробовать принудительный пуш (если репозиторий пустой)
git push -u origin main --force
```

## Если нужна помощь:
1. Создайте репозиторий через веб-интерфейс GitHub
2. Или предоставьте personal access token с правами `repo`
3. Я помогу с остальными командами