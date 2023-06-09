from oy3opy.utils.task import doneQueue, Task
from oy3opy.ai.bing import Model as bing, events as bing_events
from .model import *

def Events(model:str):
    if model == 'bing':
        return bing_events

def Model(model:str):
    if model == 'bing':
        return bing
    return None

class Chat:
    def __init__(self, model:str, cookie:dict, listeners:dict, proxy:str):
        self.model = model
        self.context = None
        self.messages = []
        self.ai = AI(Model(model)(cookie, listeners, ({scheme: proxy for scheme in ['http://','https://']} if type(proxy) == str else proxy) if proxy else {}))
    async def update(self, context):
        await self.ai.model._update(context)
        self.context = context
    async def send(self, message):
        turn = {'prompt':message, 'context':self.context,'answer':''}
        self.messages.append(turn)
        async for chunk in self.ai.model._send(message):
            turn['answer'] += chunk
            yield chunk
    async def send_once(self, message):
        response = ''
        async for chunk in self.ai.model._send(message):
            response += chunk
        return response
    async def close(self):
        await self.ai.close()

class Config:
    def __init__(self, data:dict[str,dict or str]={}):
        self.model:str = data.get('model') or 'bing'
        self.context:str = data.get('context') or ''
        self.cookie:dict = data.get('cookie') or {}
        self.proxy:str = data.get('proxy') or {}
        self.contexts:dict[str,str] = data.get('contexts') or {}
        self.cookies:dict[str,str]= data.get('cookies') or {}
        self.proxies:dict[str,str] = data.get('proxies') or {}
        self.listeners:dict[str,dict] = data.get('listeners') or {}

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
            proxy = object.__getattribute__(self, 'proxies').get(name) or object.__getattribute__(self, 'proxy')
            return {
                'model': name,
                'context': object.__getattribute__(self, 'contexts').get(name) or object.__getattribute__(self, 'context'),
                'cookie': object.__getattribute__(self, 'cookies').get(name) or object.__getattribute__(self, 'cookie'),
                'proxies': {_: proxy for _ in ['http://','https://']} if proxy else {},
                'listeners': object.__getattribute__(self, 'listeners').get(name) or {},
            }

config = Config()

async def exec(prompt:str, context:str=None, model:str = 'bing', _config:Config = None):
    c:dict = getattr(config, model)
    c.update(getattr(_config, model))
    ai = AI(Model(model)(c['cookie'], c['listeners'], c['proxies']))
    async for chunk in ai.exec({'context': c['context'] if context is None else context, 'prompt': prompt}):
        yield chunk
    await ai.close()

async def exec_once(prompt:str, context:str=None, model:str = 'bing', _config:Config = None):
    response = ''
    async for chunk in exec(prompt, context, model, _config):
        response += chunk
    return response

def execTasks(tasks, _config = config):
    for response in doneQueue([(task, Task(exec_once,(task['prompt'], task.get('context'), task['model'], _config))) for task in tasks]):
        yield response

def execTasks_once(tasks, _config = config):
    return [response for response in execTasks(tasks, _config)]

def execTasksChain(chain, _config = config):
    context = ''
    def update(tasks):
        for task in tasks:
            task['context'] = context + (task['context'] if task.get('context') else '')
        return tasks

    def parseContext(node):
        context = ''
        for (ai, response) in node:
            context += f'[{ai}]: {response}\n[/${ai}]\n'
        return context

    for tasks in chain:
        node = execTasks_once(update(tasks), _config)
        context = parseContext(node)
        yield node

def execTasksChain_once(chain, _config = config):
    response = []
    for node in execTasksChain(chain, _config):
        response.append(node)
    return response