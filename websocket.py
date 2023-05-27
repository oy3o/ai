from oy3opy.utils.string import tojson, errString
from .core import *
from websockets.server import serve
import asyncio
import json


_proxies = {}
async def listen(addr:str, port:int, proxy = None):
    _proxies.update({_: proxy for _ in ['http://','https://']} if proxy else {})
    while True:
        try:
            async with serve(handler, addr, port):
                await asyncio.Future()
        except:
            pass

async def handler(socket):
    _ai = {}
    try:
        async for payload in socket:
            message = json.loads(payload)
            id = message.get('id')
            model = message.get('model')
            cookie = message.get('cookie')
            if id:
                await _handler(socket, _ai, message, id, model, cookie)
            else:
                prompt = message.get('prompt')
                if prompt:
                    ai = AI(Model(model)(cookie, dict.fromkeys(Events(model), event_sender(socket, model)), _proxies))
                    await send(socket, message, ai)
                    await ai.close()
    except: # websocket close
        pass

    for id in _ai:
        await _ai[id].close()


def event_sender(socket, id):
    def send_event(e):
        e.update({'id':id, 'type':'event'})
        asyncio.run(socket.send(tojson(e)))
    return send_event


async def send(socket, message, ai):
    context = message.get('context')
    prompt = message.get('prompt')
    if not (context or prompt):
        return
    try:
        async for chunk in ai.exec({
            'context': context,
            'prompt': prompt,
        }):
            await socket.send(tojson({'type':'message', 'message': chunk}))
    except Exception as e:
        await socket.send(tojson({'type':'error', 'message': errString(e)}))


async def _handler(socket, _ai, message, id, model, cookie):
    if cookie:
        if _ai.get(id):
            await _ai[id].close()
        _ai[id] = AI(Model(model)(cookie, dict.fromkeys(Events(model), event_sender(socket, model)), _proxies))
    if not _ai.get(id):
        await socket.send('{"type":"error", "id":"'+ id +'", "message":"model is not initialized"}')
        return

    await send(socket, message, _ai[id])
