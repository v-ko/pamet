// """It supports adding named channels on which to subscribe handlers and then
// dispatch messages (which are arbitrary python objects).

import { get_logger } from "../logging"
import { Callable, get_counted_id } from "../util"

// Dispatching and invoking the handlers are both done on the same thread, so
// it's expected that the subscribed callables are light, since the main purpose
// of fusion is GUI rendering and blocking the main loop would cause freezing.
// """


let log = get_logger('channel.ts')

// # --------------Dispatcher related-------------------
let _channels = {}
let MISSING = 'MISSING'


export function unsubscribe_all() {
    for (let channel_name in _channels) {
        let channel = _channels[channel_name]
        for (let sub_props in channel.subscriptions) {
            let sub = channel.subscriptions[sub_props]
            sub.unsubscribe()
        }
    }
}


export class SubscriptionTypes {
    static CHANNEL = 1
    static ENTITY = 2
    static INVALID = 0
}


export class Subscription {
    public id: number
    public handler: Callable
    public channel: Channel
    public index_val: any

    constructor(handler: Callable, channel: Channel, index_val = MISSING) {
        this.id = get_counted_id(this)
        this.handler = handler
        this.channel = channel
        this.index_val = index_val
    }

    props() {
        return [this.handler, this.channel, this.index_val]
    }

    unsubscribe() {
        this.channel.remove_subscribtion(this)
    }
}

export class Channel {
    name: string
    index_key: Callable | null
    filter_key: Callable | null
    subscriptions: { [key: string]: Subscription }
    index: { [key: string]: any[] }

    constructor(name: string, index_key: Callable | null = null, filter_key: Callable | null = null) {
        this.name = name
        this.index_key = index_key
        this.filter_key = filter_key
        this.subscriptions = {}
        this.index = {}

        if (name in _channels) {
            throw new Error('A channel with this name already exists')
        }
        _channels[name] = this
    }

    push(message) {
        if (this.filter_key) {
            if (!this.filter_key(message)) {
                return
            }
        }

        for (let sub_props in this.subscriptions) {
            let sub = this.subscriptions[sub_props]
            if (this.index_key && sub.index_val !== MISSING) {
                if (this.index_key(message) !== sub.index_val) {
                    continue
                }
            }

            log.info(`Queueing ${sub.handler} for ${message} on channel_name=${this.name}`)
            call_delayed(sub.handler, 0, [message])
        }
    }

    subscribe(handler: Callable, index_val: any = MISSING) {
        let sub = new Subscription(handler, _channels[this.name], index_val)
        this.add_subscribtion(sub)
        return sub
    }

    add_subscribtion(subscribtion) {
        if (subscribtion.props() in this.subscriptions) {
            throw new Error(`Subscription with props ${subscribtion.props()} already added to channel ${this.name}`)
        }

        this.subscriptions[subscribtion.props()] = subscribtion
    }

    remove_subscribtion(subscribtion) {
        if (!(subscribtion.props() in this.subscriptions.indexOf)) {
            throw new Error(
                `Cannot unsubscribe missing subscription with props ${subscribtion.props()} in channel ${this.name}`)
        }

        delete this.subscriptions[subscribtion.props()]
    }
}

function call_delayed(handler: Callable, arg1: number, arg2: any[]) {
    throw new Error("Function not implemented.")
}

