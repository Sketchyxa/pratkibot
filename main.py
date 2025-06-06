import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import os
import random
import aiosqlite

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

from config import BOT_TOKEN, DAILY_COOLDOWN, xp_for_level, UPGRADE_RULES, TRIPLE_CARD_BONUS, ADMIN_IDS
from database import Database
from cards import get_random_card, get_card_info, format_card_message, get_card_xp, CARDS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    if not update.effective_user:
        return
    
    await db.create_user(
        update.effective_user.id,
        update.effective_user.username or "Anonymous"
    )
    
    welcome_text = """
🎮 Привет! Я бот для коллекционирования карточек!

Доступные команды:
/dailycard - Получить ежедневную карточку
/mycards - Посмотреть свою коллекцию
/profile - Посмотреть свой профиль
/cardinfo <название> - Информация о карточке
/leaderboard - Посмотреть список лучших
/upgrade - улучшить 3 одинаковых карты

Удачи в коллекционировании! 🎉
"""
    await update.message.reply_text(welcome_text)

async def calculate_level(xp: int) -> tuple[int, int, int]:
    """Вычисляет текущий уровень, текущий опыт и опыт до следующего уровня"""
    level = 1
    while xp >= xp_for_level(level):
        xp -= xp_for_level(level)
        level += 1
    return level, xp, xp_for_level(level) - xp

async def format_time_until(target_time: Optional[datetime]) -> str:
    """Форматирует оставшееся время"""
    if not target_time:
        return "сейчас"
    
    now = datetime.now()
    if target_time <= now:
        return "сейчас"
    
    diff = target_time - now
    total_seconds = diff.total_seconds()
    
    # Всегда показываем часы и минуты
    total_minutes = int(total_seconds / 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    return f"{hours}ч {minutes}м"

async def send_card_message(message: str, image_path: str, update: Update):
    """Отправить сообщение с изображением или анимацией карточки"""
    try:
        if not os.path.exists(image_path):
            await update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.HTML
            )
            return
            
        # Определяем расширение файла
        file_ext = os.path.splitext(image_path)[1].lower()
        
        with open(image_path, 'rb') as media_file:
            if file_ext in ['.mp4', '.gif']:
                # Для анимированных файлов используем animation
                await update.effective_message.reply_animation(
                    animation=media_file,
                    caption=message,
                    parse_mode=ParseMode.HTML,
                    read_timeout=30,
                    write_timeout=30
                )
            else:
                # Для статичных изображений используем photo
                await update.effective_message.reply_photo(
                    photo=media_file,
                    caption=message,
                    parse_mode=ParseMode.HTML,
                    read_timeout=30,
                    write_timeout=30
                )
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        # Если не удалось отправить с медиа, отправляем только текст
        await update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.HTML
        )

