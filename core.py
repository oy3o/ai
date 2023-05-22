from oy3opy.utils.task import doneQueue, AsyncTask
from oy3opy.ai.bing import Model as bing, events as bing_events
from .model import AI

def Events(model:str):
    if model == 'bing':
        return bing_events

def Model(model:str):
    if model == 'bing':
        return bing
    return None

class Chat:
    def __init__(self, model, cookie, listeners, proxies):
        self.ai = AI(Model(model)(cookie, listeners, proxies))
    async def update(self, context):
        await self.ai.model._update(context)
    async def send(self, message):
        async for chunk in self.ai.model._send(message):
            yield chunk
    async def send_once(self, message):
        response = ''
        async for chunk in self.ai.model._send(message):
            response += chunk
        return response
    async def close(self):
        await self.ai.close()

class BingConfig:
    def __init__(self, data={}):
        self.cookie = (data and data.get('cookie')) or {}
        self.listeners = (data and data.get('listeners')) or {}
        self.proxies = (data and data.get('proxies')) or {}

class Config:
    def __init__(self, data={}):
        self.bing = BingConfig(data.get('bing'))

config = Config()

async def exec(model:str, prompt:str, context='', _config = config):
    ai = AI(Model(model)(
        _config.bing.cookie,
        _config.bing.listeners,
        _config.bing.proxies,
    ))
    async for chunk in ai.exec({'context': context, 'prompt': prompt}):
        yield chunk
    await ai.close()

async def exec_once(model:str, prompt:str, context='', _config = config):
    response = ''
    async for chunk in exec(model, prompt, context, _config):
        response += chunk
    return response

def execTasks(tasks, _config = config):
    for response in doneQueue([(task['model'], AsyncTask(exec_once,(task['model'], task['prompt'], task.get('context'), _config))) for task in tasks]):
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