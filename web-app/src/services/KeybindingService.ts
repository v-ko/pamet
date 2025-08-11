import { getCommand } from "fusion/libs/Command";
import { getLogger } from "fusion/logging";
import { pamet } from "@/core/facade";

const log = getLogger('KeybindingService');

function contextConditionFulfilled(whenExpression: string): boolean {
  if (whenExpression.includes('&&') || whenExpression.includes('||')) {
    throw new Error('Logical expressions not implemented yet');
  }

  // For now, we only support simple conditions like 'pageHasFocus'
  let condition = whenExpression;
  const contextVal = pamet.context[condition];
  if (contextVal === undefined) {
    throw new Error(`Context condition not found: ${condition}`);
  }

  return contextVal;
}

export interface Keybinding {
  key: string;     // e.g. "Ctrl+Shift+N", "Alt+ArrowUp", "Ctrl+=", "Ctrl+Digit1"
  command: string; // The command name to be looked up in getCommand(commandName)
  when: string;    // e.g. "pageHasFocus", "someContext", etc.
}

/**
 * Maps certain ASCII characters to their (approximate) event.code values.
 * This is a partial table—extend as needed.
 *
 * Reference: https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/code
 */
const ASCII_TO_CODE_MAP: Record<string, string> = {
  // Letters
  a: 'KeyA', b: 'KeyB', c: 'KeyC', d: 'KeyD', e: 'KeyE',
  f: 'KeyF', g: 'KeyG', h: 'KeyH', i: 'KeyI', j: 'KeyJ',
  k: 'KeyK', l: 'KeyL', m: 'KeyM', n: 'KeyN', o: 'KeyO',
  p: 'KeyP', q: 'KeyQ', r: 'KeyR', s: 'KeyS', t: 'KeyT',
  u: 'KeyU', v: 'KeyV', w: 'KeyW', x: 'KeyX', y: 'KeyY',
  z: 'KeyZ',

  // Digits
  '0': 'Digit0', '1': 'Digit1', '2': 'Digit2', '3': 'Digit3', '4': 'Digit4',
  '5': 'Digit5', '6': 'Digit6', '7': 'Digit7', '8': 'Digit8', '9': 'Digit9',

  // Common punctuation
  '=': 'Equal',
  '-': 'Minus',
  '[': 'BracketLeft',
  ']': 'BracketRight',
  '\\': 'Backslash',
  ';': 'Semicolon',
  '\'': 'Quote',
  ',': 'Comma',
  '.': 'Period',
  '/': 'Slash',
  '`': 'Backquote',
  ' ': 'Space',
};

const SPECIAL_KEY_MAP: Record<string, string> = {
  // Arrows
  'up': 'ArrowUp',
  'down': 'ArrowDown',
  'left': 'ArrowLeft',
  'right': 'ArrowRight',

  // Navigation
  'pagedown': 'PageDown',
  'pageup': 'PageUp',

  // Others
  'escape': 'Escape',
  'delete': 'Delete',
  'tab': 'Tab',
  'backspace': 'Backspace',
  'enter': 'Enter',
  'home': 'Home',
  'end': 'End',
  // ... add more as needed
};

/**
 * Data structure for quick lookup. This is what we'll store in the Map.
 *
 * Example:
 *   {
 *     ctrlKey:   true,
 *     shiftKey:  false,
 *     altKey:    false,
 *     metaKey:   false,
 *     code:      'KeyN'  // the event.code for 'n'
 *   }
 */
interface ResolvedKeybinding {
  ctrlKey: boolean;
  shiftKey: boolean;
  altKey: boolean;
  metaKey: boolean;
  code: string;  // The final "event.code" or special code for arrows, etc.
}

/**
 * Convert a user-supplied keybinding string (e.g. "Ctrl+Shift+N")
 * into a ResolvedKeybinding + the original Keybinding object.
 */
function parseAndResolveKeybinding(kb: Keybinding): { resolved: ResolvedKeybinding; original: Keybinding } {
  const parts = kb.key.split('+');
  let ctrlKey = false;
  let shiftKey = false;
  let altKey = false;
  let metaKey = false;

  // We'll temporarily hold the "primary" key string until we figure out its code.
  let primaryPart = '';

  for (const part of parts) {
    const lowered = part.toLowerCase();
    switch (lowered) {
      case 'ctrl':
        ctrlKey = true;
        break;
      case 'shift':
        shiftKey = true;
        break;
      case 'alt':
        altKey = true;
        break;
      case 'cmd':
      case 'meta':
        metaKey = true;
        break;
      default:
        primaryPart = part;  // e.g. "N", "ArrowUp", "Digit1", "="
        break;
    }
  }

  // We only allow ASCII letters/digits/punctuation that exist in ASCII_TO_CODE_MAP,
  // OR a known "special" key like "ArrowUp", "ArrowDown", "Escape", etc.
  // So let's see if the user-specified `primaryPart` is a known "ArrowUp"/"Escape"
  // or can be mapped via ASCII_TO_CODE_MAP.

  let code = '';
  const lower = primaryPart.toLowerCase();

  // If the user wrote "up" (for ArrowUp) or "escape" (for Escape), etc.:
  if (SPECIAL_KEY_MAP[lower]) {
    code = SPECIAL_KEY_MAP[lower];
  } else if (ASCII_TO_CODE_MAP[lower]) {
    // Then fallback to your ASCII map for letters/digits/punctuation
    code = ASCII_TO_CODE_MAP[lower];
  } else {
    // Try ASCII map approach
    const lower = primaryPart.toLowerCase();
    if (ASCII_TO_CODE_MAP[lower]) {
      code = ASCII_TO_CODE_MAP[lower];
    } else {
      throw new Error(
        `Non-ASCII or unsupported primary key: "${primaryPart}". ` +
        `Allowed special keys: ${Object.keys(SPECIAL_KEY_MAP).join(', ')}. ` +
        `Or use ASCII chars mapped in ASCII_TO_CODE_MAP.`
      );
    }
  }

  const resolved: ResolvedKeybinding = { ctrlKey, shiftKey, altKey, metaKey, code };
  return { resolved, original: kb };
}