async def dailycard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /dailycard"""
    if not update.effective_user or not update.effective_message:
        return

    user = await db.get_user(update.effective_user.id)
    if not user:
        await db.create_user(
            update.effective_user.id,
            update.effective_user.username or "Anonymous"
        )
        user = await db.get_user(update.effective_user.id)

    now = datetime.now()
    
    # Проверяем кулдаун
    if user and user['last_daily']:
        try:
            last_daily = datetime.fromisoformat(user['last_daily'].replace('Z', '+00:00'))
            next_daily = last_daily + timedelta(seconds=DAILY_COOLDOWN)
            
            if now < next_daily:
                time_until = await format_time_until(next_daily)
                await update.effective_message.reply_text(
                    f"⌛ Следующую карточку можно получить через {time_until}"
                )
                return
        except ValueError:
            pass

    # Проверяем, есть ли у пользователя карточки
    async with aiosqlite.connect(db.db_path) as db_conn:
        cursor = await db_conn.execute(
            "SELECT COUNT(*) FROM cards WHERE user_id = ?",
            (update.effective_user.id,)
        )
        card_count = (await cursor.fetchone())[0]
        is_first_card = card_count == 0

    # Получаем случайную карточку
    card_name, card_info = get_random_card()
    
    # Специальный эффект для артифактных карточек
    if card_info['rarity'] == 'artifact':
        # 50/50 шанс на дополнительную карточку или потерю случайной
        if random.random() < 0.5:
            # Получаем случайную карточку любой редкости
            bonus_card_name, bonus_card_info = get_random_card()
            await db.add_card(update.effective_user.id, bonus_card_name)
            await update.effective_message.reply_text(
                f"🎁 Артифактная карточка принесла вам бонус!\n"
                f"Получена дополнительная карточка: {bonus_card_name} ({bonus_card_info['rarity']})"
            )
        else:
            # Получаем список карточек пользователя
            user_cards = await db.get_user_cards(update.effective_user.id)
            if user_cards:
                # Выбираем случайную карточку для удаления
                card_to_remove = random.choice(user_cards)
                await db.remove_card(update.effective_user.id, card_to_remove['card_name'])
                await update.effective_message.reply_text(
                    f"💀 Артифактная карточка забрала у вас карточку: {card_to_remove['card_name']}"
                )
    
    # Добавляем карточку пользователю
    count = await db.add_card(update.effective_user.id, card_name)

    # Если это первая карточка пользователя, даём бонусную
    bonus_message = ""
    if is_first_card:
        bonus_card_name, bonus_card_info = get_random_card()
        await db.add_card(update.effective_user.id, bonus_card_name)
        bonus_message = f"\n\n🎁 Бонус для новичка!\nВы получаете дополнительную карточку: {bonus_card_name} ({bonus_card_info['rarity'].capitalize()})"
    
    # Проверяем на тройку одинаковых карточек
    if count % 3 == 0:
        bonus_xp = TRIPLE_CARD_BONUS[card_info['rarity']]
        await db.add_xp(update.effective_user.id, bonus_xp)
        await update.effective_message.reply_text(
            f"🎉 Бонус! У вас {count} карточек {card_name}!\n"
            f"Получено дополнительно {bonus_xp} опыта!"
        )
    
    # Обновляем время последнего получения
    await db.update_last_daily(update.effective_user.id)
    
    # Начисляем опыт
    xp = get_card_xp(card_info["rarity"])
    await db.add_xp(update.effective_user.id, xp)
    
    # Получаем общее количество карточек
    user_cards = await db.get_user_cards(update.effective_user.id)
    total_cards = sum(card['count'] for card in user_cards)
    
    # Форматируем и отправляем сообщение
    next_daily = now + timedelta(seconds=DAILY_COOLDOWN)
    time_until = await format_time_until(next_daily)
    
    message = format_card_message(
        update.effective_user.username or "Anonymous",
        card_name,
        card_info,
        total_cards,
        time_until
    ) + bonus_message
    
    await send_card_message(message, card_info['image_path'], update)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /profile"""
    if not update.effective_user or not update.effective_message:
        return

    user = await db.get_user(update.effective_user.id)
    if not user:
        await update.effective_message.reply_text("❌ Профиль не найден. Используйте /start для начала игры.")
        return

    xp = user['xp']
    level, current_xp, xp_needed = await calculate_level(xp)
    
    user_cards = await db.get_user_cards(update.effective_user.id)
    total_cards = sum(card['count'] for card in user_cards)
    
    unique_cards = len(user_cards)
    
    profile_text = f"""
👤 Профиль @{update.effective_user.username or "Anonymous"}

📊 Уровень: {level}
⭐️ Опыт: {current_xp}/{xp_needed}
🎴 Карточек: {total_cards} (уникальных: {unique_cards})
"""
    
    await update.effective_message.reply_text(profile_text)

