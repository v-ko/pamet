import { useState, useEffect } from 'react';
import { pamet } from '@/app/facade';
import { appActions } from '@/actions/app';
import { LIGHT_THEME, DARK_THEME, ThemeMode, type CanvasTokens } from '@/app/theme';
import { log } from '../page/PageView';

const BUILTIN_CANVAS: Record<ThemeMode, CanvasTokens> = {
    [ThemeMode.Light]: LIGHT_THEME.canvas,
    [ThemeMode.Dark]: DARK_THEME.canvas,
};

const TOKENS: { role: string; label: string }[] = [
    { role: 'surface', label: 'Canvas Background' },
    { role: 'onSurface', label: 'Canvas Text' },
    { role: 'default', label: 'Default Fill' },
    { role: 'onDefault', label: 'Default Text' },
    { role: 'attention', label: 'Attention Fill' },
    { role: 'onAttention', label: 'Attention Text' },
    { role: 'success', label: 'Success Fill' },
    { role: 'onSuccess', label: 'Success Text' },
    { role: 'neutral', label: 'Neutral Fill' },
];

const MODES: ThemeMode[] = [ThemeMode.Light, ThemeMode.Dark];
const MODE_LABELS: Record<ThemeMode, string> = {
    [ThemeMode.Light]: 'Light mode',
    [ThemeMode.Dark]: 'Dark mode',
};

type AllValues = Record<ThemeMode, Record<string, string>>;

function isValidHex(v: string): boolean {
    return /^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(v);
}

/** Extract #RRGGBB for <input type="color"> (strips alpha). */
function toPickerHex(hex: string, fallback: string): string {
    const h = hex.replace('#', '');
    if (h.length >= 6 && /^[0-9a-fA-F]{6}/.test(h)) return '#' + h.slice(0, 6);
    return '#' + fallback.replace('#', '').slice(0, 6);
}

/** Return the 2-char alpha suffix, or empty string if opaque / 6-char hex. */
function alphaHex(hex: string): string {
    const h = hex.replace('#', '');
    return h.length >= 8 ? h.slice(6, 8) : '';
}

function initValues(initialPalette?: { [mode: string]: { [role: string]: string } }): AllValues {
    const all = {} as AllValues;
    for (const m of MODES) {
        const defaults = BUILTIN_CANVAS[m];
        const persisted = initialPalette?.[m];
        const vals: Record<string, string> = {};
        for (const { role } of TOKENS) {
            vals[role] = persisted?.[role] ?? (defaults[role] as string);
        }
        all[m] = vals;
    }
    return all;
}

function computePaletteDiff(allValues: AllValues): { [mode: string]: { [role: string]: string } } | undefined {
    const palette: { [mode: string]: { [role: string]: string } } = {};
    for (const m of MODES) {
        const defaults = BUILTIN_CANVAS[m];
        const overrides: { [role: string]: string } = {};
        for (const { role } of TOKENS) {
            const v = allValues[m][role];
            if (isValidHex(v) && v !== (defaults[role] as string)) {
                overrides[role] = v;
            }
        }
        if (Object.keys(overrides).length > 0) {
            palette[m] = overrides;
        }
    }
    return Object.keys(palette).length > 0 ? palette : undefined;
}

interface PaletteEditorProps {
    initialPalette?: { [mode: string]: { [role: string]: string } };
    onPaletteChange?: (palette: { [mode: string]: { [role: string]: string } } | undefined) => void;
}

