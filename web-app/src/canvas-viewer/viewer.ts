// Pamet canvas viewer — self-contained script for .canvas HTML files.
// Reads the embedded JSON, creates DOM notes + SVG arrows, sets scroll.

import './viewer.css';

// ── Constants ──────────────────────────────────────────────────────
const ARROW_HAND_LENGTH = 20;
const CP_BASE_DISTANCE = 80;
const CP_DIST_SEGMENT_ADJUST_K = 0.1;
const DEFAULT_ARROW_THICKNESS = 1.5;
const BBOX_PADDING_FACTOR = 0.10; // 10% padding around notes

// ── Color roles ───────────────────────────────────────────────────
const COLOR_ROLE_MAP: Record<string, string> = {
    'primary': '#0000ff1a',
    'onPrimary': '#0000ff',
    'error': '#ff00001a',
    'onError': '#ff0000',
    'success': '#00ff001a',
    'onSuccess': '#00a33c',
    'surface': '#ffffff',
    'onSurface': '#000000',
    'surfaceDim': '#0000001a',
    'transparent': '#00000000',
};

// ── Types ─────────────────────────────────────────────────────────
interface NoteData {
    id: string;
    geometry: [number, number, number, number];
    content: {
        text?: string;
        url?: string;
        page_ref?: { id: string; path: string };
        image?: { id: string; path: string; width: number; height: number };
    };
    style: {
        color_role?: string;
        background_color_role: string;
    };
}

interface EndPoint {
    position: [number, number] | null;
    note_anchor_id: string | null;
    note_anchor_type: string;
}

interface ArrowData {
    id: string;
    tail: EndPoint;
    head: EndPoint;
    mid_points: [number, number][];
    style: {
        color_role: string;
        thickness: number;
    };
}

interface PageData {
    notes?: NoteData[];
    arrows?: ArrowData[];
}

type Vec2 = [number, number];

// ── Vector math ───────────────────────────────────────────────────
function vadd(a: Vec2, b: Vec2): Vec2 { return [a[0] + b[0], a[1] + b[1]]; }
function vsub(a: Vec2, b: Vec2): Vec2 { return [a[0] - b[0], a[1] - b[1]]; }
function vmul(a: Vec2, k: number): Vec2 { return [a[0] * k, a[1] * k]; }
function vdist(a: Vec2, b: Vec2): number {
    const dx = a[0] - b[0], dy = a[1] - b[1];
    return Math.sqrt(dx * dx + dy * dy);
}
function vrot(p: Vec2, angle: number, center: Vec2): Vec2 {
    const cos = Math.cos(angle), sin = Math.sin(angle);
    const dx = p[0] - center[0], dy = p[1] - center[1];
    return [center[0] + dx * cos - dy * sin, center[1] + dx * sin + dy * cos];
}

// ── Color helpers ─────────────────────────────────────────────────
function resolveColor(role: string | undefined): string {
    if (!role) return '#000000';
    return COLOR_ROLE_MAP[role] || '#000000';
}

