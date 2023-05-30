from oy3opy import *
from oy3opy.utils.terminal import curses, color
from oy3opy.utils.string import tojson, errString, splitstrings_bywidth
from oy3opy.utils.file import trytouch, loads, dumps
from oy3opy.dataflow import Flow
from oy3opy.dataflow.ternimal import App as MessageViewer
from oy3opy.editor import InputBox, Editor
from oy3opy.input import ENTER
from oy3opy.chat import Channel, User, Message, MessageBody, Text, Notice, Body
from oy3opy.ai.core import * # Chat, exec, execTasksChain_once
import asyncio
import threading
import typer

help = '''    command      │    description
─────────────────────────────────────────────────────────────
    exit         │    exit app
    chat NAME    │    start a chat
    task NAME    │    start a task
    view NUM     │    show details of message
    edit NUM     │    edit json of message
    save path    │    save your state for load
  (chat) NUM     │    view the content of message

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

first chat help:
1. input 'chat 0', then press CTRL+D
2. wait for create chat conversation (chat initing...)
3. press CTRL+D (skip model input, use default model bing)
4. input 'hello', then press CTRL+D
5. press CTRL+D (ask without context)
6. wait for message ' N| recived answer of ask: hello'
7. input 'N', then press CTRL+D
8. see the answer, then press CTRL+D to exit
9. input 'NUM', to see another message or search result or others
10. loop the action 3-9
11. press CTRL+D to exit chat
12. input 'chat 0' back to chat
13. exit to exit app
'''

local_channel = Channel()
system = User()

@dataclass
class TaskState:
    name:str
    flow:Flow
    updateview:Callable
    chain:list
    config:Config
    done:list = None

    def __post_init__(self):
        if self.done is None:
            self.done = []
        for group in execTasksChain(self.chain, self.config):
            self.done.append(group)
            self.updateview()
    def __str__(self) -> str:
        return f'{self.name}({len(self.done)}/{len(self.chain)})'


class ChatState(Chat):
    def __init__(self, name:str, flow:Flow, model: str, cookie: dict, listeners: dict, proxy: str):
        super().__init__(model, cookie, listeners, proxy)
        self.name = name
        self.flow = flow

    def update(self, context):
        async def _(self):
            await super().update(context)
        Task(_,(self,)).do()

    def send(self, message):
        id = len(self.flow)
        self.flow.append(Notice(Body(str(id), str(id).rjust(len(str(id))+1)+f'| (waiting) send message:{message}', [Text('waiting answer')])))
        async def _(self):
            id = None
            answer = ''
            async for chunk in super().send(message):
                if not id:
                    id = len(self.flow)
                    self.flow.append(Message(MessageBody(str(id), str(id).rjust(len(str(id))+1)+f'| recived answer of ask:{message}', [Text('')], local_channel, system)))
                answer += chunk
                self.flow[id].body.content[0].data = answer
                self.flow.change(id, self.flow[id])
            return answer
        self.flow[id] = Notice(Body(str(id), str(id).rjust(len(str(id))+1)+f'| (done) send message:{message}', [Text(asyncio.run(_(self)))]))
        self.flow.change(id, self.flow[id])


    def __str__(self) -> str:
        return f'{self.name}({len(self.messages)})'

def eventprinter(flow:Flow):
    def _(event:dict):
        id = len(flow)
        flow.append(Notice(Body(str(id), str(id).rjust(len(str(id))+1)+f'| event:{event["event"]}', [Text(str(event['message']))])))
    return _

class State:
    def __init__(self, data):
        self.tasks:dict = data.get('tasks',{})
        self.chats:dict = data.get('chats',{})
    def __str__(self) -> str:
        return f'Tasks: {" ".join(["",*map(str, [*self.tasks.values()])])}    Chats: {" ".join(["", *map(str, [*self.chats.values()])])}'

