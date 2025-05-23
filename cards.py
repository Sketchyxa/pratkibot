import random
import json
import os
import logging
from typing import Dict, Optional, Tuple
from config import CARD_RARITY

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Пути к файлам
CARDS_JSON_PATH = os.path.join('assets', 'cards.json')
CARDS_IMAGES_DIR = os.path.join('assets', 'cards')

def get_card_image_path(image_filename: str) -> str:
    """Получить полный путь к изображению карточки"""
    return os.path.join(CARDS_IMAGES_DIR, image_filename)

def load_cards() -> Dict:
    """Загрузить данные карточек из JSON файла"""
    if not os.path.exists(CARDS_JSON_PATH):
        raise FileNotFoundError(f"Файл с карточками не найден: {CARDS_JSON_PATH}")
    
    with open(CARDS_JSON_PATH, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    # Проверяем форматы файлов
    for card_name, card_info in cards.items():
        image_file = card_info.get('image', '')
        file_ext = os.path.splitext(image_file)[1].lower()
        
        if file_ext not in ['.gif', '.mp4']:
            raise ValueError(
                f"Ошибка в карточке '{card_name}': файл {image_file} имеет неподдерживаемый формат. "
                f"Разрешены только .gif и .mp4"
            )
        
        # Проверяем существование файла
        image_path = get_card_image_path(image_file)
        if not os.path.exists(image_path):
            raise FileNotFoundError(
                f"Ошибка в карточке '{card_name}': файл {image_file} не найден в папке {CARDS_IMAGES_DIR}"
            )
        
    # Проверяем распределение карточек по редкости
    rarity_distribution = {}
    for card_name, card_info in cards.items():
        rarity = card_info['rarity']
        if rarity not in rarity_distribution:
            rarity_distribution[rarity] = []
        rarity_distribution[rarity].append(card_name)
    
    # Логируем информацию о распределении
    for rarity, cards_list in rarity_distribution.items():
        logger.info(f"Карточек редкости {rarity}: {len(cards_list)}")
        logger.info(f"Список карточек {rarity}: {', '.join(cards_list)}")
    
    return cards

# Загружаем карточки при импорте модуля
CARDS = load_cards()

def get_card_info(card_name: str) -> Optional[Dict]:
    """Получить информацию о карточке по её названию"""
    card_info = CARDS.get(card_name)
    if card_info:
        # Добавляем полный путь к изображению
        card_info['image_path'] = get_card_image_path(card_info['image'])
    return card_info

def get_random_card() -> Tuple[str, Dict]:
    """Получить случайную карточку с учетом весов редкости"""
    # Группируем карточки по редкости для более эффективного выбора
    cards_by_rarity = {}
    for name, card in CARDS.items():
        rarity = card["rarity"]
        if rarity not in cards_by_rarity:
            cards_by_rarity[rarity] = []
        cards_by_rarity[rarity].append(name)
    
    # Выбираем редкость с учетом весов
    rarities = list(CARD_RARITY.keys())
    weights = [CARD_RARITY[rarity]["weight"] for rarity in rarities]
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    
    # Выбираем случайную карточку из выбранной редкости
    available_cards = cards_by_rarity.get(chosen_rarity, [])
    if not available_cards:
        # Если почему-то нет карточек выбранной редкости, выбираем из всех
        name = random.choice(list(CARDS.keys()))
    else:
        name = random.choice(available_cards)
    
    # Логируем информацию о выпавшей карточке
    logger.info(f"Выпала карточка: {name} (редкость: {chosen_rarity})")
    
    card_info = CARDS[name].copy()
    card_info['image_path'] = get_card_image_path(card_info['image'])
    return name, card_info

def get_card_xp(rarity: str) -> int:
    """Получить количество опыта за карточку определенной редкости"""
    return CARD_RARITY[rarity]["xp"]

def format_card_message(username: str, card_name: str, card_info: Dict, total_cards: int, cooldown: str) -> str:
    """Форматировать сообщение о полученной карточке"""
    rarity_emoji = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "artifact": "🔴"
    }
    
    return f"""🎉 @{username} получил карточку:
{rarity_emoji[card_info['rarity']]} [{card_name}]
🔹 Редкость: {card_info['rarity'].capitalize()}
📝 {card_info['description']}
🧠 +{get_card_xp(card_info['rarity'])} опыта

👑 Всего карточек у тебя: {total_cards}
🔁 Следующая попытка: через {cooldown}""" 