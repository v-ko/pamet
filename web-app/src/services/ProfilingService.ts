/**
 * Lightweight profiling service for diagnosing rendering & interaction performance.
 *
 * Usage from the browser console:
 *   profiling.enable()    — start collecting
 *   profiling.report()    — print summary
 *   profiling.reset()     — clear data (without disabling)
 *   profiling.disable()   — stop collecting
 */

interface TimedStats {
    count: number;
    totalMs: number;
    minMs: number;
    maxMs: number;
    totalItems: number; // sum of itemCount passed to track/end
}

export class ProfilingService {
    enabled = false;
    private _timed = new Map<string, TimedStats>();
    private _counters = new Map<string, number>();
    private _sessionStart = 0;

    enable() {
        this.enabled = true;
        this.reset();
        this._sessionStart = performance.now();
        console.log(
            '%c[Profiling] Enabled. Do your operations, then call profiling.report()',
            'color: #0a0; font-weight: bold'
        );
    }

    disable() {
        this.enabled = false;
        console.log('%c[Profiling] Disabled', 'color: #a00');
    }

    reset() {
        this._timed.clear();
        this._counters.clear();
        this._sessionStart = performance.now();
    }

    // ── Lightweight counter (no timing overhead) ──────────────────────
    count(name: string) {
        if (!this.enabled) return;
        this._counters.set(name, (this._counters.get(name) ?? 0) + 1);
    }

    // ── Timed wrapper – use for outer operations ─────────────────────
    track<T>(name: string, fn: () => T, itemCount?: number): T {
        if (!this.enabled) return fn();
        const start = performance.now();
        const result = fn();
        this._recordTimed(name, performance.now() - start, itemCount ?? 0);
        return result;
    }

    // ── Manual begin / end – for functions with multiple returns ──────
    begin(): number {
        return this.enabled ? performance.now() : 0;
    }

    end(name: string, startTime: number, itemCount?: number) {
        if (startTime === 0) return;
        this._recordTimed(name, performance.now() - startTime, itemCount ?? 0);
    }

    // ── Report ───────────────────────────────────────────────────────
    report(): string {
        const sessionMs = performance.now() - this._sessionStart;
        const lines: string[] = [];
        lines.push(`\n=== Profiling Report  (session ${(sessionMs / 1000).toFixed(1)}s) ===\n`);

        // Timed operations sorted by total time desc
        const sorted = [...this._timed.entries()].sort((a, b) => b[1].totalMs - a[1].totalMs);
        if (sorted.length > 0) {
            lines.push('── Timed operations ──');
            for (const [name, s] of sorted) {
                const avg = s.count > 0 ? s.totalMs / s.count : 0;
                const avgItems = s.count > 0 ? s.totalItems / s.count : 0;
                lines.push(
                    `  ${name}` +
                    `  |  calls ${s.count}` +
                    `  |  total ${s.totalMs.toFixed(1)}ms` +
                    `  |  avg ${avg.toFixed(3)}ms` +
                    `  |  min ${s.minMs.toFixed(3)}ms` +
                    `  |  max ${s.maxMs.toFixed(3)}ms` +
                    (s.totalItems > 0 ? `  |  avgItems ${avgItems.toFixed(0)}` : '')
                );
            }
            lines.push('');
        }

        // Counters sorted by count desc
        const counters = [...this._counters.entries()].sort((a, b) => b[1] - a[1]);
        if (counters.length > 0) {
            lines.push('── Counters ──');
            for (const [name, count] of counters) {
                lines.push(`  ${name}  |  ${count}`);
            }
            lines.push('');
        }

        const text = lines.join('\n');
        console.log(text);
        return text;
    }

    // ── internal ─────────────────────────────────────────────────────
    private _recordTimed(name: string, elapsedMs: number, itemCount: number) {
        let s = this._timed.get(name);
        if (!s) {
            s = { count: 0, totalMs: 0, minMs: Infinity, maxMs: 0, totalItems: 0 };
            this._timed.set(name, s);
        }
        s.count++;
        s.totalMs += elapsedMs;
        if (elapsedMs < s.minMs) s.minMs = elapsedMs;
        if (elapsedMs > s.maxMs) s.maxMs = elapsedMs;
        s.totalItems += itemCount;
    }
}


