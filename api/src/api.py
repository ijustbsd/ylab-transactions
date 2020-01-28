# coding: utf-8

import base64
import datetime
import hashlib

import bcrypt
import jwt


class API():
    def __init__(self, pool, secret):
        self.pool = pool
        self.secret = secret

    def _create_token(self, email, lifetime=10):
        """
        Создаёт JWT токен.
        """
        # токен действителен lifetime минут
        exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=lifetime)
        payload = {'email': email, 'exp': exp}
        token = jwt.encode(payload, self.secret, algorithm='HS256')
        return token.decode()

    def _check_token(self, token):
        """
        Проверяет валидность JWT токена.
        """
        try:
            payload = jwt.decode(token.encode(), self.secret, algorithm='HS256')
        except jwt.ExpiredSignatureError:
            return False, 'Token expired!'
        except (jwt.DecodeError, AttributeError):
            return False, 'Invalid token!'
        return True, payload['email']

    def _prepare_for_bcrypt(self, password):
        """
        Подготавливает пароль для хеширования bcrypt'ом.
        """
        # bcrypt не умеет работать со строками больше 72 символов
        sha256_hash = hashlib.sha256(password.encode()).digest()
        # защищаемся от NULL байтов
        base64_hash = base64.b64encode(sha256_hash)
        return base64_hash

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

        password = self._prepare_for_bcrypt(password)
        # хешируем и солим пароль для хранения в базе
        hashed = bcrypt.hashpw(password, bcrypt.gensalt(12))

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

        user = await self._get_user(email)

        # проверяем зарегистрирован ли пользователь с таким email'ом
        if not user:
            return 404, 'User not found!', {}

        password = self._prepare_for_bcrypt(password)
        # если хеши совпали, то отдаём пользователю токен
        if bcrypt.checkpw(password, user['password']):
            return 200, 'OK', self._create_token(email)

        return 403, 'Wrong password!', {}

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
