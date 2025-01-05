import { ArrowViewState } from "../arrow/ArrowViewState";
import { Viewport } from "./Viewport";
import { ElementViewState } from "./ElementViewState";
import { PageMode, PageViewState } from "./PageViewState";
import { NoteViewState } from "../note/NoteViewState";
import { ALIGNMENT_LINE_LENGTH, ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS, ARROW_CONTROL_POINT_RADIUS, ARROW_POTENTIAL_CONTROL_POINT_RADIUS, ARROW_SELECTION_THICKNESS_DELTA, DRAG_SELECT_COLOR_ROLE, IMAGE_CACHE_PADDING, MAX_RENDER_TIME, RESIZE_CIRCLE_RADIUS, SELECTED_ITEM_OVERLAY_COLOR_ROLE } from "../../core/constants";
import { getLogger } from "fusion/logging";
import { drawCrossingDiagonals } from "../../util";
import { color_role_to_hex_color } from "../../util/Color";
import { Rectangle } from "../../util/Rectangle";
import { ElementView, getElementView } from "../elementViewLibrary";
import { ArrowCanvasView } from "../arrow/ArrowCanvasView";
import { arrowAnchorPosition, ArrowAnchorOnNoteType } from "../../model/Arrow";

let log = getLogger('DirectRenderer');

const MAX_CACHE_IMAGE_DIM = 1024;

export enum DrawMode {
    NONE,
    DENOVO,
    CACHE,
    PATTERN
}


export interface ElementDrawStats {
    total: number,
    reused: number,
    reusedDirty: number,
    deNovoRedraw: number,
    deNovoClean: number,
    deNovoAll: number,
    direct: number,
    pattern: number,
    render_time: number
}

const MIN_RERENDER_TIME = 5; // ms

const selectionColor = color_role_to_hex_color(SELECTED_ITEM_OVERLAY_COLOR_ROLE);
const dragSelectRectColor = color_role_to_hex_color(DRAG_SELECT_COLOR_ROLE);