export function PaletteEditor({ initialPalette, onPaletteChange }: PaletteEditorProps) {
    const activeMode = pamet.themeManager.resolvedMode;
    const [values, setValues] = useState<AllValues>(() => initValues(initialPalette));
    const hasChanges = JSON.stringify(computePaletteDiff(values)) !== JSON.stringify(initialPalette);

    // Apply overrides for the currently active mode only
    const applyToTheme = (allValues: AllValues) => {
        const defaults = BUILTIN_CANVAS[activeMode];
        const modeValues = allValues[activeMode];
        const overrides: Partial<CanvasTokens> = {};
        for (const { role } of TOKENS) {
            const v = modeValues[role];
            if (isValidHex(v) && v !== defaults[role]) {
                overrides[role] = v;
            }
        }
        appActions.applyCanvasPalette(
            Object.keys(overrides).length > 0 ? overrides : null
        );
    };

    // Restore persisted palette when the editor unmounts (reverts unsaved previews)
    useEffect(() => () => {
        const projectId = pamet.appViewState.currentProjectId;
        const props = projectId ? pamet.loadProjectProperties(projectId) : undefined;
        const mode = pamet.themeManager.resolvedMode;
        appActions.applyCanvasPalette(props?.canvas_palette?.[mode] ?? null);
    }, []);

    const setColor = (mode: ThemeMode, role: string, hex: string) => {
        const next: AllValues = {
            ...values,
            [mode]: { ...values[mode], [role]: hex },
        };
        setValues(next);
        if (isValidHex(hex)) applyToTheme(next);
        onPaletteChange?.(computePaletteDiff(next));
    };

    const handlePicker = (mode: ThemeMode, role: string, rgb: string) => {
        const a = alphaHex(values[mode][role]);
        setColor(mode, role, a ? rgb + a : rgb);
    };

    const resetOne = (mode: ThemeMode, role: string) => {
        setColor(mode, role, BUILTIN_CANVAS[mode][role] as string);
    };

    const copyAll = () => {
        const out: Record<string, Record<string, string>> = {};
        for (const m of MODES) {
            out[m] = {};
            for (const { role } of TOKENS) out[m][role] = values[m][role];
        }
        navigator.clipboard.writeText(JSON.stringify(out, null, 2)).catch(() => { log.info("Clipboard write failed"); });
    };

    const pasteAll = async () => {
        try {
            const text = await navigator.clipboard.readText();
            const parsed = JSON.parse(text);
            const next = { ...values };
            for (const m of MODES) {
                const modeData = parsed[m] ?? parsed; // accept flat or nested
                if (typeof modeData !== 'object') continue;
                next[m] = { ...values[m] };
                for (const { role } of TOKENS) {
                    if (modeData[role] && isValidHex(modeData[role])) {
                        next[m][role] = modeData[role];
                    }
                }
            }
            setValues(next);
            applyToTheme(next);
            onPaletteChange?.(computePaletteDiff(next));
        } catch { /* ignore invalid clipboard */ }
    };

    return (
        <details>
            <summary style={{ cursor: 'pointer' }}>Project Palette</summary>

            <div style={{ maxHeight: '300px', overflowY: 'auto', padding: '0.25rem 0' }}>
                {MODES.map(mode => {
                    const defaults = BUILTIN_CANVAS[mode];
                    const isActive = mode === activeMode;
                    return (
                        <div key={mode}>
                            <div style={{
                                fontWeight: 'bold', fontSize: '0.85em',
                                padding: '0.35rem 0 0.15rem',
                                color: isActive ? 'var(--color-text)' : 'var(--color-text-muted)',
                            }}>
                                {MODE_LABELS[mode]}{isActive ? ' (active)' : ''}
                            </div>
                            {TOKENS.map(({ role, label }) => {
                                const val = values[mode][role];
                                const modified = val !== (defaults[role] as string);
                                return (
                                    <div key={role} style={{
                                        display: 'flex', alignItems: 'center', gap: '0.25rem',
                                        padding: '2px 0', fontSize: '0.85em',
                                    }}>
                                        <span style={{ flex: '1 1 auto', minWidth: 0 }}>
                                            {label}
                                            <span style={{ fontFamily: 'monospace', fontSize: '0.8em', color: 'var(--color-text-faded)', marginLeft: '0.3em' }}>{role}</span>
                                        </span>
                                        <input
                                            type="color"
                                            value={toPickerHex(val, defaults[role] as string)}
                                            onChange={e => handlePicker(mode, role, e.target.value)}
                                            title={`Pick color for ${label}`}
                                            style={{
                                                width: '1.75rem', height: '1.5rem',
                                                padding: 0, border: 'none',
                                                cursor: 'pointer', flexShrink: 0,
                                            }}
                                        />
                                        <input
                                            type="text"
                                            value={val}
                                            onChange={e => setColor(mode, role, e.target.value)}
                                            className="dialog-input"
                                            style={{
                                                width: '5.5rem', fontFamily: 'monospace',
                                                fontSize: '0.9em', padding: '1px 4px', flexShrink: 0,
                                            }}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => resetOne(mode, role)}
                                            disabled={!modified}
                                            title="Restore default"
                                            style={{
                                                background: 'none', border: 'none',
                                                cursor: modified ? 'pointer' : 'default',
                                                opacity: modified ? 1 : 0.3,
                                                padding: '0 2px', lineHeight: 1,
                                            }}
                                        >↺</button>
                                    </div>
                                );
                            })}
                        </div>
                    );
                })}
            </div>

            {hasChanges && (
                <div style={{
                    fontSize: '0.8em', fontStyle: 'italic',
                    color: 'var(--color-text-muted)', padding: '0.25rem 0',
                }}>Previewing changes — save to apply</div>
            )}

            <div style={{ display: 'flex', gap: '0.25rem', paddingTop: '0.25rem' }}>
                <button type="button" className="btn" onClick={copyAll}
                    style={{ fontSize: '0.85em' }}>Copy</button>
                <button type="button" className="btn" onClick={pasteAll}
                    style={{ fontSize: '0.85em' }}>Paste</button>
            </div>
        </details>
    );
}
