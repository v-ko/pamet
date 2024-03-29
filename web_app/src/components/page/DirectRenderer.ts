import { ArrowViewState } from "../arrow/ArrowViewState";
import { Viewport } from "./Viewport";
import { ElementViewState } from "./ElementViewState";
import { PageMode, PageViewState } from "./PageViewState";
import { NoteViewState } from "../note/NoteViewState";
import { ARROW_SELECTION_THICKNESS_DELTA, DRAG_SELECT_COLOR, IMAGE_CACHE_PADDING, MAX_RENDER_TIME, SELECTION_OVERLAY_COLOR } from "../../constants";
import { getLogger } from "../../fusion/logging";
import { color_to_css_rgba_string, drawCrossingDiagonals } from "../../util";
import { Rectangle } from "../../util/Rectangle";
import { ElementView, getElementView } from "../../elementViewLibrary";
import { ArrowCanvasView } from "../arrow/ArrowCanvasView";

let log = getLogger('CanvasCacheService');

const MAX_CACHE_IMAGE_DIM = 1024;

export enum DrawMode {
    NONE,
    DENOVO,
    CACHE,
    PATTERN
}

const MIN_RERENDER_TIME = 5; // ms

const selectionColor = color_to_css_rgba_string(SELECTION_OVERLAY_COLOR);
const dragSelectRectColor = color_to_css_rgba_string(DRAG_SELECT_COLOR);

function renderPattern(ctx: CanvasRenderingContext2D, noteVS: NoteViewState) {
    let note = noteVS.note;
    ctx.strokeStyle = color_to_css_rgba_string(note.style.color);
    let rect = note.rect();
    drawCrossingDiagonals(ctx, rect.x, rect.y, rect.width(), rect.height(), 20);
}


export class CanvasPageRenderer {
    private _nvsCache: Map<NoteViewState, ImageBitmap> = new Map();
    private _nvsCacheSize: number = 0;
    private renderTimeout: NodeJS.Timeout | null = null;
    private _followupRenderSteps: number = 0;
    // Image cache: one per nvs, and clear
    private _imageCache: Map<string, HTMLImageElement> = new Map();

    get nvsCacheSize(): number {
        return this._nvsCacheSize;
    }

    // getImage(src: string): HTMLImageElement | null {
    //     // Lazy load image
    //     let image = this._imageCache.get(src);
    //     if (image === undefined) {
    //         image = new Image();
    //         image.src = src;
    //         this._imageCache.set(src, image);
    //     }
    //     return image;
    // }

    getImage(src: string): HTMLImageElement | null {
        console.log('-----------------getImage', src)
        let img = document.querySelector(`img[src="${src}"]`) as HTMLImageElement;
        return img;
    }
    nvsCache(noteViewState: NoteViewState): ImageBitmap | undefined {
        return this._nvsCache.get(noteViewState);
    }

    setNvsCache(noteViewState: NoteViewState, imageBitmap: ImageBitmap) {
        if (this._nvsCache.has(noteViewState)) {
            this.deleteNvsCache(noteViewState);
        }

        this._nvsCache.set(noteViewState, imageBitmap);
        let imageSize = imageBitmap.width * imageBitmap.height * 4;
        this._nvsCacheSize += imageSize;
    }
    deleteNvsCache(noteViewState: NoteViewState) {
        let imageBitmap = this._nvsCache.get(noteViewState);
        if (imageBitmap !== undefined) {
            this._nvsCache.delete(noteViewState);
            let imageSize = imageBitmap.width * imageBitmap.height * 4;
            this._nvsCacheSize -= imageSize;
            imageBitmap.close();
        }
    }

    displayRect(noteVS: NoteViewState, viewport: Viewport): Rectangle {
        let rect = viewport.projectRect(noteVS.note.rect());
        return rect;
    }

    cacheRectRealSpace(noteVS: NoteViewState, viewport: Viewport): Rectangle {
        /** Returns a rect, expanded to fit the pixel grid */

        // # Drawing on the cache image needs to be
        // # done with an offset = display_rect.x() % 1 otherwise there will be
        // # visual artefats at the boundaries of adjacent notes.
        // # RIP a few more hours of tracing those.
        // 2024: add a few more hours for the DPR correction

        let nvsCacheRectReal = this.cacheRectAfterDPR(noteVS, viewport);
        // Reverse DPR correction
        const dpr = viewport.devicePixelRatio;
        let [x, y, w, h] = nvsCacheRectReal.data();
        nvsCacheRectReal = new Rectangle(x / dpr, y / dpr, w / dpr, h / dpr);
        return viewport.unprojectRect(nvsCacheRectReal);
    }