function renderPattern(ctx: CanvasRenderingContext2D, noteVS: NoteViewState) {
    let note = noteVS.note();
    ctx.strokeStyle = color_role_to_hex_color(note.style.color_role);
    let rect = note.rect();
    drawCrossingDiagonals(ctx, rect.x, rect.y, rect.width, rect.height, 20);
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
        // console.log('-----------------getImage', src)
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
        let rect = viewport.projectRect(noteVS.note().rect());
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
            context.save();
            view.render(context);
        } catch (e) {
            log.error('Error rendering element', element, e);
        } finally {
            context.restore();
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
            cacheRectAfterDPR.width, cacheRectAfterDPR.height);

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
        if (imageBitmap.width !== cacheRectAfterDPR.width || imageBitmap.height !== cacheRectAfterDPR.height) {
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
            cacheRectReal.x, cacheRectReal.y, cacheRectReal.width, cacheRectReal.height
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
            this.renderTimeout = null;
            this._render(state, context);
        }, MIN_RERENDER_TIME);
    }

    _applyProjectionMatrix(state: PageViewState, ctx: CanvasRenderingContext2D) {
        // Apply DPR correction
        let dpr = state.viewport.devicePixelRatio;
        ctx.scale(dpr, dpr);
        // Scale to the zoom level
        let heightScaleFactor = state.viewport.heightScaleFactor();
        ctx.scale(heightScaleFactor, heightScaleFactor);
        // Translate
        ctx.translate(-state.viewport.xReal, -state.viewport.yReal);
    }

    _render(state: PageViewState, ctx: CanvasRenderingContext2D) {
        // console.log('Rendering at', state.viewport);

        // Clear the canvas
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.resetTransform(); // may be redundant, but why not

        // Drawing without transformation
        // Draw drag selection rectangle
        if (state.mode === PageMode.DragSelection && state.dragSelectionRectData !== null) {
            ctx.fillStyle = dragSelectRectColor;
            ctx.fillRect(...state.dragSelectionRectData);
        }

        // Draw elements
        this._drawElements(state, ctx);

        // Draw stuff in real space
        // Setup the projection matrix
        ctx.save()
        this._applyProjectionMatrix(state, ctx);

        // // Draw test rect
        // ctx.fillStyle = 'red';
        // ctx.fillRect(0, 0, 100, 100);

        // // Draw viewport boundaries (for debugging)
        // ctx.strokeStyle = 'black';
        // ctx.lineWidth = 1;
        // ctx.strokeRect(...state.viewport.realBounds().data());

        // Draw selection overlays
        // If drag selection is active - add drag selected children to the selection
        if (state.mode === PageMode.DragSelection) {
            for (const childVS of state.dragSelectedElementsVS) {
                this._drawSelectionOverlay(ctx, childVS);
            }
        }

        // Draw regular selection overlays
        for (const childVS of state.selectedElementsVS) {
            this._drawSelectionOverlay(ctx, childVS);
        }

        // Draw anchor suggestions (when creating an arrow) and new arrow
        if (state.mode === PageMode.CreateArrow && state.projectedMousePosition) {
            // Draw anchor suggestions
            let realMousePos = state.viewport.unprojectPoint(state.projectedMousePosition);
            let anchorSuggestion = state.noteAnchorSuggestionAt(realMousePos);
            if (anchorSuggestion.onAnchor || anchorSuggestion.onNote) {
                let note = anchorSuggestion.noteViewState.note();

                for (let anchorType of
                    [ArrowAnchorOnNoteType.mid_left, ArrowAnchorOnNoteType.top_mid,
                    ArrowAnchorOnNoteType.mid_right, ArrowAnchorOnNoteType.bottom_mid]) {
                    let anchorPosition = arrowAnchorPosition(note, anchorType as ArrowAnchorOnNoteType);

                    // Draw the circle
                    ctx.strokeStyle = color_role_to_hex_color(note.style.color_role);
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.arc(anchorPosition.x, anchorPosition.y, ARROW_ANCHOR_ON_NOTE_SUGGEST_RADIUS, 0, 2 * Math.PI);
                    ctx.stroke();
                    ctx.closePath();
                }
            }

            // Draw the currently created arrow
            if (state.newArrowViewState !== null) {
                console.log('Drawing new arrow', state.newArrowViewState);
                // Head should be null, and we want to set it to the mouse pos
                let arrow = state.newArrowViewState.arrow()
                arrow.setHead(realMousePos, null, ArrowAnchorOnNoteType.none);
                let newArrowVS = new ArrowViewState(
                    arrow)
                let view = new ArrowCanvasView(this, newArrowVS);
                try{
                    ctx.save();
                    view.render(ctx);
                } catch (e) {
                    log.error('Error rendering new arrow', e);
                } finally {
                    ctx.restore();
                }
            }
        } else if (state.mode === PageMode.NoteResize || state.mode === PageMode.MoveElements) {
            // Draw note alignment lines
            for (let elementVS of state.selectedElementsVS) {
                if (elementVS instanceof NoteViewState) {
                    // Draw four lines that extend all rect sides with ALIGNM
                    let note = elementVS.note();
                    let rect = note.rect();
                    let leftLine = [
                        rect.x, rect.y - ALIGNMENT_LINE_LENGTH,
                        rect.x, rect.bottom() + ALIGNMENT_LINE_LENGTH,
                    ];
                    let rightLine = [
                        rect.right(), rect.y - ALIGNMENT_LINE_LENGTH,
                        rect.right(), rect.bottom() + ALIGNMENT_LINE_LENGTH,
                    ];
                    let topLine = [
                        rect.x - ALIGNMENT_LINE_LENGTH, rect.y,
                        rect.right() + ALIGNMENT_LINE_LENGTH, rect.y,
                    ];
                    let bottomLine = [
                        rect.x - ALIGNMENT_LINE_LENGTH, rect.bottom(),
                        rect.right() + ALIGNMENT_LINE_LENGTH, rect.bottom(),
                    ];
                    ctx.strokeStyle = color_role_to_hex_color(note.style.color_role);
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(leftLine[0], leftLine[1]);
                    ctx.lineTo(leftLine[2], leftLine[3]);
                    ctx.moveTo(rightLine[0], rightLine[1]);
                    ctx.lineTo(rightLine[2], rightLine[3]);
                    ctx.moveTo(topLine[0], topLine[1]);
                    ctx.lineTo(topLine[2], topLine[3]);
                    ctx.moveTo(bottomLine[0], bottomLine[1]);
                    ctx.lineTo(bottomLine[2], bottomLine[3]);
                    ctx.stroke();
                    ctx.closePath();
                }
            }
        }

        // When a single arrow is selected - draw the control points for editing it
        let editableArrowVS = state.arrowVS_withVisibleControlPoints();
        if (editableArrowVS !== null) {
            // Display control points and suggested control points
            let arrow = editableArrowVS.arrow();

            ctx.strokeStyle = color_role_to_hex_color(arrow.colorRole);
            ctx.lineWidth = 1;

            // Display control points
            for (let cpIndex of arrow.controlPointIndices()) {
                let cp = editableArrowVS.controlPointPosition(cpIndex);
                ctx.beginPath();
                ctx.arc(cp.x, cp.y, ARROW_CONTROL_POINT_RADIUS, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.closePath();
            }
            // Display potential control points
            for (let cpIndex of arrow.potentialControlPointIndices()) {
                let cp = editableArrowVS.controlPointPosition(cpIndex);
                ctx.beginPath();
                ctx.arc(cp.x, cp.y, ARROW_POTENTIAL_CONTROL_POINT_RADIUS, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.closePath();
            }
        }

        ctx.restore()
    }

    _drawElements(state: PageViewState, ctx: CanvasRenderingContext2D) {
        ctx.save()
        this._applyProjectionMatrix(state, ctx);

        //Debug: time the rendering
        let paintStartT = performance.now();

        const noTimeLeft = () => {
            let currentT = performance.now();
            let elapsedT = currentT - paintStartT;
            return elapsedT > MAX_RENDER_TIME * 1000;
        }

        // Draw notes
        let viewportRect = state.viewport.realBounds()

        let drawStats: ElementDrawStats = {
            total: 0,
            reused: 0,
            reusedDirty: 0,
            deNovoRedraw: 0,
            deNovoClean: 0,
            deNovoAll: 0,
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
            if (!viewportRect.intersects(noteVS.note().rect())) {
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
                sizeMatches = imageBitmap.width === cacheRectAfterDPR.width && imageBitmap.height === cacheRectAfterDPR.height;
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
        // Render notes with no cache (with priority)
        let dpr = state.viewport.devicePixelRatio;
        for (const noteVS of withNoCache) {
            if (noTimeLeft() && drawStats.deNovoAll >= 2) {
                renderPattern(ctx, noteVS);
                drawStats.pattern++;
                continue;
            }
            let successful = this.renderNoteView_toCache(ctx, noteVS, state.viewport, dpr);
            if (successful) {
                this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
                drawStats.deNovoAll++;
                drawStats.deNovoClean++;
            } else {
                this.drawElement(ctx, noteVS)
                drawStats.direct++;
            }
        }
        // Update those with expired cache or draw them if no time is left
        for (const noteVS of withExpiredCache) {
            if (noTimeLeft() && drawStats.deNovoAll >= 2) {
                this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
                drawStats.reusedDirty++;
                continue;
            }
            let successful = this.renderNoteView_toCache(ctx, noteVS, state.viewport, dpr);
            if (successful) {
                this.canvasDrawNVS_fromCache(ctx, noteVS, state.viewport);
                drawStats.deNovoAll++;
                drawStats.deNovoRedraw++;
            } else {
                this.drawElement(ctx, noteVS)
                drawStats.direct++;
            }
        }


        // Draw arrows
        for (const arrowVS of state.arrowViewStatesByOwnId.values()) {
            // Skip if the arrow is outside the viewport | does not really speed up anything
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

        // Restore the projection matrix
        ctx.restore()

        // Debug: time the rendering
        let end = performance.now();
        let duration = end - paintStartT;
        drawStats.render_time = duration;
        // console.log(`Rendering took ${duration} ms`)

        // Overview

        // Draw stats
        let pixelSpaceRect = state.viewport.projectedBounds();
        ctx.save()
        ctx.resetTransform()
        ctx.fillStyle = 'black';
        ctx.font = '15px sans-serif';
        let xStats = 10;
        let yStats = pixelSpaceRect.height - 10;
        ctx.fillText(`Render stats | total: ${drawStats.total} | reused: ${drawStats.reused} | reusedDirty: ${drawStats.reusedDirty} | deNovoRedraw: ${drawStats.deNovoRedraw} | deNovoClean: ${drawStats.deNovoClean} | pattern: ${drawStats.pattern} | direct: ${drawStats.direct} | render_time: ${drawStats.render_time.toFixed(2)} ms`, xStats, yStats);
        ctx.restore()

        // Call the next render if some notes have not been fully rendered
        if (drawStats.deNovoAll > 0 || drawStats.pattern > 0) {
            this.requestFollowupRender(state, ctx, dpr);
        } else {
            this._followupRenderSteps = 0;
        }
    }

    _drawSelectionOverlay(ctx: CanvasRenderingContext2D, childVS: ElementViewState) {
        // Expects the ctx to be in the real space
        if (childVS instanceof NoteViewState) {
            let note = childVS.note();
            let rect = note.rect();
            // Render the note selection overlay
            ctx.fillStyle = selectionColor;
            ctx.fillRect(...rect.data());
            // Draw the resize circles
            ctx.fillStyle = color_role_to_hex_color(note.style.background_color_role);
            let bottomRight = rect.bottomRight();
            ctx.beginPath();
            ctx.arc(bottomRight.x, bottomRight.y, RESIZE_CIRCLE_RADIUS, 0, 2 * Math.PI);
            ctx.fill();
            ctx.closePath();

        } else if (childVS instanceof ArrowViewState) {
            // Render the arrow selection overlay
            let arrowView = new ArrowCanvasView(this, childVS);
            try {
                ctx.save();
                arrowView.renderSelectionOverlay(ctx);
            } catch (e) {
                log.error('Error rendering arrow selection overlay', e);
            } finally {
                ctx.restore();
            }
        }
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


// a decorator for
