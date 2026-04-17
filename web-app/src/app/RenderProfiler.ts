export class RenderProfiler {
    mouseMoveTime?: number;
    renderIds: Set<number> = new Set();
    // mouseMoveEventCounts: number = 0;
    reactRender?: number;
    reactRenderCounts: number = 0;

    mobxReaction?: number;
    mobxReactionCounts: number = 0;

    directRendererInvoke?: number;
    directRendererInvokeCounts: number = 0;

    propSetSkips: number = 0;

    constructor() {
        // clear
    }

    addRenderId(renderId: number) {
        // if (this.mouseMoveTime || !renderId) {
        //     this.propSetSkips++;
        //     return;
        // }
        if (!this.mouseMoveTime) {
            this.mouseMoveTime = performance.now();
            // log.info('Starting render with id:', renderId);
        }
        // log.info(`Render id added: ${renderId}.`);
        this.renderIds.add(renderId);
    }
    setReactRender(renderId: number) {
        this.reactRenderCounts++;
        if (renderId && this.renderIds?.has(renderId)) {
            this.propSetSkips++;
        }
        this.reactRender = performance.now();
    }
    setMobxReaction(renderId: number) {
        this.mobxReactionCounts++;
        if (renderId && this.renderIds?.has(renderId)) {
            this.propSetSkips++;
        }
        this.mobxReaction = performance.now();
    }
    setDirectRendererInvoke(renderId: number) {
        this.directRendererInvokeCounts++;
        if (renderId && this.renderIds?.has(renderId)) {
            this.propSetSkips++;
        }
        this.directRendererInvoke = performance.now();
    }
    logTimeSinceMouseMove(message: string, renderId: number) {
        if (!renderId || !this.renderIds?.has(renderId) || !this.mouseMoveTime) {
            // log.info(`Skipping for request with mouse position ${renderId}.`);
            return;
        }
        let timeSinceMouseMove = performance.now() - this.mouseMoveTime;
        // log.info(`${message} - Time since last mouse move: ${timeSinceMouseMove} ms. Skip count: ${this.propSetSkips}`);
    }

    clear(renderId: number): any {
        // log.info(`Clearing render profiler data. Counts: renderIds.size=${this.renderIds.size}, reactRender=${this.reactRenderCounts}, mobxReaction=${this.mobxReactionCounts}, directRendererInvoke=${this.directRendererInvokeCounts}, propSetSkips=${this.propSetSkips}`);
        if ((!renderId || !this.renderIds?.has(renderId))
            // && !(this.mouseMoveTime && (this.mouseMoveTime + 1000 > performance.now()))
        ) { // if the mouse coordinates are from an e.g. skipped render - timeout and clear
            this.propSetSkips++;
            return;
        }

        let stats = {};

        this.mouseMoveTime = undefined;

        this.renderIds.clear();
        this.reactRender = undefined;
        this.reactRenderCounts = 0;

        this.mobxReaction = undefined;
        this.mobxReactionCounts = 0;

        this.directRendererInvoke = undefined;
        this.directRendererInvokeCounts = 0;

        this.propSetSkips = 0;
    }
}