async def mycards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /mycards"""
    if not update.effective_user or not update.effective_message:
        return

    user_cards = await db.get_user_cards(update.effective_user.id)
    if not user_cards:
        await update.effective_message.reply_text("У вас пока нет карточек. Используйте /dailycard чтобы получить первую!")
        return

    # Группируем карточки по редкости
    cards_by_rarity = {
        "artifact": [],
        "legendary": [],
        "epic": [],
        "rare": [],
        "common": []
    }
    
    for card in user_cards:
        card_info = get_card_info(card['card_name'])
        if card_info:
            cards_by_rarity[card_info['rarity']].append(
                f"{card['card_name']} (x{card['count']})"
            )

    # Форматируем сообщение
    rarity_emoji = {
        "artifact": "🔴",
        "legendary": "🟡",
        "epic": "🟣",
        "rare": "🔵",
        "common": "⚪"
    }
    
    message = "🎴 Ваша коллекция:\n\n"
    for rarity, cards in cards_by_rarity.items():
        if cards:
            message += f"{rarity_emoji[rarity]} {rarity.capitalize()}:\n"
            message += "\n".join(f"• {card}" for card in cards)
            message += "\n\n"

    await update.effective_message.reply_text(message)

async def cardinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cardinfo"""
    if not update.effective_message or not context.args:
        await update.effective_message.reply_text(
            "❌ Укажите название карточки: /cardinfo <название>"
        )
        return

    card_name = " ".join(context.args)
    card_info = get_card_info(card_name)
    
    if not card_info:
        await update.effective_message.reply_text("❌ Карточка не найдена")
        return

    rarity_emoji = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "artifact": "🔴"
    }

    message = f"""
{rarity_emoji[card_info['rarity']]} [{card_name}]
🔹 Редкость: {card_info['rarity'].capitalize()}
📝 Описание: {card_info['description']}
🧠 Опыт: +{get_card_xp(card_info['rarity'])} XP
"""

    await send_card_message(message, card_info['image_path'], update)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /leaderboard"""
    if not update.effective_message:
        return
    
    leaders = await db.get_leaderboard()
    if not leaders:
        await update.effective_message.reply_text("📊 Пока нет данных для таблицы лидеров")
        return
    
    message = "🏆 Таблица лидеров:\n\n"
    for i, leader in enumerate(leaders, 1):
        message += f"{i}. {leader['username']}\n"
        message += f"   ⭐️ {leader['xp']} опыта\n"
        message += f"   🎴 {leader['total_cards']} карточек ({leader['unique_cards']} уникальных)\n\n"
    
    await update.effective_message.reply_text(message)

async def upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /upgrade"""
    if not update.effective_message or not context.args:
        await update.effective_message.reply_text(
            "❌ Укажите название карточки: /upgrade <название>"
        )
        return
    
    card_name = " ".join(context.args)
    card_info = get_card_info(card_name)
    
    if not card_info:
        await update.effective_message.reply_text("❌ Карточка не найдена")
        return
    
    if card_info['rarity'] == "artifact":
        await update.effective_message.reply_text("❌ Артифактные карточки нельзя улучшить")
        return
    
    # Пытаемся улучшить карточки
    result = await db.upgrade_cards(update.effective_user.id, card_name)
    if not result:
        await update.effective_message.reply_text(
            f"❌ Для улучшения нужно 3 карточки {card_name}"
        )
        return
    
    # Определяем следующую редкость
    next_rarity = UPGRADE_RULES[card_info['rarity']]
    
    # Ищем случайную карточку следующей редкости
    available_cards = [
        name for name, info in CARDS.items()
        if info['rarity'] == next_rarity
    ]
    
    if not available_cards:
        await update.effective_message.reply_text("❌ Ошибка: нет карточек для улучшения")
        return
    
    # Выбираем случайную карточку новой редкости
    new_card_name = random.choice(available_cards)
    new_card_info = get_card_info(new_card_name)
    
    # Добавляем новую карточку
    await db.add_card(update.effective_user.id, new_card_name)
    
    # Форматируем сообщение
    rarity_emoji = {
        "artifact": "🔴",
        "legendary": "🟡",
        "epic": "🟣",
        "rare": "🔵",
        "common": "⚪"
    }
    
    message = f"""✨ Улучшение успешно!

Потрачено: 3x {card_name} ({card_info['rarity']})
Получено: {rarity_emoji[next_rarity]} [{new_card_name}]
🔹 Редкость: {next_rarity.capitalize()}
📝 {new_card_info['description']}"""

    await send_card_message(message, new_card_info['image_path'], update)

async def is_admin(user_id: int) -> bool:
    """Проверка на админа"""
    return user_id in ADMIN_IDS

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить объявление всем пользователям (только для админов)"""
    if not update.effective_user or not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для использования этой команды")
        return

    if not context.args:
        await update.message.reply_text("❌ Укажите текст объявления: /announce <текст>")
        return

    announcement = " ".join(context.args)
    
    # Получаем всех пользователей из базы
    async with aiosqlite.connect(db.db_path) as db_conn:
        cursor = await db_conn.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()

    success_count = 0
    fail_count = 0

    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user[0],
                text=f"📢 ОБЪЯВЛЕНИЕ\n\n{announcement}"
            )
            success_count += 1
        except Exception:
            fail_count += 1

    await update.message.reply_text(
        f"✅ Объявление отправлено!\n"
        f"Успешно: {success_count}\n"
        f"Не удалось: {fail_count}"
    )

async def set_xp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить опыт пользователю (только для админов)"""
    if not update.effective_user or not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для использования этой команды")
        return

    if len(context.args) != 2:
        await update.message.reply_text("❌ Использование: /setxp <username> <количество>")
        return

    username, xp = context.args[0], context.args[1]
    
    try:
        xp = int(xp)
    except ValueError:
        await update.message.reply_text("❌ Количество опыта должно быть числом")
        return

    # Обновляем опыт пользователя
    async with aiosqlite.connect(db.db_path) as db_conn:
        await db_conn.execute(
            "UPDATE users SET xp = ? WHERE username = ?",
            (xp, username)
        )
        await db_conn.commit()

    await update.message.reply_text(f"✅ Установлен опыт {xp} для пользователя {username}")

