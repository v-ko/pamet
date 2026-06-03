import { HexColorData } from "sivkit/primitives/Color";
import { getLogger } from "sivkit/logging";
import { reaction, IReactionDisposer } from "mobx";
// Lazy access: imported circularly but only used at runtime (after module init)
import { pamet } from "@/app/facade";
import { appActions } from "@/actions/app";

const log = getLogger('ThemeManager');

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export enum ThemeMode {
    Light = 'light',
    Dark = 'dark',
}

export enum ThemePreference {
    Light = 'light',
    Dark = 'dark',
    Auto = 'auto',
}

/** Chrome = UI shell (panels, menus, dialogs). Mapped 1:1 to CSS custom properties. */
export interface ChromeTokens {
    // Backgrounds
    'color-bg-white': string;
    'color-bg-light': string;
    'color-bg-medium': string;
    'color-bg-title': string;
    'color-bg-pressed': string;
    'color-bg-subtle': string;
    'color-bg-canvas': string;

    // Text
    'color-text': string;
    'color-text-muted': string;
    'color-text-faded': string;

    // Borders
    'color-light-border': string;
    'color-dark-border': string;

    // Interactive
    'color-hover-light': string;
    'color-close-hover': string;

    // Accent / semantic
    'color-primary': string;
    'color-primary-contrast': string;
    'color-accent': string;
    'color-bg-light-accent': string;
    'color-danger': string;
    'color-danger-contrast': string;
    'color-highlight-search': string;

    // Shadows
    'shadow-sm': string;
    'shadow-md': string;
    'shadow-lg': string;

    // Icon filter (for <img> SVGs that can't inherit currentColor)
    'icon-filter': string;
}

/** Canvas = note/arrow domain colors. Keyed by color-role name. */
export type CanvasTokens = { [role: string]: HexColorData };

export interface ThemeDefinition {
    meta: { name: string; mode: ThemeMode };
    chrome: ChromeTokens;
    canvas: CanvasTokens;
}

// ---------------------------------------------------------------------------
// Built-in themes
// ---------------------------------------------------------------------------

export const LIGHT_THEME: ThemeDefinition = {
    meta: { name: 'Light', mode: ThemeMode.Light },
    chrome: {
        'color-bg-white': '#ffffff',
        'color-bg-light': '#f5f5f5',
        'color-bg-medium': '#dddddd',
        'color-bg-title': '#dddddd',
        'color-bg-pressed': '#cccccc',
        'color-bg-subtle': '#f0f0f0',
        'color-bg-canvas': '#ffffff',

        'color-text': '#333333',
        'color-text-muted': '#595959',
        'color-text-faded': '#888888',

        'color-light-border': '#dddddd',
        'color-dark-border': '#5f5f5f',

        'color-hover-light': '#e0e0e0',
        'color-close-hover': '#777777',

        'color-primary': '#0066cc',
        'color-primary-contrast': '#ffffff',
        'color-accent': '#0066cc',
        'color-bg-light-accent': '#e6f0ff',
        'color-danger': '#dc3545',
        'color-danger-contrast': '#ffffff',
        'color-highlight-search': '#ffeb3b',

        'shadow-sm': '0 0 0.5rem rgba(0,0,0,0.2)',
        'shadow-md': '0 0 0.9375rem rgba(0,0,0,0.2)',
        'shadow-lg': '0 0.5rem 1.5rem rgba(0,0,0,0.5)',

        'icon-filter': 'none',
    },
    canvas: {
        'default': '#0000ff1a',
        'onDefault': '#0000ff',
        'attention': '#ff00001a',
        'onAttention': '#ff0000',
        'success': '#00ff001a',
        'onSuccess': '#00a33c',
        'surface': '#ffffff',
        'onSurface': '#000000',
        'neutral': '#0000001a',
        'transparent': '#00000000',
    },
};

export const DARK_THEME: ThemeDefinition = {
    meta: { name: 'Dark', mode: ThemeMode.Dark },
    chrome: {
        'color-bg-white': '#252529',
        'color-bg-light': '#2c2c31',
        'color-bg-medium': '#38383e',
        'color-bg-title': '#38383e',
        'color-bg-pressed': '#44444b',
        'color-bg-subtle': '#303035',
        'color-bg-canvas': '#121214',

        'color-text': '#e4e4e0',
        'color-text-muted': '#a0a09a',
        'color-text-faded': '#6e6e68',

        'color-light-border': '#3e3e44',
        'color-dark-border': '#606068',

        'color-hover-light': '#38383e',
        'color-close-hover': '#b0ada6',

        'color-primary': '#6eaaff',
        'color-primary-contrast': '#1a1a1e',
        'color-accent': '#6eaaff',
        'color-bg-light-accent': '#1a3054',
        'color-danger': '#f28b82',
        'color-danger-contrast': '#1a1a1e',
        'color-highlight-search': '#524a1a',

        'shadow-sm': '0 0 0.5rem rgba(0,0,0,0.4)',
        'shadow-md': '0 0 0.9375rem rgba(0,0,0,0.5)',
        'shadow-lg': '0 0.5rem 1.5rem rgba(0,0,0,0.7)',

        'icon-filter': 'invert(1) brightness(0.85)',
    },
    canvas: {
        // Ayu-mirage inspired, night-mode (red filter) compatible.
        // R-channel separation: green=135, onSurface=204, default=155, attention=242
        'default': '#9bb9ff1a',     // soft blue fill
        'onDefault': '#9bb9ff',     // soft blue text
        'attention': '#f287791a',   // coral fill
        'onAttention': '#f28779',   // coral text
        'success': '#87d96c1a',     // lime fill
        'onSuccess': '#87d96c',     // lime text
        'surface': '#121214',       // dark slate
        'onSurface': '#cccac2',     // ayu foreground
        'neutral': '#cccac21a',     // neutral fill
        'transparent': '#00000000',
    },
};

