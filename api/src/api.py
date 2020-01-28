# coding: utf-8

import asyncio
import base64
import datetime
import hashlib
import os

import aiohttp
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

    def _curr_conversion(self, amount, mult_1, rate_1, mult_2, rate_2):
        return amount * mult_1 * rate_2 / mult_2 * rate_1

    async def _update_currensy(self):
        """
        Обновления курса валют в бд. Курс берётся из внешних источников.
        """

        rates = {
            'USD': 1.0  # базовая валюта
        }

        # получаем EUR, GBP, RUB
        async with aiohttp.ClientSession() as session:
            url = 'https://api.exchangeratesapi.io/latest?base=USD&symbols=EUR,GBP,RUB'
            async with session.get(url) as resp:
                r = await resp.json()
                rates.update(r['rates'])

        # получаем BTC
        async with aiohttp.ClientSession() as session:
            url = 'https://blockchain.info/ticker'
            async with session.get(url) as resp:
                r = await resp.json()
                rates['BTC'] = r['USD']['last']

        # обновляем курсы валют за одну транзакцию
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for k, v in rates.items():
                    await conn.execute(
                        "UPDATE Currencies SET rate = $1 WHERE id = $2", v, k
                    )

    def _prepare_for_bcrypt(self, password):
        """
        Подготавливает пароль для хеширования bcrypt'ом.
        """
        # bcrypt не умеет работать со строками больше 72 символов
        sha256_hash = hashlib.sha256(password.encode()).digest()
        # защищаемся от NULL байтов
        base64_hash = base64.b64encode(sha256_hash)
        return base64_hash

    async def _get_currency_data(self, currency):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                curr = await conn.fetchrow(
                    "SELECT * FROM Currencies WHERE id = $1", currency
                )
                return dict(curr) if curr else {}

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

    async def add_user(self, email, password, balance, currency, **kwargs):
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

    async def auth(self, email, password, **kwargs):
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

    async def get_transactions_list(self, current_user, limit=10, skip=0, **kwargs):
        """
        Возвращает список всех операций по счёту пользователя.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                data = await conn.fetch(
                    "SELECT * FROM Transactions WHERE sender = $1 or recipient = $1 \
                    LIMIT $2 OFFSET $3",
                    current_user, limit, skip
                )
                data_dict = []
                for x in data:
                    row = dict(x)
                    row['date'] = row['date'].strftime("%H:%M %d-%m-%Y")
                    row['amount'] = str(row['amount'])
                    data_dict.append(row)
                return 200, 'OK', data_dict

    async def make_transaction(self, email, amount, current_user, **kwargs):
        """
        Переводит средства на счёт пользователя.
        """

        recipient = await self._get_user(email)
        # проверяем существует ли получатель
        if not recipient:
            return 404, 'Recipient not found!', {}

        sender = await self._get_user(current_user)

        # проверяем баланс
        if sender['balance'] < amount:
            return 400, 'Insufficient funds', {}

        # если у отправителя и получателя разные валюты счетов, то конвертируем
        if sender['currency'] != recipient['currency']:
            s_curr = await self._get_currency_data(sender['currency'])
            r_curr = await self._get_currency_data(recipient['currency'])
            amount_convert = self._curr_conversion(
                amount, s_curr['multiplier'], s_curr['rate'],
                r_curr['multiplier'], r_curr['rate']
            )
        else:
            amount_convert = amount

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE Users SET balance = balance - $1 WHERE email = $2",
                    amount, current_user
                )
                await conn.execute(
                    "UPDATE Users SET balance = balance + $1 WHERE email = $2",
                    amount_convert, email
                )
                await conn.execute(
                    "INSERT INTO Transactions (sender, recipient, amount) VALUES ($1, $2, $3)",
                    current_user, email, amount
                )
                return 200, 'OK', {}

    async def update_currency_run(self):
        while True:
            await self._update_currensy()
            await asyncio.sleep(int(os.environ['CURRENCY_UPDATE_DELAY']) * 60)