/**
 * Generate a unique string from a ResolvedKeybinding that we can use as a Map key.
 * This must match exactly between setKeybindings-time and keyDown-time.
 */
function keybindingToMapKey(r: ResolvedKeybinding): string {
  // For example: "ctrl=1|shift=0|alt=0|meta=0|code=KeyN"
  // This is stable and consistent.
  return `ctrl=${r.ctrlKey ? '1' : '0'}|shift=${r.shiftKey ? '1' : '0'}|alt=${r.altKey ? '1' : '0'}|meta=${r.metaKey ? '1' : '0'}|code=${r.code}`;
}

/**
 * Convert a KeyboardEvent into a ResolvedKeybinding for lookup.
 *
 * - We check event.ctrlKey, event.shiftKey, event.altKey, event.metaKey
 * - If event.code is in ASCII_TO_CODE_MAP or a known special code, we use it
 *   directly as `r.code`.
 */
function eventToResolvedKeybinding(event: KeyboardEvent): ResolvedKeybinding {
  // Account for the case where the user presses "Ctrl+Shift+=", etc.
  // This is used for catching zoom in/out events.
  if (event.key === '+' && event.ctrlKey) {
    return {
      ctrlKey: true,
      shiftKey: false,
      altKey: false,
      metaKey: false,
      code: 'Equal',
    };
  }
  if (event.key === '-' && event.ctrlKey) {
    return {
      ctrlKey: true,
      shiftKey: false,
      altKey: false,
      metaKey: false,
      code: 'Minus',
    };
  }

  return {
    ctrlKey: event.ctrlKey,
    shiftKey: event.shiftKey,
    altKey: event.altKey,
    metaKey: event.metaKey,
    code: event.code, // e.g. "KeyN", "Digit1", "ArrowUp", "Escape", "Equal", etc.
  };
}

export class KeybindingService {
  /**
   * A Map whose key is the string from `keybindingToMapKey(resolved)`.
   * The value is the Keybinding object (and possibly the parsed ResolvedKeybinding,
   * but we only need the original Keybinding for the command + when).
   */
  private bindingMap = new Map<string, Keybinding>();

  private keyDownHandler: (event: KeyboardEvent) => void;

  constructor() {
    this.keyDownHandler = (event: KeyboardEvent) => this.handleKeyDown(event);
    window.addEventListener('keydown', this.keyDownHandler);
  }

  /**
   * Overwrite all current bindings with the newly provided ones.
   * We parse them immediately, building a map for constant-time lookups.
   */
  public setKeybindings(bindings: Keybinding[]): void {
    // Clear the current map
    this.bindingMap.clear();

    for (const kb of bindings) {
      try {
        const { resolved, original } = parseAndResolveKeybinding(kb);
        const mapKey = keybindingToMapKey(resolved);

        if (this.bindingMap.has(mapKey)) {
          log.warning(`Duplicate keybinding detected for: ${kb.key}`);
        }

        this.bindingMap.set(mapKey, original);
      } catch (e: any) {
        log.error(`Error parsing keybinding: ${kb.key}: ${e.message}`);
      }
    }
  }

  public destroy(): void {
    window.removeEventListener('keydown', this.keyDownHandler);
    this.bindingMap.clear();
  }

  private handleKeyDown(event: KeyboardEvent): void {
    console.log('Key pressed:', event.key, event.code, event.ctrlKey, event.shiftKey, event.altKey, event.metaKey);
    const resolved = eventToResolvedKeybinding(event);
    const mapKey = keybindingToMapKey(resolved);

    // Check the map for an existing keybinding.
    const matchedBinding = this.bindingMap.get(mapKey);
    if (!matchedBinding) {
      return;
    }

    if (!contextConditionFulfilled(matchedBinding.when)) {
      return;
    }

    // We found a matching keybinding whose 'when' is satisfied.
    event.preventDefault();


    // If it's ctrl+P or ctrl+S, we need to take extra steps
    if ((event.code === 'KeyP' || event.code === 'KeyS') &&
        (event.ctrlKey || event.metaKey) && !event.altKey &&
        (!event.shiftKey || (window as any).chrome || (window as any).opera)) {
      // Prevent the default browser print/save action
        if (event.stopImmediatePropagation) {
            event.stopImmediatePropagation();
        } else {
            event.stopPropagation();
        }
    }

    const cmd = getCommand(matchedBinding.command);
    if (cmd) {
      cmd.function();
    } else {
      log.error(`Command not found with name: ${matchedBinding.command}`);
    }
  }
}