const BUILTIN_THEMES: Record<ThemeMode, ThemeDefinition> = {
    [ThemeMode.Light]: LIGHT_THEME,
    [ThemeMode.Dark]: DARK_THEME,
};

// ---------------------------------------------------------------------------
// Persistence keys (exported for facade use)
// ---------------------------------------------------------------------------

export const STORAGE_KEY_PREFERENCE = 'pamet-theme:preference';   // 'light' | 'dark' | 'auto'

// ---------------------------------------------------------------------------
// ThemeManager — pure service, no action calls, no persistence
//
// Responsibilities:
//   - Theme definitions + mode resolution (auto → light/dark via media query)
//   - Reactive DOM sync (MobX reaction on AppViewState.themeResolvedMode)
//   - Canvas color lookup (with optional per-project overrides)
//
// The facade owns the flow:
//   config store delta → resolve mode → call action → reaction fires → DOM
// ---------------------------------------------------------------------------

export class ThemeManager {
    // Canvas color overrides (per-project palette customization)
    private _canvasOverrides: Partial<CanvasTokens> = {};

    private _mediaQuery: MediaQueryList | null = null;
    private _mediaListener: ((e: MediaQueryListEvent) => void) | null = null;
    private _reactionDisposer: IReactionDisposer | null = null;

    // -- Getters (read from AppViewState) -----------------------------------

    get resolvedMode(): ThemeMode {
        return pamet.appViewState.themeResolvedMode;
    }

    get activeTheme(): ThemeDefinition {
        const base = BUILTIN_THEMES[this.resolvedMode];
        return {
            meta: { ...base.meta },
            chrome: { ...base.chrome } as ChromeTokens,
            canvas: { ...base.canvas, ...this._canvasOverrides } as CanvasTokens,
        };
    }

    // -- Lifecycle ----------------------------------------------------------

    /**
     * Set up media query listener, apply initial theme, and start reacting to
     * resolved-mode changes.  Call once at startup, after setAppViewState.
     */
    initialize(initialPref: ThemePreference) {
        this._mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this._mediaListener = () => {
            if (pamet.appViewState.themePreference === ThemePreference.Auto) {
                const resolved = this.resolveMode(ThemePreference.Auto);
                appActions.applyTheme(pamet.appViewState, ThemePreference.Auto, resolved);
            }
        };
        this._mediaQuery.addEventListener('change', this._mediaListener);

        // Set state before the reaction so fireImmediately reads the right value
        const resolved = this.resolveMode(initialPref);
        appActions.applyTheme(pamet.appViewState, initialPref, resolved);

        // Sync CSS custom properties to <html> whenever resolved mode changes
        this._reactionDisposer = reaction(
            () => pamet.appViewState.themeResolvedMode,
            () => this._applyToDOM(),
            { fireImmediately: true },
        );
    }

    dispose() {
        if (this._mediaQuery && this._mediaListener) {
            this._mediaQuery.removeEventListener('change', this._mediaListener);
        }
        this._reactionDisposer?.();
    }

    // -- Public API ---------------------------------------------------------

    /** Resolve a preference to a concrete mode using the system media query. */
    resolveMode(pref: ThemePreference): ThemeMode {
        if (pref === ThemePreference.Auto) {
            return (this._mediaQuery?.matches ?? false) ? ThemeMode.Dark : ThemeMode.Light;
        }
        return pref === ThemePreference.Dark ? ThemeMode.Dark : ThemeMode.Light;
    }

    setCanvasOverrides(overrides: Partial<CanvasTokens>) {
        Object.assign(this._canvasOverrides, overrides);
    }

    clearCanvasOverrides() {
        this._canvasOverrides = {};
    }

    /** Look up a canvas color role from the active theme. */
    canvasColor(role: string): HexColorData {
        const color = this.activeTheme.canvas[role];
        if (color !== undefined) return color;
        log.error(`Canvas color role "${role}" not found in active theme`);
        return '#ff0000';
    }

    // -- Internal -----------------------------------------------------------

    /** Push chrome tokens to CSS custom properties on <html>. */
    private _applyToDOM() {
        const theme = this.activeTheme;
        const root = document.documentElement;

        root.dataset.theme = theme.meta.mode;

        for (const [key, value] of Object.entries(theme.chrome)) {
            root.style.setProperty(`--${key}`, value);
        }
    }
}
