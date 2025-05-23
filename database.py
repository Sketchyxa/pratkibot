import aiosqlite
import os
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self):
        self.db_path = "bot.db"

    async def init(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Создаем таблицу пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    xp INTEGER DEFAULT 0,
                    last_daily TEXT
                )
            """)
            
            # Создаем таблицу карточек
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    user_id INTEGER,
                    card_name TEXT,
                    count INTEGER DEFAULT 1,
                    UNIQUE(user_id, card_name)
                )
            """)
            
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            return await cursor.fetchone()

    async def create_user(self, user_id: int, username: str):
        """Создать нового пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, xp) VALUES (?, ?, 0)",
                (user_id, username)
            )
            await db.commit()

    async def update_last_daily(self, user_id: int):
        """Обновить время последнего получения карточки"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_daily = ? WHERE user_id = ?",
                (now, user_id)
            )
            await db.commit()

    async def add_card(self, user_id: int, card_name: str) -> int:
        """Добавить карточку пользователю и вернуть новое количество"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO cards (user_id, card_name, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, card_name)
                DO UPDATE SET count = count + 1
            """, (user_id, card_name))
            await db.commit()
            
            cursor = await db.execute(
                "SELECT count FROM cards WHERE user_id = ? AND card_name = ?",
                (user_id, card_name)
            )
            result = await cursor.fetchone()
            return result[0] if result else 1

    async def get_user_cards(self, user_id: int) -> List[Dict]:
        """Получить все карточки пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT card_name, count FROM cards WHERE user_id = ?",
                (user_id,)
            )
            return await cursor.fetchall()

    async def add_xp(self, user_id: int, xp: int):
        """Добавить опыт пользователю"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET xp = xp + ? WHERE user_id = ?",
                (xp, user_id)
            )
            await db.commit()

    async def get_leaderboard(self) -> List[Dict]:
        """Получить список лидеров"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT 
                    u.username,
                    u.xp,
                    COUNT(c.card_name) as unique_cards,
                    SUM(c.count) as total_cards
                FROM users u
                LEFT JOIN cards c ON u.user_id = c.user_id
                GROUP BY u.user_id
                ORDER BY u.xp DESC
                LIMIT 10
            """)
            return await cursor.fetchall()

    async def upgrade_cards(self, user_id: int, card_name: str) -> Optional[str]:
        """Улучшить три одинаковые карточки в одну более редкую"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем количество карточек
            cursor = await db.execute(
                "SELECT count FROM cards WHERE user_id = ? AND card_name = ?",
                (user_id, card_name)
            )
            result = await cursor.fetchone()
            
            if not result or result[0] < 3:
                return None
            
            # Уменьшаем количество карточек на 3
            await db.execute("""
                UPDATE cards 
                SET count = count - 3 
                WHERE user_id = ? AND card_name = ?
            """, (user_id, card_name))
            
            # Удаляем запись, если карточек не осталось
            await db.execute("""
                DELETE FROM cards 
                WHERE user_id = ? AND card_name = ? AND count <= 0
            """, (user_id, card_name))
            
            await db.commit()
            return card_name

    async def remove_card(self, user_id: int, card_name: str) -> bool:
        """Удалить одну карточку у пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем наличие карточки
            cursor = await db.execute(
                "SELECT count FROM cards WHERE user_id = ? AND card_name = ?",
                (user_id, card_name)
            )
            result = await cursor.fetchone()
            
            if not result or result[0] < 1:
                return False
            
            # Уменьшаем количество карточек на 1
            await db.execute("""
                UPDATE cards 
                SET count = count - 1 
                WHERE user_id = ? AND card_name = ?
            """, (user_id, card_name))
            
            # Удаляем запись, если карточек не осталось
            await db.execute("""
                DELETE FROM cards 
                WHERE user_id = ? AND card_name = ? AND count <= 0
            """, (user_id, card_name))
            
            await db.commit()
            return True 