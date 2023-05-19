# AI Chat Mode and Tasks Chain with Python API and Websocket API and Terminal
call all ai models under oy3opy.ai through chat mode, one times ask and tasks chain.
## Python API
python api to access multiple with chat mode or not
### chat mode
you can use api as chat mode ( stream or one message), with chat context.
```py
from oy3opy.ai import Chat
from oy3opy.ai.bing import events
from oy3opy.utils.file import read_text
import asyncio
import json

cookie = dict([(c['name'], c['value']) for c in json.loads(read_text('cookie.json'))])
listeners = dict.fromkeys(events, print)
proxies = {
    'http://': 'http://127.0.0.1:1081',
    'https://': 'http://127.0.0.1:1081',
}

async def main():
    chat = Chat('bing', cookie, listeners, proxies)
    await chat.update('current time: 2024-05-20 00:00:00')
    # stream
    async for chunk in chat.send('what is the time on page?'):
        print(chunk, end='', flush=True)
    # one message
    print(await chat.send_once('what is the realtime?'))

asyncio.run(main())
```
### No chat context
you can use api without chat context
```py
from oy3opy.ai import config, exec, Config, exec_once

config.bing.cookie = cookie
config.bing.listeners = listeners
config.bing.proxies = proxies
# stream
async for chunk in exec('bing', 'hello', context=''):
    print(chunk, end='', flush=True)
# one message with special config, all function can use special config
print(await exec_once('bing', 'hello', '', Config({
    'bing':{
        'cookie': cookie,
        'listeners': listeners,
        'proxies': proxies,
    }
})))
```
### Tasks Chain
all function has stream version and one message version
```py
from oy3opy.ai import execTasksChain, execTasksChain_once, config

config.bing.cookie = cookie
config.bing.listeners = listeners
config.bing.proxies = proxies
# tasks stream version
for response in execTasks([{'model':'bing', 'prompt':'What is Goldbach Conjecture 1+1'},{'model':'bing', 'prompt':'What is Peano axioms 1+1'}]):
    print(response)
# tasks chain one message version
ResponseChain = execTasksChain_once([
    [{'model':'bing', 'prompt':'What is Goldbach Conjecture 1+1'},{'model':'bing', 'prompt':'What is Peano axioms 1+1'}],
    [{'model':'bing', 'prompt':'No Search, what is 1+1 means in math?'}]
])
print(ResponseChain)
```

## Websocket API
```
come soon...
```
## Terminal command
```
come soon...
```