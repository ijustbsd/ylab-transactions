# coding: utf-8

import json
import logging

from aiohttp import web
from jsonschema import ValidationError, validate

from api import API

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

api = API()

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
        validate(request_data, json_schema)
    except json.decoder.JSONDecodeError:
        return api_response(400, 'Invalid JSON!')
    except ValidationError as e:
        return api_response(400, e.message)

    (query, params), = request_data.pop('request').items()
    params.update(request_data)

    code, msg, payload = await getattr(api, query)(**params)
    return api_response(code, msg, payload)


async def create_app():
    app = web.Application()
    app.add_routes(routes)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app)