    drawElement(context: CanvasRenderingContext2D, elementVS: ElementViewState) {
        let element = elementVS.element();
        let ViewType: ElementView<any>;
        try {
            ViewType = getElementView(element.constructor as any);
        } catch (e) {
            log.error('Skipping drawing for element (no ViewType found)', element);
            return;
        }
        let view
        try {
            view = new ViewType(this, elementVS);
        } catch (e) {
            log.error('Error creating view for element', element, e);
            return;
        }
        try {
            view.render(context);
        } catch (e) {
            log.error('Error rendering element', element, e);
        }
    }

    cacheRectAfterDPR(noteVS: NoteViewState, viewport: Viewport): Rectangle {
        const dpr = viewport.devicePixelRatio;
        const adjustedPadding = Math.round(IMAGE_CACHE_PADDING * dpr);

        const displayRect = this.displayRect(noteVS, viewport);

        // use floor to round down
        let [x, y, w, h] = displayRect.data();
        x = Math.floor(x * dpr) - adjustedPadding;
        y = Math.floor(y * dpr) - adjustedPadding;
        w = Math.floor(w * dpr) + 2 * adjustedPadding;
        h = Math.floor(h * dpr) + 2 * adjustedPadding;

        return new Rectangle(x, y, w, h);
    }

    renderNoteView_toCache(mainCtx: CanvasRenderingContext2D, noteVS: NoteViewState, viewport: Viewport, dpr: number): boolean {
        /** Renders the noteView to the cache.
         * @returns false if the operation failed (e.g. note is too big)
         */
        // Setup the projection matrix. We'll scale to the viewport zoom level
        // and translate to top left of the the cache rectangle of the note VS
        // in real coordinates
        let cacheRectReal = this.cacheRectRealSpace(noteVS, viewport)
        let cacheRectAfterDPR = this.cacheRectAfterDPR(noteVS, viewport)

        let [w, h] = cacheRectAfterDPR.size().data();
        if (w > MAX_CACHE_IMAGE_DIM || h > MAX_CACHE_IMAGE_DIM) {
            return false;
        }
        let offscreenCanvas = new OffscreenCanvas(
            cacheRectAfterDPR.width(), cacheRectAfterDPR.height());

        let ctx = offscreenCanvas.getContext('2d') as CanvasRenderingContext2D | null;
        if (!ctx) {
            log.error('Could not create offscreen canvas context');
            return false;
        }

        // Prep the projection matrix. We're drawing on a canvas with the same
        // size as the cache rect, and the drawing operations are in real space
        // The note canvasDraw expects a canvas configured with a projection matrix
        // for real space (i.e. the note will be drawn on its coordinates in real
        // space). But we want the viewport to encompass the cache rect.
        // So we'll apply the dpr correction and the viewport scaling,
        // and
        ctx.save()
        ctx.scale(dpr, dpr) // compensate for dpr adjustment in the canvas size

        ctx.scale(viewport.heightScaleFactor(), viewport.heightScaleFactor())
        ctx.translate(-cacheRectReal.x, -cacheRectReal.y)

        // Draw the note
        this.drawElement(ctx, noteVS)

        // Clear projection matrix
        ctx.restore()

        let imageBitmap = offscreenCanvas.transferToImageBitmap();
        if (imageBitmap.width !== cacheRectAfterDPR.width() || imageBitmap.height !== cacheRectAfterDPR.height()) {
            log.error('Image bitmap size does not match cache rect size', imageBitmap, cacheRectAfterDPR);
        } else {
        }
        this.setNvsCache(noteVS, imageBitmap);
        return true;
    }
    canvasDrawNVS_fromCache(mainCtx: CanvasRenderingContext2D, noteVS: NoteViewState, viewport: Viewport) {
        // Draw the cached image - since the case is pretty specific, and
        // we'll avoid implelmenting a web worker for now - we'll use another
        // canvas element to scale the image data and draw it on the main canvas
        // The rendering canvas will match the viewport size and projection matrix
        // We'll draw the cached image on it and then draw the source region
        // where the imageData was scaled to the main context

        // I shoud try to do it with a changing offscreen canvas size
        // For every render - set the size to the scaled cache rect size
        // (i.e. the projected size for the new viewport) and use the offscr. canvas
        // to scale the cached image data. Then draw the whole offscreen canvas
        // to the main canvas

        const imageBitmap = this.nvsCache(noteVS);
        if (imageBitmap === undefined) {
            log.error('No image bitmap for noteVS', noteVS);
            return;
        }

        // // If size matches - draw directly to save time on scaling
        // const cacheRect = this.cacheRectProjected(noteVS, viewport);
        // if (imageBitmap.width === cacheRect.width() && imageBitmap.height === cacheRect.height()) {
        //     mainCtx.save()
        //     mainCtx.resetTransform()
        //     mainCtx.drawImage(imageBitmap, cacheRect.x, cacheRect.y)
        //     mainCtx.restore()
        //     return;
        // }

        // Draw on the mainCtx
        let cacheRectReal = this.cacheRectRealSpace(noteVS, viewport)
        mainCtx.save()
        // mainCtx.imageSmoothingEnabled = false
        // mainCtx.imageSmoothingQuality = 'low'
        mainCtx.drawImage(
            imageBitmap,
            cacheRectReal.x, cacheRectReal.y, cacheRectReal.width(), cacheRectReal.height()
        )

        mainCtx.restore()

        // //draw a rectangle outline for debugging
        // mainCtx.save()
        // mainCtx.strokeStyle = 'green'
        // mainCtx.strokeRect(...cacheRectReal.data())
        // mainCtx.restore()
    }



