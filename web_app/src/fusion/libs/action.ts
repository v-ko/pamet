import { action as mobxAction } from "mobx";
import { pamet } from "../../facade";

// Since mobx does not provide a way to register a global action middleware,
// we use a global action call stack to track the action nesting.
let _actionCallStack: Array<ActionState> = [];


function processMethod(descriptor: PropertyDescriptor, name: string, issuer: string): PropertyDescriptor {
    const originalMethod = descriptor.value; // Save the original method
    let funcName = `[${issuer}]${name}`;
    descriptor.value = mobxAction(funcName, function (this: any, ...args: any[]) {
        // Create a new action state
        let actionState = new ActionState(funcName);
        actionState.setStarted();
        _actionCallStack.push(actionState);

        // Push the start state of root actions to the appropriate channels
        pamet.rootActionEventsChannel.push(actionState);
        pamet.rawChangesPlusRootActionEventsChannel.push(actionState);

        // Call the original method
        let result = originalMethod.apply(this, args);

        // Complete the action state
        actionState = _actionCallStack.pop()!;
        actionState.setCompleted();

        // Push the completed state of root actions to the appropriate channels
        pamet.rootActionEventsChannel.push(actionState);
        pamet.rawChangesPlusRootActionEventsChannel.push(actionState);

        return result;
    });
    return descriptor;
}

// Overload interface for the action decorator
export interface IActionDecorator {
    // Overload for usage without arguments
    (target: Object, propertyKey: string | symbol, descriptor: PropertyDescriptor): void;

    // Overload for usage with options object
    (options: { name?: string, issuer?: string }): MethodDecorator;
}

export const action: IActionDecorator = function (...args: any[]): any {
    /**
     * A decorator to register a MobX action with additional metadata.
     *
     * This decorator can be applied with or without arguments. When used with arguments,
     * it allows specifying an issuer and an optional custom name for the action.
     * The custom name, if provided, replaces the method's original name in the MobX action context.
     * This is useful for middleware and services to distinguish user-triggered actions from
     * those triggered by services, aiding in functionalities like testing, undo/redo, etc.
     *
     * @param issuer - An optional issuer of the action, defaulting to 'user'.
     *                 Used to categorize the action's origin (e.g., user, system, service).
     * @param name - An optional custom name for the action. If provided, it replaces
     *               the method's original name in the action context.
     * @returns A decorator function that modifies the target method to be a MobX action.
     */

    // Check if it's being used as a decorator (without arguments)
    if (args.length === 3 && typeof args[0] === "function") {
        const [target, key, descriptor] = args as [Object, string | symbol, PropertyDescriptor];
        return processMethod(descriptor, key.toString(), 'user');

    } else if (args.length === 1 && typeof args[0] === 'object') {
        // There's an options dict supplied, which holds the named parameters
        const [options] = args as [{ name?: string, issuer?: string }];

        return function (target: Object, key: string | symbol, descriptor: PropertyDescriptor): PropertyDescriptor {
            const name = options.name || key.toString();
            const issuer = options.issuer || 'user';
            return processMethod(descriptor, name, issuer);
        }
    }
};


export enum ActionRunStates {
    NOT_STARTED = 'NOT_STARTED',
    STARTED = 'STARTED',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED'
}


export class ActionState {
    name: string;
    runState: ActionRunStates;
    startTime: number;
    duration: number;

    constructor(name: string) {
        this.name = name;
        this.runState = ActionRunStates.NOT_STARTED;
        this.startTime = 0;
        this.duration = 0;
    }

    get issuer(): string {
        return this.name.split(']')[0].replace('[', '');
    }

    get started(): boolean {
        return this.runState === ActionRunStates.STARTED;
    }
    get completed(): boolean {
        return this.runState === ActionRunStates.COMPLETED;
    }

    setStarted() {
        this.runState = ActionRunStates.STARTED;
        this.startTime = Date.now();
    }

    setCompleted() {
        this.runState = ActionRunStates.COMPLETED;
        this.duration = Date.now() - this.startTime;
    }
    copy(): ActionState {
        let copy = new ActionState(this.name);
        copy.runState = this.runState;
        copy.startTime = this.startTime;
        copy.duration = this.duration;
        return copy;
    }
}
