class Ask {
    constructor(endpoint, model, cookie, init = true) {
        this.endpoint = endpoint
        this.model = model
        this.cookie = cookie
        if (init) return this.reset()
    }

    reset() {
        return new Promise(ok => {
            if (this.ws) this.close()
            this.ws = new WebSocket(this.endpoint)
            this.ws.onopen = () => {
                this.ws.send(this.message({
                    'model': this.model,
                    'cookie': this.cookie,
                }))
                ok(this)
            }
            this.ws.onmessage = e => this.handle_message(JSON.parse(e.data))
        })
    }

    close() {
        this.ws.close()
        this.ws = null
    }

    handle_message({ type, event, message }) {
        switch (type) {
            case 'message':
                this.onmessage?.(message)
                break
            case 'event':
                this.onevent?.(event, message)
                break
            case 'signal':
                this.onsignal?.(message)
                break
        }
    }

    send(message, context) {
        this.ws.send(this.message({
            'context': context,
            'prompt': message,
        }))
    }

    message(msg) {
        return JSON.stringify(msg)
    }
}


class Chat extends Ask {
    constructor(name, endpoint, model, cookie) {
        super(endpoint, model, cookie, false)
        this.name = name
        this.context = ''
        this.events = []
        this.messages = ['']
        this.msgid = 0
        return this.reset()
    }

    update(context) {
        this.context = context
        this.ws.send(this.message({
            'id': this.name,
            'context': context,
        }))
    }

    message(msg) {
        msg.id = this.name
        return super.message(msg)
    }

    handle_message(e) {
        switch (e.type) {
            case 'message':
                this.messages[this.msgid] += e.message
                break
            case 'event':
                this.events.push(e)
                break
            case 'signal':
                this.messages[++this.msgid] = ''
                break
            default:
                console.log(e)
        }
        super.handle_message(e)
    }
}