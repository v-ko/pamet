import { getLogger } from "fusion/logging";
import { pamet } from "@/app/facade";

const log = getLogger('FocusManager');

/** Visibility check that works inside position:fixed containers (where offsetParent is always null). */
function isElementVisible(el: HTMLElement): boolean {
  return el.offsetWidth > 0 || el.offsetHeight > 0;
}

export interface FocusRegistration {
  selector: string;
  contextKey: string;
  valOnFocus: boolean;
  valOnBlur: boolean;
}

export interface VisibilityRegistration {
  selector: string;
  contextKey: string;
  valOnVisible: boolean;
  valOnHidden: boolean;
}

export class FocusManager {
  private focusInListener: (event: FocusEvent) => void;
  private focusOutListener: (event: FocusEvent) => void;

  private focusRegistrations: Map<string, FocusRegistration> = new Map();
  private visibilityRegistrations: Map<string, VisibilityRegistration> = new Map();

  private activeFocusKey: string | null = null;
  private lastFocusedElement: HTMLElement | null = null;
  private mutationObserver: MutationObserver;

  constructor() {
    this.focusInListener = (event) => this.handleFocusIn(event);
    this.focusOutListener = (event) => this.handleFocusOut(event);

    document.addEventListener('focusin', this.focusInListener);
    document.addEventListener('focusout', this.focusOutListener);

    this.mutationObserver = new MutationObserver(() => this.reevaluateVisibilityContexts());
    this.mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'hidden', 'id']
    });
  }

  public updateContextOnFocus(registration: FocusRegistration) {
    /**
     * When focus is on the element matched by the selector - the
     * contextKey is set to valOnFocus, and vice versa.
     */
    if (this.focusRegistrations.has(registration.selector)) {
      throw new Error(`Focus registration for selector "${registration.selector}" already exists.`);
    }
    this.focusRegistrations.set(registration.selector, registration);
    // log.info('Registered focus tracking for selector', registration.selector);
  }

  public updateContextOnElementVisible(registration: VisibilityRegistration) {
    if (this.visibilityRegistrations.has(registration.selector)) {
      throw new Error(`Visibility registration for selector "${registration.selector}" already exists.`);
    }
    this.visibilityRegistrations.set(registration.selector, registration);
    // log.info('Registered visibility tracking for selector', registration.selector);
    this.reevaluateVisibilityContexts(); // Initial check
  }

  private reevaluateVisibilityContexts() {
    if (this.lastFocusedElement && !this.lastFocusedElement.isConnected) {
      this.lastFocusedElement = null;
    }

    for (const registration of this.visibilityRegistrations.values()) {
      const el = document.querySelector(registration.selector) as HTMLElement | null;
      const isVisible = el ? isElementVisible(el) : false;
      const expectedValue = isVisible ? registration.valOnVisible : registration.valOnHidden;

      if (pamet.context[registration.contextKey] !== expectedValue) {
        log.info(`Visibility change: context '${registration.contextKey}' set to ${expectedValue}`);
        pamet.setContext(registration.contextKey, expectedValue);
      }
    }
  }

  private getDominantElement(elements: HTMLElement[]): HTMLElement | null {
    if (elements.length === 0) return null;
    if (elements.length === 1) return elements[0];

    let dominant = elements[0];
    for (let i = 1; i < elements.length; i++) {
      if (dominant.contains(elements[i])) {
        dominant = elements[i];
      }
    }
    return dominant;
  }

  handleFocusIn(event: FocusEvent): void {
    /**
     * When an element receives focus - we update the context if it's registered for that
     */
    const target = event.target as HTMLElement;
    log.info('FocusIn event on', target);

    const matchedElements: Map<HTMLElement, FocusRegistration> = new Map();
    for (const reg of this.focusRegistrations.values()) {
      const el = target.closest(reg.selector);
      if (el) {
        matchedElements.set(el as HTMLElement, reg);
      }
    }

    const dominantElement = this.getDominantElement(Array.from(matchedElements.keys()));
    // if (dominantElement) {
    //     log.info('Dominant element is', dominantElement);
    // }
    const dominantRegistration = dominantElement ? matchedElements.get(dominantElement) : null;
    const newActiveKey = dominantRegistration ? dominantRegistration.contextKey : null;

    if (this.activeFocusKey !== newActiveKey) {
      // log.info(`Active focus context changing from '${this.activeFocusKey}' to '${newActiveKey}'`);
      if (this.activeFocusKey) {
        const oldReg = [...this.focusRegistrations.values()].find(r => r.contextKey === this.activeFocusKey);
        if (oldReg) {
          // log.info(`Setting old context '${oldReg.contextKey}' to ${oldReg.valOnBlur} (on blur)`);
          pamet.setContext(oldReg.contextKey, oldReg.valOnBlur);
        }
      }

      if (newActiveKey && dominantRegistration) {
        // log.info(`Setting new context '${dominantRegistration.contextKey}' to ${dominantRegistration.valOnFocus} (on focus)`);
        pamet.setContext(dominantRegistration.contextKey, dominantRegistration.valOnFocus);
      }
      this.activeFocusKey = newActiveKey;
    }

    if (target && target.tabIndex > -1) {
      this.lastFocusedElement = target;
    } else if (target && target.tabIndex === -1) {
      // Correct focus always sets to a tabIndex != -1 element, so no recursion risk
      this.correctFocus();
    }
  }

  handleFocusOut(event: FocusEvent): void {
    const relatedTarget = event.relatedTarget as HTMLElement | null;
    log.info('FocusOut event, related target is', relatedTarget);

    if (!relatedTarget) {
      // When the element with focus is removed (e.g. the command palette is closed),
      // we need to correct focus to a sensible element.
      // Deferred to next frame so React can finish unmounting removed elements,
      // preventing correctFocus from picking stale/half-removed DOM nodes.
      requestAnimationFrame(() => this.correctFocus());
      return;
    }

    if (this.activeFocusKey) {
      const reg = [...this.focusRegistrations.values()].find(r => r.contextKey === this.activeFocusKey);
      if (reg) {
        const activeElement = document.querySelector(reg.selector);
        if (activeElement && !activeElement.contains(relatedTarget)) {
          // log.info(`Focus moved out of '${reg.selector}'. Setting context '${reg.contextKey}' to ${reg.valOnBlur}`);
          pamet.setContext(reg.contextKey, reg.valOnBlur);
          this.activeFocusKey = null;
        }
      }
    }
  }

  private correctFocus(): void {
    /**
     * Corrects focus when it is lost (element removed) or lands on a
     * non-focusable element.
     *
     * 1. If the last focused element is still in the DOM, return to it.
     * 2. Otherwise fall back to the visible element with the lowest tabIndex
     *    (in practice the page-view canvas at tabIndex=0).
     */

    // Bail out if focus already landed on a valid element. This happens
    // when the Qt shell sends a synthetic Tab into Chromium: the focusout
    // from the *previous* element has relatedTarget=null (synthetic events
    // don't populate it), which queues correctFocus via rAF. By the time
    // the rAF fires, Chromium has already moved focus to the next element
    // — we must not steal it back.
    const current = document.activeElement as HTMLElement | null;
    if (current && current !== document.body && current.tabIndex >= 0) {
      return;
    }

    let elementToFocus: HTMLElement | null = null;

    // Strategy 1: return to the last focused element if it's still around
    if (this.lastFocusedElement && this.lastFocusedElement.isConnected
        && isElementVisible(this.lastFocusedElement) && this.lastFocusedElement.tabIndex >= 0) {
      elementToFocus = this.lastFocusedElement;
    }

    // Strategy 2: pick the visible focusable element with the lowest tabIndex
    if (!elementToFocus) {
      const candidates = this.getVisibleFocusableElements();
      for (const el of candidates) {
        if (!elementToFocus || el.tabIndex < elementToFocus.tabIndex) {
          elementToFocus = el;
        }
      }
    }

    if (elementToFocus) {
      log.info('Correcting focus to', elementToFocus);
      elementToFocus.focus();
    } else {
      log.warning('Could not find any element to correct focus to.');
    }
  }

  private getVisibleFocusableElements(): HTMLElement[] {
    const elements: HTMLElement[] = [];
    for (const el of document.querySelectorAll<HTMLElement>('[tabindex]:not([tabindex="-1"])')) {
      if (isElementVisible(el)) {
        elements.push(el);
      }
    }
    return elements;
  }

  /**
   * Returns true when the currently focused element has the highest tabIndex
   * among all visible focusable elements in registered areas
   * (i.e. Tab would have nowhere to go).
   */
  atLastTabIndex(): boolean {
    const focused = document.activeElement as HTMLElement | null;
    if (!focused || focused.tabIndex < 0) return true;
    const maxTabIndex = this.getVisibleFocusableElements()
      .reduce((max, el) => Math.max(max, el.tabIndex), -1);
    return focused.tabIndex >= maxTabIndex;
  }

  /**
   * Returns true when the currently focused element has the lowest tabIndex
   * among all visible focusable elements in registered areas
   * (i.e. Shift+Tab would have nowhere to go).
   */
  atFirstTabIndex(): boolean {
    const focused = document.activeElement as HTMLElement | null;
    if (!focused || focused.tabIndex < 0) return true;
    const minTabIndex = this.getVisibleFocusableElements()
      .reduce((min, el) => Math.min(min, el.tabIndex), Infinity);
    return focused.tabIndex <= minTabIndex;
  }

  destroy(): void {
    document.removeEventListener('focusin', this.focusInListener);
    document.removeEventListener('focusout', this.focusOutListener);
    this.mutationObserver.disconnect();
    this.focusRegistrations.clear();
    this.visibilityRegistrations.clear();
  }
}
