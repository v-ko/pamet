import { useRef, useEffect, useCallback } from "react";

/** Density-bin + time-marker canvas for the replay timeline. */
export function ReplayTimelineCanvas({
    commitTimestamps,
    rangeStart,
    rangeEnd,
    selFracStart,
    selFracEnd,
    width,
    height,
    playheadFrac,
}: {
    commitTimestamps: number[];
    rangeStart: number;
    rangeEnd: number;
    selFracStart: number;
    selFracEnd: number;
    width: number;
    height: number;
    playheadFrac?: number;
}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const rect = canvas.getBoundingClientRect();
        const w = rect.width;
        const h = rect.height;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, w, h);

        const span = rangeEnd - rangeStart;
        if (span <= 0 || w <= 0) return;

        // ── Commit markers (semi-transparent, overlap = visual density cue) ──
        const markerWidth = Math.max(4, w * 0.006);  // ~0.6% of width, min 4px
        ctx.fillStyle = "rgba(100, 180, 255, 0.15)";
        for (const ts of commitTimestamps) {
            const frac = (ts - rangeStart) / span;
            const x = frac * w - markerWidth / 2;
            ctx.fillRect(x, 0, markerWidth, h);
        }

        // Draw dimmed regions outside selection ON TOP of markers
        const selLeftPx = selFracStart * w;
        const selRightPx = selFracEnd * w;
        ctx.fillStyle = "rgba(0, 0, 0, 0.35)";
        if (selLeftPx > 0) ctx.fillRect(0, 0, selLeftPx, h);
        if (selRightPx < w) ctx.fillRect(selRightPx, 0, w - selRightPx, h);

        // ── Time markers ──────────────────────────────────────────
        const spanMs = span;
        const spanDays = spanMs / (1000 * 60 * 60 * 24);
        const spanMonths = spanDays / 30;

        const labelY = h - 4;

        // Year boundaries
        if (spanMonths > 2) {
            ctx.font = "bold 14px sans-serif";
            ctx.textBaseline = "bottom";
            const startDate = new Date(rangeStart);
            let year = startDate.getFullYear();
            // Start from January 1 of the year containing rangeStart
            let d = new Date(year, 0, 1);
            while (d.getTime() <= rangeEnd) {
                const t = d.getTime();
                if (t >= rangeStart) {
                    const x = ((t - rangeStart) / span) * w;
                    ctx.strokeStyle = "rgba(128, 128, 128, 0.5)";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, h);
                    ctx.stroke();

                    ctx.fillStyle = "rgba(200, 200, 200, 0.9)";
                    ctx.textAlign = "left";
                    ctx.fillText(String(d.getFullYear()), x + 3, labelY);
                }
                year++;
                d = new Date(year, 0, 1);
            }
        }

        // Month boundaries
        if (spanMonths <= 48) {
            ctx.font = "bold 12px sans-serif";
            ctx.textBaseline = "bottom";
            const startDate = new Date(rangeStart);
            let year = startDate.getFullYear();
            let month = startDate.getMonth();
            let d = new Date(year, month, 1);
            const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

            while (d.getTime() <= rangeEnd) {
                const t = d.getTime();
                if (t >= rangeStart) {
                    const x = ((t - rangeStart) / span) * w;
                    ctx.strokeStyle = "rgba(128, 128, 128, 0.3)";
                    ctx.lineWidth = 0.5;
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, h);
                    ctx.stroke();

                    // Label (skip if too close to a year label in long spans)
                    if (spanMonths <= 24 || d.getMonth() !== 0) {
                        ctx.fillStyle = "rgba(180, 180, 180, 0.8)";
                        ctx.textAlign = "center";
                        ctx.fillText(monthNames[d.getMonth()], x, labelY - 10);
                    }
                }
                month++;
                if (month > 11) { month = 0; year++; }
                d = new Date(year, month, 1);
            }
        }

        // Day boundaries (only if span < 4 months)
        if (spanMonths < 4) {
            const startDate = new Date(rangeStart);
            const dayStep = spanDays > 60 ? 10 : spanDays > 14 ? 5 : 1;
            let d = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());

            while (d.getTime() <= rangeEnd) {
                const t = d.getTime();
                if (t >= rangeStart && d.getDate() % dayStep === (dayStep === 1 ? 0 : 1)) {
                    const x = ((t - rangeStart) / span) * w;
                    ctx.strokeStyle = "rgba(128, 128, 128, 0.15)";
                    ctx.lineWidth = 0.5;
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, h);
                    ctx.stroke();

                    if (dayStep <= 5) {
                        ctx.fillStyle = "rgba(160, 160, 160, 0.6)";
                        ctx.textAlign = "center";
                        ctx.fillText(String(d.getDate()), x, labelY - 10);
                    }
                }
                d = new Date(d.getTime() + 24 * 60 * 60 * 1000);
            }
        }

        // ── Playhead ──────────────────────────────────────────
        if (playheadFrac !== undefined && playheadFrac >= 0 && playheadFrac <= 1) {
            const x = playheadFrac * w;
            // Vertical line
            ctx.strokeStyle = "rgba(255, 80, 80, 0.9)";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.stroke();
            // Triangle marker at top
            const triSize = 6;
            ctx.fillStyle = "rgba(255, 80, 80, 0.95)";
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x - triSize, -triSize);
            ctx.lineTo(x + triSize, -triSize);
            ctx.closePath();
            ctx.fill();
        } else if (commitTimestamps.length > 0) {
            // "Live" indicator — green diamond at right edge
            const x = w - 4;
            const cy = h / 2;
            const d = 5;
            ctx.fillStyle = "rgba(80, 200, 120, 0.9)";
            ctx.beginPath();
            ctx.moveTo(x, cy - d);
            ctx.lineTo(x + d, cy);
            ctx.lineTo(x, cy + d);
            ctx.lineTo(x - d, cy);
            ctx.closePath();
            ctx.fill();
        }
    }, [commitTimestamps, rangeStart, rangeEnd, selFracStart, selFracEnd, width, playheadFrac]);

    useEffect(() => {
        draw();
    }, [draw]);

    return (
        <canvas
            ref={canvasRef}
            style={{
                width: "100%",
                height: `${height}px`,
                display: "block",
            }}
        />
    );
}
