import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Конфигурация карточек и их вероятностей выпадения
CARD_RARITY = {
    "common": {"weight": 69.89, "xp": 10},
    "rare": {"weight": 20, "xp": 30},
    "epic": {"weight": 8, "xp": 50},
    "legendary": {"weight": 2, "xp": 100},
    "artifact": {"weight": 0.01, "xp": 200}
}

# Время ожидания между сбором карточек (в секундах)
DAILY_COOLDOWN = 7200  # 2 часа

# Формула опыта для уровней (100 * уровень)
def xp_for_level(level: int) -> int:
    return 100 * level

# Бонусный опыт за 3 одинаковые карточки
TRIPLE_CARD_BONUS = {
    "common": 50,
    "rare": 150,
    "epic": 300,
    "legendary": 600,
    "artifact": 1200
}

# Правила улучшения карточек
UPGRADE_RULES = {
    "common": "rare",
    "rare": "epic",
    "epic": "legendary",
    "legendary": "artifact"
} 