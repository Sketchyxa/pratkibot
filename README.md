# 🎮 Бот для коллекционирования карточек пратков

Телеграм бот для коллекционирования карточек с тематикой "пратков". 

## 🌟 Особенности
- 40 уникальных карточек
- 5 уровней редкости:
  - ⚪ Common (69.89%)
  - 🔵 Rare (20%)
  - 🟣 Epic (8%)
  - 🟡 Legendary (2%)
  - 🔴 Artifact (0.01%)
- Система улучшения карточек (3 одинаковые -> 1 следующей редкости)
- Анимированные карточки (поддержка .gif и .mp4)
- Система опыта и уровней
- Таблица лидеров

## 🎯 Команды
- `/start` - Начать игру
- `/dailycard` - Получить ежедневную карточку (кулдаун 2 часа)
- `/mycards` - Посмотреть свою коллекцию
- `/profile` - Посмотреть свой профиль
- `/cardinfo <название>` - Информация о карточке
- `/upgrade <название>` - Улучшить 3 одинаковые карточки
- `/leaderboard` - Таблица лидеров

## ⚡ Система улучшения
1. Соберите 3 одинаковые карточки
2. Используйте команду `/upgrade`
3. Получите случайную карточку следующей редкости:
   - 3x Common -> 1x Rare
   - 3x Rare -> 1x Epic
   - 3x Epic -> 1x Legendary
   - 3x Legendary -> 1x Artifact

## 💎 Артефактные карточки
При получении артефактной карточки активируется один из двух эффектов (50/50):
- 🎁 Бонус: получение дополнительной случайной карточки
- 💀 Проклятие: потеря случайной карточки из коллекции

## 🎨 Требования к файлам карточек
- Формат: `.mp4` или `.gif`
- Расположение: папка `assets/cards/`
- Имя файла должно соответствовать полю `image` в `cards.json`

## 💫 Система опыта
- Common: 10 XP (бонус за тройку: 50 XP)
- Rare: 30 XP (бонус за тройку: 150 XP)
- Epic: 50 XP (бонус за тройку: 300 XP)
- Legendary: 100 XP (бонус за тройку: 600 XP)
- Artifact: 200 XP (бонус за тройку: 1200 XP)

## 🛠️ Установка
1. Установите зависимости: `pip install -r requirements.txt`
2. Создайте файл `.env` и добавьте токен бота: `BOT_TOKEN=your_token_here`
3. Поместите файлы карточек в папку `assets/cards/`
4. Запустите бота: `python main.py` 