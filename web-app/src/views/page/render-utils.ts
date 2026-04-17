import { pamet } from "@/core/facade";
import { BaseAnimation, EasingFunction } from "@/services/AnimationService";
import { Point2D } from "fusion/primitives/Point2D";
import { AUTO_NAVIGATE_TRANSITION_DURATION } from "@/actions/page";

export class PageAnimation extends BaseAnimation {
    readonly type = 'pageNavigation' as const;
    readonly targetId: string; // pageId for verification and auto-override
    readonly startState: {
        pageId: string; // For verification purposes
        viewportCenter: Point2D;
        viewportHeight: number;
    };
    readonly endState: {
        viewportCenter: Point2D;
        viewportHeight: number;
    };

    constructor(
        id: string,
        startTime: number,
        duration: number,
        easingFunction: EasingFunction,
        targetId: string,
        startState: { pageId: string; viewportCenter: Point2D; viewportHeight: number },
        endState: { viewportCenter: Point2D; viewportHeight: number }
    ) {
        super(id, 'pageNavigation', startTime, duration, easingFunction, targetId);
        this.targetId = targetId;
        this.startState = startState;
        this.endState = endState;
    }

    /**
     * Static factory method to create and add a page navigation animation
     */
    static viewportChangeAnimation(
        pageId: string,
        currentCenter: Point2D,
        currentHeight: number,
        targetCenter: Point2D,
        targetHeight: number,
        duration: number = AUTO_NAVIGATE_TRANSITION_DURATION * 1000,
        easingFunction: EasingFunction = 'easeInOut'
    ): PageAnimation {
        const animation = pamet.animationService.add({
            type: 'pageNavigation',
            targetId: pageId,
            startTime: Date.now(),
            duration: duration,
            easingFunction: easingFunction,
            startState: {
                pageId: pageId,
                viewportCenter: currentCenter.copy(),
                viewportHeight: currentHeight
            },
            endState: {
                viewportCenter: targetCenter.copy(),
                viewportHeight: targetHeight
            }
        } as any) as PageAnimation; // Cast needed for now

        return animation;
    }
}


/**
 * Get the interpolated state for a page navigation animation
 */
export function getPageNavigationState(
    animation: PageAnimation,
    currentTime: number = Date.now()
): { viewportCenter: Point2D; viewportHeight: number } {
    const elapsed = currentTime - animation.startTime;
    const progress = Math.min(Math.max(elapsed / animation.duration, 0), 1);

    // Apply easing function
    let easedProgress: number;
    switch (animation.easingFunction) {
        case 'linear':
            easedProgress = progress;
            break;
        case 'easeIn':
            easedProgress = progress * progress;
            break;
        case 'easeOut':
            easedProgress = 1 - Math.pow(1 - progress, 2);
            break;
        case 'easeInOut':
            easedProgress = progress < 0.5
                ? 2 * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            break;
        default:
            easedProgress = progress;
    }

    // Interpolate viewport center
    const startCenter = animation.startState.viewportCenter;
    const endCenter = animation.endState.viewportCenter;
    const centerDelta = endCenter.subtract(startCenter);
    const currentCenter = startCenter.add(centerDelta.multiply(easedProgress));

    // Interpolate viewport height
    const startHeight = animation.startState.viewportHeight;
    const endHeight = animation.endState.viewportHeight;
    const currentHeight = startHeight + (endHeight - startHeight) * easedProgress;

    return {
        viewportCenter: currentCenter,
        viewportHeight: currentHeight
    };
}
