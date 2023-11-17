export type HandlerFunction = (message: any) => void;
let CREATING_CHANNEL: string | null = null;


export class Subscription {
    id: number;
    handler: HandlerFunction;
    channel: Channel;
    indexVal: any;

    constructor(handler: HandlerFunction, channel: Channel, indexVal: any = undefined) {
        this.id = Date.now() + Math.random(); // A unique identifier
        this.handler = handler;
        this.channel = channel;
        this.indexVal = indexVal;
    }

    unsubscribe(): void {
        this.channel.removeSubscription(this.handler, this.indexVal);
    }
}

export class Channel {
    name: string;
    indexKey: ((message: any) => any) | null;
    filterKey: ((message: any) => boolean) | null;
    indexedSubscriptions: Map<any, Map<symbol, HandlerFunction>>;
    nonIndexedSubscriptions: Map<symbol, HandlerFunction>;

    constructor(name: string, indexKey?: ((message: any) => any) | null, filterKey?: ((message: any) => boolean) | null) {
        this.name = name;
        this.indexKey = indexKey || null;
        this.filterKey = filterKey || null;
        this.indexedSubscriptions = new Map();
        this.nonIndexedSubscriptions = new Map();

        // Ensure constructor is not called directly
        if(CREATING_CHANNEL !== name) {
            throw new Error('Do not call Channel constructor directly, use fusion.libs.add() instead.');
        }
    }

    push(message: any): void {
        if (this.filterKey && !this.filterKey(message)) {
            return;
        }

        const messageIndex = this.indexKey ? this.indexKey(message) : null;

        // Handle indexed messages
        if (messageIndex !== null && this.indexedSubscriptions.has(messageIndex)) {
            const handlers = this.indexedSubscriptions.get(messageIndex);
            handlers?.forEach((handler) => callDelayed(handler, message));
        }

        // Handle non-indexed messages
        this.nonIndexedSubscriptions.forEach((handler) => {
            callDelayed(handler, message);
        });
    }

    subscribe(handler: HandlerFunction, indexVal: any = undefined): Subscription {
        const handlerSymbol = Symbol.for(handler.toString());
        if (indexVal !== undefined) {
            // Indexed subscription
            let handlersMap = this.indexedSubscriptions.get(indexVal);
            if (!handlersMap) {
                handlersMap = new Map();
                this.indexedSubscriptions.set(indexVal, handlersMap);
            }
            handlersMap.set(handlerSymbol, handler);
        } else {
            // Non-indexed subscription
            this.nonIndexedSubscriptions.set(handlerSymbol, handler);
        }

        return new Subscription(handler, this, indexVal);
    }

    removeSubscription(handler: HandlerFunction, indexVal: any = undefined): void {
        const handlerSymbol = Symbol.for(handler.toString());
        if (indexVal !== undefined) {
            // Remove indexed subscription
            const handlersMap = this.indexedSubscriptions.get(indexVal);
            handlersMap?.delete(handlerSymbol);
            if (handlersMap && handlersMap.size === 0) {
                this.indexedSubscriptions.delete(indexVal);
            }
        } else {
            // Remove non-indexed subscription
            this.nonIndexedSubscriptions.delete(handlerSymbol);
        }
    }
}

function callDelayed(handler, message) {
    queueMicrotask(() => {
        handler(message);
    });
}

// Store for all channels, similar to _channels dictionary in the Python code.
const channels = new Map<string, Channel>();


/**
 * Registers a new channel.
 * @param name The name of the channel.
 * @param indexKey Optional function to generate an index key for messages.
 * @param filterKey Optional function to determine if a message should be processed.
 * @returns The newly created Channel instance.
 * @throws If a channel with the same name already exists.
 */
export function addChannel(
    name: string,
    indexKey?: (message: any) => any,
    filterKey?: (message: any) => boolean
  ): Channel {
    if (channels.has(name)) {
      throw new Error('A channel with this name already exists');
    }
    // create the channel without using the constructor directly
    CREATING_CHANNEL = name;

    const channel = new Channel(name, indexKey, filterKey);
    channels.set(name, channel);

    CREATING_CHANNEL = null;
    return channel;
  }

  /**
   * Removes a channel by its name.
   * @param name The name of the channel to remove.
   * @returns True if the channel was successfully removed, false otherwise.
   */
 export function removeChannel(name: string) {
    if (!channels.has(name)) {
        throw new Error(`Channel with name "${name}" does not exist and cannot be removed.`);
      }
      channels.delete(name);
  }


// For testing

export function unsubscribeAll(): void {
    channels.forEach((channel) => {
        channel.indexedSubscriptions.clear();
        channel.nonIndexedSubscriptions.clear();
    });
}

export function clearChannels(): void {
    channels.clear();
}
