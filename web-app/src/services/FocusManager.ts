export class FocusManager {
  private focusInListener: (event: FocusEvent) => void;
  private focusOutListener: (event: FocusEvent) => void;

  constructor() {
    // Subscriptions as arrow functions for proper `this` binding
    this.focusInListener = (event) => this.handleFocusIn(event);
    this.focusOutListener = (event) => this.handleFocusOut(event);

    // Add event listeners
    document.addEventListener('focusin', this.focusInListener);
    document.addEventListener('focusout', this.focusOutListener);
  }

  // Handle focusin event
  handleFocusIn(event: FocusEvent): void {
    const target = event.target as HTMLElement;

    if (target && target.tabIndex === -1) {
      this.correctFocus(); // Shift focus if the current element doesn't have a valid tabIndex
    }
  }

  // Handle focusout event
  handleFocusOut(event: FocusEvent): void {
    // console.log('Focus out:', event.target);
    this.correctFocus(); // Ensure focus moves to the highest tabIndex element
  }

  private correctFocus(): void {
    // Defer the focus correction to the next tick,
    // ensuring React has time to remove/hide the element
    setTimeout(() => {
      // Now safely query for a valid element to focus
      // (e.g., with the highest tabIndex or some other logic).
      // Example:
      const focusableElements = Array.from(
        document.querySelectorAll<HTMLElement>('[tabindex]:not([tabindex="-1"])')
      );

      if (focusableElements.length > 0) {
        // Sort by tabIndex descending, then focus the top one
        focusableElements.sort((a, b) => b.tabIndex - a.tabIndex);
        focusableElements[0].focus();
      }
    }, 0);
  }

  destroy(): void {
    // Remove event listeners
    document.removeEventListener('focusin', this.focusInListener);
    document.removeEventListener('focusout', this.focusOutListener);
  }
}