@commands(['listen'])
class InteractiveCLI:
    def __init__(self, model:str, cookie:dict, context:str, proxy:str, cookies:dict, contexts:dict, proxies:dict, loads:dict={}):
        self.config = Config({
            name: loads.get(name, value) for (name, value) in [
                ('model', model),
                ('cookie', cookie),
                ('context', context),
                ('proxy', proxy),
                ('cookies', cookies),
                ('contexts', contexts),
                ('proxies', proxies),
        ]})
        self.state = State(loads.get('state',{}))
        self.flow:list = Flow(loads.get('flow',[]))
        self.pendding = {}
        self.inputing = None
        self.editing = None
        self.changeView = False

    def listen(self):
        curses.stdscr = curses.initscr()
        curses.stdscr.keypad(True)
        curses.noecho()
        curses.cbreak()
        curses.raw()
        curses.curs_set(0)

        self.height, self.width = curses.stdscr.getmaxyx()
        self.statebar = curses.stdscr.derwin(4, self.width, self.height-4, 0)
        self.viewer = MessageViewer(self.flow, curses.stdscr.derwin(self.height-4, self.width, 0, 0), afterRender=self.update_inputing)
        self.inputbox = InputBox(curses.stdscr.derwin(1, self.width, self.height-1, 0), text='', stop=ENTER)
        self.inputarea = Editor(curses.stdscr.derwin(12, self.width, self.height-12, 0))
        self.editor = Editor(curses.stdscr.derwin(self.height, self.width, 0, 0))
        self.editor.subscribe('edit', self.viewer.stop)
        self.editor.subscribe('close', self.viewer.listen)
        self.editor.subscribe('close', self.viewer.render)
        self.flow.subscribe('change', self.viewer.render)
        self.flow.subscribe('change', self.update_editing)
        self.viewer.listen()

        self.system_message(color('enter "view 0" to show help','green'), help)
        while True:
            self.update_statebar()
            if self.changeView:
                self.viewer.height += 8
                self.changeView = False
            self.inputing = self.inputbox
            command = self.inputbox.edit('')
            self.inputing = None
            if not command:
                continue
            if command == 'exit':
                break
            self.exec(command)

        curses.endwin()

    def exec(self, command:str):
        if command.startswith('view '):
            self.view(int(command[5:] or 0))
        elif command.startswith('edit '):
            self.edit(int(command[5:] or 0))
        elif command.startswith('task '):
            self.task(command[5:].strip())
        elif command.startswith('chat '):
            self.chat(command[5:].strip())
        elif command.startswith('save '):
            self.save(command[5:].strip())
        else:
            self.system_message(color(f'[ERROR] Command not found: {command}', 'red'))

    def system_message(self, title:str, content:str = None):
        id = len(self.flow)
        
        self.flow.append(Notice(Body(str(id), str(id).rjust(len(str(id))+1)+'| '+title, [Text(content or title)])))
        return id

    def update_statebar(self, state=None):
        self.statebar.addstr(0,1,''.center(self.width-2,'─'))
        self.statebar.addstr(1,1, str(state or self.state).center(self.width-2))
        self.statebar.addstr(2,1,''.center(self.width-2,'─'))
        self.statebar.refresh()

    def update_inputing(self, *args):
        if self.inputing is not None:
            self.inputing.render()

    @throttle(0.25)
    def update_editing(self, index, newItem, oldItem):
        if self.editing == index:
            text:str = newItem.body.content[0].data
            self.editor.update(text, write=False)
            self.editor.render()

    def input(self, prompt=str, com=None):
        com = com or self.inputbox
        if (com == self.inputarea) and (not self.changeView):
            self.changeView = True
            overflow = max(0, len(self.viewer) - self.viewer.height + 8)
            self.viewer.height -= 8
            self.viewer.offset += overflow
            self.viewer.render()

        id = self.system_message(prompt)
        self.inputing = com
        value = com.edit('')
        self.inputing = None
        self.flow[id].body.content[0].data = value
        return value

    def view(self, id:int):
        if id in range(len(self.flow)):
            self.editing = id
            self.editor.edit(self.flow[id].body.content[0], editable=False)
            self.editing = None
        else:
            self.system_message(color(f'Message with id {id} not found', 'red'))

    def edit(self, id:int):
        if id in range(len(self.flow)):
            self.editing = id
            origin = self.flow[id].body.content[0]
            origin.data = self.editor.edit(origin.data)
            self.editing = None
        else:
            self.system_message(color(f'Message with id {id} not found', 'red'))

    def task(self, name:str):
        chain = []
        tasks = []
        getNext = True
        while True:
            while getNext:
                self.update_statebar(f'Chains:{len(chain)}    Tasks:{len(tasks)}')
                prompt = self.input('enter prompt(empty to end task input)', self.inputarea)
                if not prompt:
                    break

                model = self.input(f'enter model name(empty to {self.config.model})') or self.config.model
                context = self.input('enter context(empty to set default)', self.inputarea) or getattr(self.config, model)['context']
                tasks.append({
                    'model': model,
                    'prompt':prompt,
                    'context':context,
                })
            if tasks:
                chain.append(tasks)
                self.update_statebar(f'Chains:{len(chain)}    Tasks:{len(tasks)}')
                tasks = []
                choice = self.input('chain to next tasks?[y/n(default)]')
                if not choice.startswith('y'):
                    getNext = False
            else:
                break

        self.state.tasks[name] = TaskState(name, self.flow, self.update_statebar, chain, self.config)

    def chat(self, name:str):
        chat = self.state.chats.get(name, None)
        if chat is None:
            model = self.input(f'enter model(empty to {self.config.model})', self.inputbox) or self.config.model
            config = getattr(self.config, model)
            self.system_message('chat initing...')
            self.state.chats[name] = ChatState(name, self.flow, model, config['cookie'], dict.fromkeys(Events(model), [eventprinter(self.flow)]), config['proxies'])
            chat = self.state.chats[name]

        while True:
            prompt = self.input('enter prompt(empty to exit chat)', self.inputarea)
            while prompt.isdigit():
                self.edit(int(prompt))
                prompt = self.inputarea.edit('')
            if not prompt:
                break
            context = self.input('enter context(empty to set default)', self.inputarea)
            def task():
                chat.update(context)
                chat.send(prompt)
            t = threading.Thread(target=task)
            t.setDaemon(True)
            t.start()


    def save(self, path:str):
        err = trytouch(path, tojson({
            'config': self.config,
            'state': self.state,
            'flow': self.flow,
        }))
        if err == None:
            self.system_message(color(f'[INFO] File saved to {path}', 'green'))
        else:
            self.system_message(color(f'File save failed due to {errString(err)}', 'red'))

