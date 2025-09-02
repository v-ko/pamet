import { getLogger } from "fusion/logging";

const log = getLogger('AnimationService');

export type EasingFunction = 'linear' | 'easeInOut' | 'easeIn' | 'easeOut';

export abstract class BaseAnimation {
    readonly id: string;
    readonly type: string;
    readonly targetId?: string; // For auto-overriding animations with same type+targetId
    readonly startTime: number;
    readonly duration: number;
    readonly easingFunction: EasingFunction;

    constructor(
        id: string,
        type: string,
        startTime: number,
        duration: number,
        easingFunction: EasingFunction,
        targetId?: string
    ) {
        this.id = id;
        this.type = type;
        this.startTime = startTime;
        this.duration = duration;
        this.easingFunction = easingFunction;
        this.targetId = targetId;
    }
}

export class AnimationService {
    private _animations: Map<string, BaseAnimation> = new Map();
    private _nextId: number = 1;

    constructor() {
        log.info('AnimationService initialized');
    }

    /**
     * Add a new animation to the service
     * Auto-overrides any existing animation with the same type and targetId
     * Performs implicit cleanup of expired animations
     */
    add(animation: Omit<BaseAnimation, 'id'>): BaseAnimation {
        // Implicit cleanup on every add
        this.cleanup();

        // Auto-override any existing animation with same type and targetId
        if (animation.targetId) {
            const toRemove: string[] = [];
            for (const [id, existingAnimation] of this._animations) {
                if (existingAnimation.type === animation.type &&
                    existingAnimation.targetId === animation.targetId) {
                    toRemove.push(id);
                }
            }
            toRemove.forEach(id => this._animations.delete(id));

            if (toRemove.length > 0) {
                log.info('Auto-overrode existing animations', {
                    type: animation.type,
                    targetId: animation.targetId,
                    count: toRemove.length
                });
            }
        }

        const id = this._generateId();
        const fullAnimation = { ...animation, id };

        this._animations.set(id, fullAnimation);
        log.info('Added animation', { id, type: animation.type, duration: animation.duration });

        return fullAnimation;
    }

    /**
     * Get animations by type (with implicit cleanup)
     */
    getByType(type: string): BaseAnimation[] {
        this.cleanup();
        return Array.from(this._animations.values())
            .filter(animation => animation.type === type);
    }

    /**
     * Remove all expired animations based on current time (internal method)
     */
    private cleanup(currentTime: number = Date.now()): void {
        const toRemove: string[] = [];

        for (const [id, animation] of this._animations) {
            if (currentTime >= animation.startTime + animation.duration) {
                toRemove.push(id);
            }
        }

        toRemove.forEach(id => this._animations.delete(id));

        if (toRemove.length > 0) {
            log.info('Cleaned up expired animations', { count: toRemove.length });
        }
    }

    private _generateId(): string {
        return `anim_${this._nextId++}`;
    }
}
