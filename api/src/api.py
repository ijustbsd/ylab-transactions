# coding: utf-8

import base64
import hashlib

import bcrypt


class API():
    def __init__(self, pool):
        self.pool = pool

    async def _get_user(self, email):
        """
        Получает данные о бользователе из бд.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                user = await conn.fetchrow(
                    "SELECT * FROM Users WHERE email = $1", email
                )
                return dict(user) if user else {}

    async def add_user(self, email, password, balance, currency):
        """
        Добавляет нового пользователя в бд.
        """

        # проверяем зарегистрирован ли пользователь с таким email'ом
        if await self._get_user(email):
            return 400, 'User with this email already exist!', {}

        # bcrypt не умеет работать со строками больше 72 символов
        sha256_hash = hashlib.sha256(password.encode()).digest()
        # защищаемся от NULL байтов
        base64_hash = base64.b64encode(sha256_hash)
        # хешируем и солим пароль для хранения в базе
        hashed = bcrypt.hashpw(base64_hash, bcrypt.gensalt(12))

        # добавляем пользователя в бд
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("INSERT INTO Users VALUES ($1, $2, $3, $4)",
                                   email, hashed, balance, currency)
                return 200, 'OK', {}

    async def auth(self, email, password):
        """
        Авторизует пользователя.
        """
        return 200, 'OK', {}

    async def get_transactions_list(self, **kwargs):
        """
        Возвращает список всех операций по счёту пользователя.
        """
        return 200, 'OK', {}

    async def make_transaction(self, **kwargs):
        """
        Переводит средства на счёт другого пользователя.
        """
        return 200, 'OK', {}
