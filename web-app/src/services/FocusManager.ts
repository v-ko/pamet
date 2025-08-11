import { getLogger } from "fusion/logging";
import { pamet } from "@/core/facade";

const log = getLogger('FocusManager');

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
    for (const registration of this.visibilityRegistrations.values()) {
      const el = document.querySelector(registration.selector) as HTMLElement | null;
      const isVisible = el ? el.offsetParent !== null : false;
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
    const target = event.target as HTMLElement;
    // log.info('FocusIn event on', target);

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
      // log.info('Focused element has tabIndex -1, correcting focus.');
      this.correctFocus();
    }
  }

  handleFocusOut(event: FocusEvent): void {
    const relatedTarget = event.relatedTarget as HTMLElement | null;
    // log.info('FocusOut event, related target is', relatedTarget);

    if (!relatedTarget) {
      // log.info('Focus left the document, correcting focus.');
      this.correctFocus();
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
    setTimeout(() => {
      let elementToFocus: HTMLElement | null = null;

      // Strategy 1: Go back to what you were doing.
      // We check what was the last thing you clicked on.
      if (this.lastFocusedElement) {
        // Find the main component area (e.g., the note editor or the page view) that contains the last element.
        // We pick the most specific one (e.g., note editor wins over the page view if it's inside it).
        const matchedElements: Map<HTMLElement, FocusRegistration> = new Map();
        for (const reg of this.focusRegistrations.values()) {
          const el = this.lastFocusedElement.closest(reg.selector);
          if (el) {
            matchedElements.set(el as HTMLElement, reg);
          }
        }
        const dominantElement = this.getDominantElement(Array.from(matchedElements.keys()));

        if (dominantElement) {
          // If that main area itself can be focused, let's focus it.
          if (dominantElement.matches('[tabindex]:not([tabindex="-1"])')) {
            elementToFocus = dominantElement;
          } else {
            // Otherwise, find the first thing we can focus inside it.
            elementToFocus = dominantElement.querySelector<HTMLElement>('[tabindex]:not([tabindex="-1"])');
          }
        }
      }

      // Strategy 2: If strategy 1 fails, find any active component on screen.
      // This is a fallback in case the last thing you were doing is now gone.
      if (!elementToFocus) {
        // Find all visible registered components (e.g., page view, note editor).
        const allVisibleElements = [];
        for (const reg of this.focusRegistrations.values()) {
          const el = document.querySelector(reg.selector) as HTMLElement | null;
          if (el && el.offsetParent !== null) { // is visible
            allVisibleElements.push(el);
          }
        }
        // Pick the most specific one that's visible.
        const dominantVisibleElement = this.getDominantElement(allVisibleElements);
        if (dominantVisibleElement) {
          // If that main area itself can be focused, let's focus it.
          if (dominantVisibleElement.matches('[tabindex]:not([tabindex="-1"])')) {
            elementToFocus = dominantVisibleElement;
          } else {
            // Otherwise, find the first thing we can focus inside it.
            elementToFocus = dominantVisibleElement.querySelector<HTMLElement>('[tabindex]:not([tabindex="-1"])');
          }
        }
      }

      if (elementToFocus) {
        log.info('Correcting focus to', elementToFocus);
        elementToFocus.focus();
      } else {
        log.warning('Could not find any element to correct focus to.');
      }
    }, 0);
  }

  destroy(): void {
    document.removeEventListener('focusin', this.focusInListener);
    document.removeEventListener('focusout', this.focusOutListener);
    this.mutationObserver.disconnect();
    this.focusRegistrations.clear();
    this.visibilityRegistrations.clear();
  }
}
