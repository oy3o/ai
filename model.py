from oy3opy.utils.string import errString

class Model():
    def __init__(self, cookie, listeners, proxies):
        self.cookie = cookie
        self.listeners = listeners
        self.proxies = proxies
        self.context = ''
        self.chat = None
        self._init()

    def dispatch(self, event, payload:dict={}):
        if event in self.listeners:
            payload.update({'event': event})
            self.listeners[event](payload)

    def error(self, action:str, e:Exception):
        self.dispatch('error', {
            'action': action,
            'message': errString(e),
        })

    def _init(self):
        try:
            self.init()
            self.chat = True
        except Exception as e:
            self.error('init', e)

    async def _update(self, context):
        try:
            await self.update(context)
            self.context = context
        except Exception as e:
            self.error('update', e)

    async def _send(self, message):
        try:
            async for chunk in self.send(message):
                yield chunk
        except Exception as e:
            self.error('send', e)

    async def _close(self):
        try:
            await self.close()
            self.chat = False
            self.listeners = {}
        except Exception as e:
            self.error('close', e)

    def init(self):
        pass
    async def update(self, context):
        pass
    async def send(self, message):
        pass
    async def close(self):
        pass

class AI:
    def __init__(self, model:Model):
        self.model = model

    async def exec(self, task:dict):
        context = task.get('context')
        prompt = task.get('prompt')
        if context:
            await self.model._update(context)
        if prompt:
            async for chunk in self.model._send(prompt):
                yield chunk

    async def close(self):
        await self.model._close()