    renderPage(state: PageViewState, context: CanvasRenderingContext2D) {

        // Debounce redundant rendering
        if (this.renderTimeout !== null) {
            return;
        }
        this.renderTimeout = setTimeout(() => {
            // let context = this.context;
            // if (context === null) {
            //     log.error('Canvas context is null');
            //     return;
            // }
            this.renderTimeout = null;
            this._render(state, context);
        }, MIN_RERENDER_TIME);
    }

    _render(state: PageViewState, ctx: CanvasRenderingContext2D) {
        // console.log('Rendering at', state.viewport, 'last render time', this.lastRenderStart);

        let dpr = state.viewport.devicePixelRatio;
        //Debug: time the rendering
        let paintStartT = performance.now();

        const noTimeLeft = () => {
            let currentT = performance.now();
            let elapsedT = currentT - paintStartT;
            return elapsedT > MAX_RENDER_TIME * 1000;
        }

        // Clear the canvas
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.resetTransform(); // may be redundant, but why not

        // Draw elemnts in pixel space
        // Draw drag selection rectangle
        if (state.mode === PageMode.DragSelection && state.dragSelectionRectData !== null) {
            ctx.fillStyle = dragSelectRectColor;
            ctx.fillRect(...state.dragSelectionRectData);
        }

        // Draw elemnts in real space

        // Setup the projection matrix
        ctx.save()
        ctx.scale(dpr, dpr);
        // // Translate to the center of the screen in pixel space
        // ctx.translate(pixelSpaceRect.width() / 2, pixelSpaceRect.height() / 2);
        // Scale to the zoom level
        let heightScaleFactor = state.viewport.heightScaleFactor();
        ctx.scale(heightScaleFactor, heightScaleFactor);
        // Translate to the center of the viewport
        // let viewportTopLeft = state.viewport.top
        ctx.translate(-state.viewport.xReal, -state.viewport.yReal);

        // Draw test rect
        ctx.fillStyle = 'red';
        ctx.fillRect(0, 0, 100, 100);

        // Draw viewport boundaries
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1;
        ctx.strokeRect(...state.viewport.realBounds().data());


        // Draw notes
        let viewportRect = state.viewport.realBounds()

        interface DrawStats {
            total: number,
            reused: number,
            reusedDirty: number,
            deNovoRedraw: number,
            deNovoClean: number,
            direct: number,
            pattern: number,
            render_time: number
        }
        let drawStats: DrawStats = {
            total: 0,
            reused: 0,
            reusedDirty: 0,
            deNovoRedraw: 0,
            deNovoClean: 0,
            direct: 0,
            pattern: 0,
            render_time: 0
        }

        // Plan the drawing
        let withCorrectCache = new Set<NoteViewState>(); // Render all with correct cache
        let withExpiredCache = new Set<NoteViewState>(); // Render all with correct cache
        let withNoCache = new Set<NoteViewState>(); // nvs in the viewport without cache
        for (const noteVS of state.noteViewStatesByOwnId.values()) {
            // Skip if the note is outside the viewport
            if (!viewportRect.intersects(noteVS.note.rect())) {
                continue;
            }

            drawStats.total++;

            // Get cache
            let imageBitmap = this.nvsCache(noteVS);
            let cachePresent: boolean;
            let sizeMatches: boolean;

            // Prep flags
            const cacheRectAfterDPR = this.cacheRectAfterDPR(noteVS, state.viewport);
            if (imageBitmap !== undefined) {
                cachePresent = true;
                sizeMatches = imageBitmap.width === cacheRectAfterDPR.width() && imageBitmap.height === cacheRectAfterDPR.height();
            } else {
                cachePresent = false;
                sizeMatches = false;
            }

            // Plan painting
            if (cachePresent) {
                if (sizeMatches) {
                    withCorrectCache.add(noteVS);
                } else {
                    withExpiredCache.add(noteVS);
                }
            } else { // (no cache)
                withNoCache.add(noteVS);
            }
        }

        // Draw notes with correct cache
        for (const noteVS of withCorrectCache) {
            this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
            drawStats.reused++;
        }

        // Update the cache while there is time left or for minimum 2 notes
        let denovoRendered = 0;
        // Start with notes with no cache with priority
        for (const noteVS of withNoCache) {
            if (noTimeLeft() && denovoRendered >= 2) {
                renderPattern(ctx, noteVS);
                drawStats.pattern++;
                continue;
            }
            let successful = this.renderNoteView_toCache(ctx, noteVS, state.viewport, dpr);
            if (successful) {
                this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
                denovoRendered++;
                drawStats.deNovoClean++;
            } else {
                this.drawElement(ctx, noteVS)
                drawStats.direct++;
            }
        }
        // Update those with expired cache or draw them if no time is left
        for (const noteVS of withExpiredCache) {
            if (noTimeLeft() && denovoRendered >= 2) {
                this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
                drawStats.reusedDirty++;
                continue;
            }
            let successful = this.renderNoteView_toCache(ctx, noteVS, state.viewport, dpr);
            if (successful) {
                this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
                denovoRendered++;
                drawStats.deNovoRedraw++;
            } else {
                this.drawElement(ctx, noteVS)
                drawStats.direct++;
            }
        }


        // Draw arrows
        for (const arrowVS of state.arrowViewStatesByOwnId.values()) {
            // Skip if the arrow is outside the viewport
            // if (!arrowVS.intersectsRect(viewportRect)) {
            //     continue;
            // }
            // arrowVS.canvasDraw(ctx);
            try {
                let view = new ArrowCanvasView(this, arrowVS);
                view.render(ctx);
            } catch (e) {
                log.error('Error rendering arrow', arrowVS, e);
            }
        }

        const drawSelectionOverlay = (childVS: ElementViewState) => {
            if (childVS instanceof NoteViewState) {
                ctx.fillStyle = selectionColor;
                ctx.fillRect(...childVS.note.rect().data());

            } else if (childVS instanceof ArrowViewState) {
                ctx.strokeStyle = selectionColor;
                ctx.lineWidth = childVS.arrow.line_thickness + ARROW_SELECTION_THICKNESS_DELTA;
                for (let curve of childVS.bezierCurveParams) {
                    ctx.beginPath();
                    ctx.moveTo(curve[0].x, curve[0].y);
                    ctx.bezierCurveTo(curve[1].x, curve[1].y, curve[2].x, curve[2].y, curve[3].x, curve[3].y);
                    ctx.stroke();
                    ctx.closePath();
                }
            }
        }

        // If drag selection is active - add drag selected children to the selection
        if (state.mode === PageMode.DragSelection) {
            for (const childVS of state.dragSelectedElements) {
                drawSelectionOverlay(childVS);
            }
        }

        for (const childVS of state.selectedElements) {
            drawSelectionOverlay(childVS);
        }

        ctx.restore()

        // Debug: time the rendering
        let end = performance.now();
        let duration = end - paintStartT;
        drawStats.render_time = duration;
        // console.log(`Rendering took ${duration} ms`)

        // Overview

        // Draw stats
        ctx.save()
        ctx.resetTransform()
        ctx.fillStyle = 'black';
        ctx.font = '15px sans-serif';
        ctx.fillText(`Render stats | total: ${drawStats.total} | reused: ${drawStats.reused} | reusedDirty: ${drawStats.reusedDirty} | deNovoRedraw: ${drawStats.deNovoRedraw} | deNovoClean: ${drawStats.deNovoClean} | pattern: ${drawStats.pattern} | direct: ${drawStats.direct} | render_time: ${drawStats.render_time.toFixed(2)} ms`, 10, 20);
        ctx.restore()

        // Call the next render if some notes have not been fully rendered
        if (denovoRendered > 0 || drawStats.pattern > 0) {
            this.requestFollowupRender(state, ctx, dpr);
        } else {
            this._followupRenderSteps = 0;
        }

        return drawStats;
    }

    requestFollowupRender(state: PageViewState, context: CanvasRenderingContext2D, dpr: number) {
        this._followupRenderSteps++;

        // Prevent infinite loop
        if (this._followupRenderSteps > 10000) {
            log.error('Followup render steps exceeded 10000. Interrupting');
            this._followupRenderSteps = 0;
            return;
        }
        this.renderPage(state, context);
    }
}