def main(
    prompt:Annotated[Optional[str], typer.Argument()] = None,
    model:Optional[str]='bing',
    context:Optional[str]='',
    cookie:Optional[str]=None,
    proxy:Optional[str]=None,
    config:Optional[str]=None,
    load:Optional[str]=None,
):

    cookies = {}
    contexts = {}
    proxies = {}
    if config:
        try:
            o = loads(config)
            cookies = o.get('cookies', {})
            contexts = o.get('contexts', {})
            proxies = o.get('proxies', {})
        except (IOError, ValueError) as e:
            return typer.echo(color(f'[ERROR] {e}', 'red'))

    if not cookie and not cookies:
        return typer.echo(color('[ERROR] one of cookie or config cookies must exist', 'red'))

    if prompt:
        async def asyncExec():
            async for chunk in exec(prompt, context, model, Config({'cookie': loads(cookie or cookies[model]), 'cookies': cookies, 'proxy': proxy, 'proxies': proxies})):
                print(chunk, end='', flush=True)
        asyncio.run(asyncExec())
    else:
        InteractiveCLI(
            model,
            dict([(c['name'], c['value']) for c in loads(cookie)]),
            context,
            proxy,
            {model: dict([(c['name'], c['value']) for c in loads(path)]) for (model, path) in cookies.items()},
            contexts,
            proxies,
            loads(load) if load else {},
        ).listen()

def app():
    typer.run(main)

if __name__ == '__main__':
    app()