from oy3opy import *
from oy3opy.utils.terminal import curses, color
from oy3opy.utils.string import tojson, errString
from oy3opy.utils.file import trytouch, io
from oy3opy.dataflow import Flow
from oy3opy.dataflow.ternimal import App as MessageViewer
from oy3opy.editor import InputBox, Editor
from oy3opy.input import ENTER
from oy3opy.chat import Channel, User, Message, MessageBody, Text
from .core import * # Chat, exec, execTasksChain_once
from typing import Optional
from typing_extensions import Annotated
import typer
import json

help = '''    command      │    description
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

'''

local_channel = Channel()
system = User()

@dataclass
class TaskState:
    name:str
    chain:list
    done:list = None

    def __post_init__(self):
        if self.done is None:
            self.done = []

    def __str__(self) -> str:
        return f'{self.name}({len(self.done)}/{len(self.chain)})'

class ChatState:
    def __str__(self) -> str:
        pass

class State:
    def __init__(self, data):
        self.tasks:dict = data.get('tasks',{})
        self.chats:dict = data.get('chats',{})
    def __str__(self) -> str:
        return f'Tasks: {" ".join([*self.tasks.values()])}    Chats: {" ".join([*self.chats.values()])}'


def backrun(state:TaskState, config:Config, updateview:Callable):
    for group in execTasksChain(state.chain, config):
        state.done.append(group)
        updateview()

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
        self.flow:list[Message] = Flow(loads.get('flow',[]))
        self.pendding = {}

    def listen(self):
        curses.stdscr = curses.initscr()
        curses.stdscr.keypad(True)
        curses.noecho()
        curses.cbreak()
        curses.raw()
        curses.curs_set(0)

        self.height, self.width = curses.stdscr.getmaxyx()
        self.statebar = curses.stdscr.derwin(4, self.width, self.height-4, 0)
        self.viewer = MessageViewer(self.flow, curses.stdscr.derwin(self.height-4, self.width, 0, 0))
        self.inputbox = InputBox(curses.stdscr.derwin(1, self.width, self.height-1, 0), text='', stop=ENTER)
        self.inputarea = Editor(curses.stdscr.derwin(12, self.width, self.height-12, 0))
        self.editor = Editor(curses.stdscr.derwin(self.height, self.width, 0, 0))
        self.editor.subscribe('edit', self.viewer.stop)
        self.editor.subscribe('close', self.viewer.listen)
        self.editor.subscribe('close', self.viewer.render)
        self.viewer.listen()

        self.system_message(color('enter "view 0" to show help','green'), help)
        while True:
            self.update_statebar()
            command = self.inputbox.edit('')
            if not command:
                continue
            if command == 'exit':
                break
            self.exec(command)

        curses.endwin()

    def exec(self, command:str):
        if command.startswith('view '):
            self.view(int(command[5:]))
        elif command.startswith('edit '):
            self.edit(int(command[5:]))
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
        
        self.flow.append(Message(MessageBody(str(id), str(id).rjust(len(str(id))+1)+'| '+title, [Text(content or title)], local_channel, system)))
        return id

    def update_statebar(self, state=None):
        self.statebar.addstr(0,0,''.center(self.width,'─'))
        self.statebar.addstr(1,0, str(state or self.state).center(self.width-1))
        self.statebar.addstr(2,0,''.center(self.width,'─'))
        self.statebar.refresh()

    def input(self, prompt=str, com=None):
        com = com or self.inputbox
        id = self.system_message(prompt)
        value = com.edit('')
        self.flow[id].body.content[0].data = value
        return value

    def view(self, id:int):
        if id in range(len(self.flow)):
            self.editor.edit(self.flow[id].body.content[0], editable=False)
        else:
            self.system_message(color(f'Message with id {id} not found', 'red'))

    def edit(self, id:int):
        if id in range(len(self.flow)):
            origin = self.flow[id].body
            self.flow[id] = Message(MessageBody(origin.id, origin.name, [Text(self.editor.edit(origin.content[0]))], origin.channel, origin.user, origin.forward))
        else:
            self.system_message(color(f'Message with id {id} not found', 'red'))

    def task(self, name:str):
        chain = []
        tasks = []
        changeView = False
        getNext = True
        while True:
            while getNext:
                self.update_statebar(f'Chains:{len(chain)}    Tasks:{len(tasks)}')
                prompt = self.input('enter prompt', self.inputarea)
                if not prompt:
                    break
                if not changeView:
                    changeView = True
                    overflow = max(0, len(self.viewer) - self.viewer.height + 8)
                    self.viewer.height -= 8
                    self.viewer.offset += overflow
                    self.viewer.render()

                model = self.input(f'enter model name(empty to set default)')
                context = self.input('enter context(empty to set default)', self.inputarea)
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
        
        if changeView:
            self.viewer.height += 8

        task = TaskState(name, chain)
        self.state.tasks[name] = task
        backrun(task, self.config, self.update_statebar)

    def chat(self, name:str):
        if name == 'help':
            return self.chat_help()
        pass

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

    def chat_help():
        pass

def main(
    prompt:Annotated[Optional[str], typer.Argument()] = None,
    model:Optional[str]='bing',
    context:Optional[str]='',
    cookie:Optional[str]=None,
    proxy:Optional[str]=None,
    config:Optional[str]=None,
    loads:Optional[str]=None,
):

    cookies = {}
    contexts = {}
    proxies = {}
    if config:
        try:
            with io(config) as f:
                o = json.load(f)
            cookies = o.get('cookies', {})
            contexts = o.get('contexts', {})
            proxies = o.get('proxies', {})
        except (IOError, ValueError) as e:
            return typer.echo(color(f'[ERROR] {e}', 'red'))

    if not cookie and not cookies:
        return typer.echo(color('[ERROR] one of cookie or config cookies must exist', 'red'))

    if prompt:
        with io(cookie or cookies[model]) as f:
            for chunk in exec(prompt, context, model, Config({'cookie': json.load(f), 'cookies': cookies, 'proxy': proxy, 'proxies': proxies})):
                print(chunk, end='', flush=True)
    else:
        InteractiveCLI(
            model,
            json.load(io(cookie)),
            context,
            proxy,
            {model: json.load(io(path)) for (model, path) in cookies.items()},
            contexts,
            proxies,
            json.load(io(loads)) if loads else {},
        ).listen()

def app():
    typer.run(main)