// ── Main ──────────────────────────────────────────────────────────
function init(): void {

    const dataTag = document.getElementById("pamet-data");
    if (!dataTag) return;

    let pageData: PageData;
    try {
        pageData = JSON.parse(dataTag.textContent || "{}");
    } catch {
        console.error("Failed to parse pamet-data JSON");
        return;
    }

    const notes = pageData.notes || [];
    const arrows = pageData.arrows || [];
    if (notes.length === 0 && arrows.length === 0) return;

    // ── Compute bounding box ──────────────────────────────────────────
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of notes) {
        const [x, y, w, h] = n.geometry;
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x + w > maxX) maxX = x + w;
        if (y + h > maxY) maxY = y + h;
    }
    // Include arrow free-floating endpoints in bbox
    for (const a of arrows) {
        for (const ep of [a.tail, a.head]) {
            if (ep.position) {
                const [x, y] = ep.position;
                if (x < minX) minX = x;
                if (y < minY) minY = y;
                if (x > maxX) maxX = x;
                if (y > maxY) maxY = y;
            }
        }
    }

    const bboxW = maxX - minX;
    const bboxH = maxY - minY;
    const padX = bboxW * BBOX_PADDING_FACTOR;
    const padY = bboxH * BBOX_PADDING_FACTOR;
    // Origin offset: shift all coords so bbox.topLeft → (padX, padY)
    const ox = -minX + padX;
    const oy = -minY + padY;
    const canvasW = bboxW + 2 * padX;
    const canvasH = bboxH + 2 * padY;

    // ── Create canvas container ───────────────────────────────────────
    const canvas = document.createElement('div');
    canvas.id = 'pamet-canvas';
    canvas.style.width = canvasW + 'px';
    canvas.style.height = canvasH + 'px';
    document.body.appendChild(canvas);

    // Build a lookup of notes by ID for arrow anchor resolution
    const noteById = new Map<string, NoteData>();
    for (const n of notes) noteById.set(n.id, n);

    // ── Render notes ──────────────────────────────────────────────────
    for (const note of notes) {
        renderNote(note, canvas);
    }

    // ── Render arrows ─────────────────────────────────────────────────
    if (arrows.length > 0) {
        const hl = ARROW_HAND_LENGTH;
        const paths = arrows.map(a => renderArrowPath(a)).filter(Boolean).join('\n');
        const wrapper = document.createElement('div');
        wrapper.innerHTML =
            `<svg id="arrows-layer" xmlns="http://www.w3.org/2000/svg" width="${canvasW}" height="${canvasH}">` +
            `<defs><marker id="ah" markerWidth="${hl}" markerHeight="${hl}" ` +
            `refX="${hl}" refY="${hl / 2}" orient="auto" markerUnits="userSpaceOnUse">` +
            `<polyline points="0 0,${hl} ${hl / 2},0 ${hl}" fill="none" ` +
            `stroke="context-stroke" stroke-width="context-stroke-width" ` +
            `stroke-linecap="round" stroke-linejoin="round"/></marker></defs>` +
            paths + `</svg>`;
        canvas.appendChild(wrapper.firstElementChild!);
    }

    // ── Set initial scroll to center ──────────────────────────────────
    requestAnimationFrame(() => {
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        // Center of canvas content
        const cx = ox + bboxW / 2;
        const cy = oy + bboxH / 2;
        window.scrollTo(cx - vw / 2, cy - vh / 2);
    });

    // ── Note rendering ────────────────────────────────────────────────
    function renderNote(note: NoteData, container: HTMLElement): void {
        const [nx, ny, nw, nh] = note.geometry;
        const x = nx + ox, y = ny + oy;
        const textColor = resolveColor(note.style.color_role);
        const bgColor = resolveColor(note.style.background_color_role);
        const img = note.content.image;
        const hasText = !!note.content.text;
        const hasImage = !!img;

        // Layout: how to arrange text + image
        let layout: 'text-only' | 'image-only' | 'horizontal' | 'vertical' = 'text-only';
        if (hasText && hasImage) {
            const imageAR = (img!.width > 0 && img!.height > 0) ? img!.width / img!.height : 1;
            layout = (nw / nh - imageAR > 0.5) ? 'horizontal' : 'vertical';
        } else if (!hasText && hasImage) {
            layout = 'image-only';
        }

        const noteEl = document.createElement('div');
        noteEl.className = 'note';
        noteEl.style.cssText = `left:${x}px;top:${y}px;width:${nw}px;height:${nh}px;background-color:${bgColor};color:${textColor}`;

        if (note.content.page_ref) noteEl.classList.add('has-border');
        else if (note.content.url) noteEl.classList.add('has-border', 'external-link');

        const body = document.createElement('div');
        body.className = 'note-body' +
            (layout === 'horizontal' ? ' layout-horizontal' : '') +
            (layout === 'vertical' ? ' layout-vertical' : '');

        if (hasImage && layout !== 'text-only') {
            const imgArea = document.createElement('div');
            imgArea.className = 'note-image-area';
            const imageAR = (img!.width > 0 && img!.height > 0) ? img!.width / img!.height : 1;
            if (layout === 'horizontal') imgArea.style.width = (nh * imageAR) + 'px';
            else if (layout === 'vertical') imgArea.style.height = (nh * 0.8) + 'px';
            const imgEl = document.createElement('img');
            imgEl.src = img!.path;
            imgEl.alt = '';
            imgEl.loading = 'lazy';
            imgArea.appendChild(imgEl);
            body.appendChild(imgArea);
        }

        if (hasText && layout !== 'image-only') {
            const textArea = document.createElement('div');
            textArea.className = 'note-text';
            textArea.textContent = note.content.text!;
            body.appendChild(textArea);
        }

        noteEl.appendChild(body);

        const href = note.content.page_ref?.path || note.content.url;
        if (href) {
            const a = document.createElement('a');
            a.className = 'note-link';
            a.href = href;
            if (note.content.url && !note.content.page_ref) {
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
            }
            a.style.cssText = `position:absolute;left:${x}px;top:${y}px;width:${nw}px;height:${nh}px`;
            noteEl.style.cssText = `position:relative;width:100%;height:100%;background-color:${bgColor};color:${textColor}`;
            a.appendChild(noteEl);
            container.appendChild(a);
        } else {
            container.appendChild(noteEl);
        }
    }

    // ── Arrow rendering ───────────────────────────────────────────────

    // Anchor position on a note rect
    function anchorPos(noteGeo: [number, number, number, number], anchorType: string): Vec2 {
        const [x, y, w, h] = noteGeo;
        switch (anchorType) {
            case 'mid_left': return [x + ox, y + h / 2 + oy];
            case 'top_mid': return [x + w / 2 + ox, y + oy];
            case 'mid_right': return [x + w + ox, y + h / 2 + oy];
            case 'bottom_mid': return [x + w / 2 + ox, y + h + oy];
            default: return [x + w / 2 + ox, y + h / 2 + oy];
        }
    }

    function inferAnchorType(adjPoint: Vec2, noteGeo: [number, number, number, number]): string {
        const [nx, ny, nw, nh] = noteGeo;
        const left = nx + ox, top = ny + oy, right = left + nw, bottom = top + nh;
        const cy = top + nh / 2;

        if (adjPoint[0] < left) return 'mid_left';
        if (adjPoint[0] > right) return 'mid_right';
        if (adjPoint[1] < top) return 'top_mid';
        if (adjPoint[1] > bottom) return 'bottom_mid';
        return adjPoint[1] < cy ? 'top_mid' : 'bottom_mid';
    }

    function specialSigmoid(x: number): number {
        return 1 / (1 + Math.exp(-x / (CP_BASE_DISTANCE / 2) + 5));
    }

    function cpDist(p1: Vec2, p2: Vec2): number {
        const d = vdist(p1, p2);
        return specialSigmoid(d) * CP_BASE_DISTANCE + CP_DIST_SEGMENT_ADJUST_K * d;
    }

    function headOrTailCP(point: Vec2, adjPoint: Vec2, dist: number, anchorType: string): Vec2 {
        if (anchorType === 'none' || anchorType === 'auto') {
            const d = vdist(point, adjPoint);
            if (d < 0.001) return point;
            const k = dist / d;
            return vadd(point, vmul(vsub(adjPoint, point), k));
        }
        switch (anchorType) {
            case 'mid_left': return vadd(point, [-dist, 0]);
            case 'top_mid': return vadd(point, [0, -dist]);
            case 'mid_right': return vadd(point, [dist, 0]);
            case 'bottom_mid': return vadd(point, [0, dist]);
            default: return point;
        }
    }

    type BezierCurve = [Vec2, Vec2, Vec2, Vec2];

    // Resolve endpoint position and anchor type
    function resolveEndpoint(ep: EndPoint, epNote: NoteData | undefined, adjPoint: Vec2): [Vec2, string] {
        if (!epNote) {
            return [ep.position ? vadd(ep.position as Vec2, [ox, oy]) : [0, 0], 'none'];
        }
        let aType = ep.note_anchor_type || 'auto';
        if (aType === 'auto') aType = inferAnchorType(adjPoint, epNote.geometry as [number, number, number, number]);
        return [anchorPos(epNote.geometry, aType), aType];
    }

    function computeBezierCurves(arrow: ArrowData): BezierCurve[] {
        const midPoints = (arrow.mid_points || []).map(p => vadd(p as Vec2, [ox, oy]) as Vec2);
        const curves: BezierCurve[] = [];

        const tailNote = arrow.tail.note_anchor_id ? noteById.get(arrow.tail.note_anchor_id) : undefined;
        const headNote = arrow.head.note_anchor_id ? noteById.get(arrow.head.note_anchor_id) : undefined;

        // Resolve tail
        const tailAdj0: Vec2 = midPoints.length > 0 ? midPoints[0]
            : (headNote ? anchorPos(headNote.geometry, arrow.head.note_anchor_type || 'top_mid')
                : (arrow.head.position ? vadd(arrow.head.position as Vec2, [ox, oy]) : [0, 0]));
        const [tailPoint, tailAnchorType] = resolveEndpoint(arrow.tail, tailNote, tailAdj0);

        // Resolve head
        const headAdj0: Vec2 = midPoints.length > 0 ? midPoints[midPoints.length - 1] : tailPoint;
        const [headPoint, headAnchorType] = resolveEndpoint(arrow.head, headNote, headAdj0);

        // Loop arrow special case
        if (midPoints.length === 0 && vdist(tailPoint, headPoint) < 0.1) {
            const d = CP_BASE_DISTANCE;
            curves.push([tailPoint, vadd(tailPoint, [d, 0]), vadd(tailPoint, [0, d]), headPoint]);
            return curves;
        }

        // Build curves
        const tailAdj = midPoints.length > 0 ? midPoints[0] : headPoint;
        const headAdj = midPoints.length > 0 ? midPoints[midPoints.length - 1] : tailPoint;

        let controlPointDistance = cpDist(tailPoint, tailAdj);
        let firstCP = headOrTailCP(tailPoint, tailAdj, controlPointDistance, tailAnchorType);

        let prevPoint = tailPoint;
        for (let idx = 0; idx < midPoints.length; idx++) {
            const curPoint = midPoints[idx];
            const nextPoint = idx + 1 < midPoints.length ? midPoints[idx + 1] : headPoint;

            const dA = vsub(prevPoint, curPoint);
            const dB = vsub(nextPoint, curPoint);
            let gamma = Math.atan2(dA[1], dA[0]);
            let theta = Math.atan2(dB[1], dB[0]);
            if (gamma < 0) gamma += Math.PI * 2;
            if (theta < 0) theta += Math.PI * 2;
            const beta = (Math.PI * 2 + theta - gamma) % (Math.PI * 2);
            const alpha = Math.PI / 2 - beta / 2;

            const b = vdist(prevPoint, curPoint) || 0.0001;
            const a = vdist(curPoint, nextPoint) || 0.0001;

            controlPointDistance = cpDist(prevPoint, curPoint);
            const k1 = controlPointDistance / b;
            const zPrim = vadd(curPoint, vmul(vsub(prevPoint, curPoint), k1));
            const secondCP = vrot(zPrim, alpha, curPoint);

            curves.push([prevPoint, firstCP, secondCP, curPoint]);

            controlPointDistance = cpDist(curPoint, nextPoint);
            const k2 = controlPointDistance / a;
            const qPrim = vadd(curPoint, vmul(vsub(nextPoint, curPoint), k2));
            firstCP = vrot(qPrim, -alpha, curPoint);

            prevPoint = curPoint;
        }

        const lastCP = headOrTailCP(headPoint, headAdj, controlPointDistance, headAnchorType);
        curves.push([prevPoint, firstCP, lastCP, headPoint]);

        return curves;
    }

    function renderArrowPath(arrow: ArrowData): string {
        const curves = computeBezierCurves(arrow);
        if (curves.length === 0) return '';

        const color = resolveColor(arrow.style?.color_role);
        const thickness = arrow.style?.thickness || DEFAULT_ARROW_THICKNESS;

        const d = curves.map(([s, c1, c2, e]) =>
            `M ${s[0]} ${s[1]} C ${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${e[0]} ${e[1]}`
        ).join(' ');

        return `<path d="${d}" stroke="${color}" stroke-width="${thickness}" fill="none" stroke-linecap="round" marker-end="url(#ah)"/>`;
    }

} // end init

init();
