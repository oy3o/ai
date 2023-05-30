# AI Chat Mode and Tasks Chain with Python API and Websocket API and Terminal
call all ai models under `oy3opy.ai` through chat mode, one times ask and tasks chain with Python API and Websocket API and Terminal
## Python API
python api to access multiple with chat mode or not
### chat mode
you can use api as chat mode ( stream or one message), with chat context.
```py
from oy3opy.ai import Chat, Events
from oy3opy.utils.file import io
import asyncio
import json

with io('cookie.json') as f:
    cookie = dict([(c['name'], c['value']) for c in json.load(f)])
listeners = dict.fromkeys(Events('bing'), [print])
proxy = 'http://127.0.0.1:1081'

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

# default config
config.cookie =  cookie
config.listener = listeners
config.proxy = proxies
# stream
async for chunk in exec('hello', context=''):
    print(chunk, end='', flush=True)
# one message with special config, all function can use special config
print(await exec_once('hello', None, 'bing', Config({
    'cookies': {'bing': cookie},
    'listeners': {'bing': listeners},
    'proxies': {'bing': proxies},
})))
```
### Tasks Chain
all function has stream version and one message version
```py
from oy3opy.ai import execTasksChain, execTasksChain_once, config

# bing default config
config.cookies['bing'] =  cookie
config.listeners['bing'] = listeners
config.proxies['bing'] = proxies
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
why not http? you can do it, but websocket is more suitable for stream and event.
### server
```py
# server
from oy3opy.ai.websocket import listen
import asyncio
import nest_asyncio
nest_asyncio.apply()
asyncio.run(listen('127.0.0.1', 8443, proxies = {
    'http://': 'http://127.0.0.1:1081',
    'https://': 'http://127.0.0.1:1081',
}))
```
### demo client of python
```py
# client test
from oy3opy.utils.string import tojson
from oy3opy.utils.file import io
from websockets.sync.client import connect
import json

with io('cookie.json') as f:
    cookie = dict([(c['name'], c['value']) for c in json.load(f)])

ws = connect("ws://127.0.0.1:8443")

ws.send(tojson({'id':'IdOfThisAi', 'model':'bing','cookie':cookie,'prompt':'hello'}))
ws.send(tojson({'id':'IdOfThisAi', 'prompt':'how are you'}))

ws.send(tojson({'model':'bing','cookie':cookie,'prompt':'hello'}))
while True:
    message = json.loads(ws.recv())
    if message['type'] == 'message': # error | event | message
        print(message['message'], end='', flush=True)
    else:
        print(message)
```

## Terminal command
### commandline
`app 'prompt' [option]` ask one question then get a stream print answer
```
    --model   'bing'
    --context 'context'
    --cookie  'path/your/cookie'
    --proxy   'http://127.0.0.1:1081'
    --config  'path/your/config'
    --load   'path/your/save'
```

### interactive cli
`app --config 'path/your/config'` just without `prompt` then you can access interactive cli
```
    command      │    description
─────────────────────────────────────────────────────────────
    exit         │    exit app
    chat NAME    │    start a chat
    task NAME    │    start a task
    view NUM     │    show details of message
    edit NUM     │    edit json of message

─────────────────────────────────────────────────────────────
    shortcut     │    description
─────────────────────────────────────────────────────────────
    Ctrl+A       │    cursor to start
    Ctrl+E       │    cursor to end
    Ctrl+X       │    clean all content
    Ctrl+Z       │    resotre pre action
    Ctrl+C       │    copy all content to clipboard
    Ctrl+V       │    paste from your clipboard
    Esc          │    exit edit without change
    Ctrl+D       │    stop edit with change

let's try to first chat, enter 'chat help' to access interactive guide

```

*message display update throttle 0.25s, i think someone may want to know it, it define on line 208*