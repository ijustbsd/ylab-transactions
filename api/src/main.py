# coding: utf-8

import json
import os

import asyncpg
from aiohttp import web
from jsonschema import ValidationError, validate

from api import API

routes = web.RouteTableDef()

with open('schema.json') as f:
    json_schema = json.load(f)


def api_response(code, msg, payload=None):
    if payload is None:
        payload = {}
    template = {
        'code': code,
        'message': msg,
        'payload': payload
    }
    return web.json_response(template)


@routes.post('/')
async def main_post(request):
    try:
        request_data = await request.json()
        # валидируем данные согласно jsonschem'е
        validate(request_data, json_schema)
    except json.decoder.JSONDecodeError:
        return api_response(400, 'Invalid JSON!')
    except ValidationError as e:
        return api_response(400, e.message)

    # если данные прошли валидацию, то достаём из них поле с запросом
    (query, params), = request_data['request'].items()
    # вызываем метод используя getattr т.к. он провалидирован jsonschem'ой
    code, msg, payload = await getattr(request.app['api'], query)(**params)
    return api_response(code, msg, payload)


async def create_app():
    app = web.Application()
    app['pool'] = await asyncpg.create_pool(
        host='postgres',
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME']
    )
    app['api'] = API(pool=app['pool'])
    # создаём первого пользователя, который сможет добавлять последующих
    email = os.environ['USER_EMAIL']
    password = os.environ['USER_PASSWORD']
    balance = os.environ['USER_BALANCE']
    currency = os.environ['USER_CURRENCY']
    await app['api'].add_user(email, password, balance, currency)
    app.add_routes(routes)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app)