async def give_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдать карточку пользователю (только для админов)"""
    if not update.effective_user or not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для использования этой команды")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /givecard <username> <название_карточки>")
        return

    username = context.args[0]
    card_name = " ".join(context.args[1:])
    
    # Проверяем существование карточки
    card_info = get_card_info(card_name)
    if not card_info:
        await update.message.reply_text("❌ Карточка не найдена")
        return

    # Находим ID пользователя по имени
    async with aiosqlite.connect(db.db_path) as db_conn:
        cursor = await db_conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        )
        user = await cursor.fetchone()
        
        if not user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        user_id = user[0]

    # Выдаем карточку
    count = await db.add_card(user_id, card_name)
    
    await update.message.reply_text(
        f"✅ Выдана карточка {card_name} пользователю {username}\n"
        f"Теперь у него {count} таких карточек"
    )

async def mass_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Раздать карточку случайным игрокам (только для админов)"""
    if not update.effective_user or not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав для использования этой команды")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /massgift <количество_игроков> <название_карточки>")
        return

    try:
        num_players = int(context.args[0])
        if num_players <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Количество игроков должно быть положительным числом")
        return

    card_name = " ".join(context.args[1:])
    
    # Проверяем существование карточки
    card_info = get_card_info(card_name)
    if not card_info:
        await update.message.reply_text("❌ Карточка не найдена")
        return

    # Получаем всех пользователей из базы
    async with aiosqlite.connect(db.db_path) as db_conn:
        cursor = await db_conn.execute("SELECT user_id, username FROM users")
        all_users = await cursor.fetchall()

    if not all_users:
        await update.message.reply_text("❌ В базе нет пользователей")
        return

    # Выбираем случайных пользователей
    selected_users = random.sample(all_users, min(num_players, len(all_users)))
    
    success_count = 0
    failed_count = 0
    winners_list = []

    # Фиксированный бонус опыта за участие в раздаче
    GIVEAWAY_XP_BONUS = 50

    # Раздаем карточки
    for user_id, username in selected_users:
        try:
            # Выдаем карточку
            count = await db.add_card(user_id, card_name)
            
            # Добавляем бонусный опыт
            await db.add_xp(user_id, GIVEAWAY_XP_BONUS)

            message = f"🎉 Поздравляем! Вы выиграли карточку в раздаче!\n\n"
            message += f"Карточка: {card_name}\n"
            message += f"Редкость: {card_info['rarity'].capitalize()}\n"
            message += f"У вас теперь {count} таких карточек\n"
            message += f"Получено {GIVEAWAY_XP_BONUS} опыта за участие в раздаче!"

            # Отправляем уведомление пользователю
            await context.bot.send_message(
                chat_id=user_id,
                text=message
            )
            
            success_count += 1
            winners_list.append(username)
        except Exception as e:
            logging.error(f"Ошибка при раздаче карточки: {e}")
            failed_count += 1

    # Формируем сообщение о результатах
    result_message = f"✅ Раздача карточки {card_name} завершена!\n\n"
    result_message += f"Успешно выдано: {success_count}\n"
    result_message += f"Не удалось выдать: {failed_count}\n"
    result_message += f"Бонус опыта каждому: {GIVEAWAY_XP_BONUS}\n\n"
    
    result_message += "Список победителей:\n"
    for i, winner in enumerate(winners_list, 1):
        result_message += f"{i}. {winner}\n"

    await update.message.reply_text(result_message)

if __name__ == "__main__":
    # Создаем и запускаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dailycard", dailycard))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("mycards", mycards))
    app.add_handler(CommandHandler("cardinfo", cardinfo))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("upgrade", upgrade))
    
    # Админские команды
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("setxp", set_xp))
    app.add_handler(CommandHandler("givecard", give_card))
    app.add_handler(CommandHandler("massgift", mass_gift))
    
    # Инициализируем базу данных
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.init())
    
    print("🤖 Бот запущен и готов к работе!")
    
    # Запускаем бота
    app.run_polling() 