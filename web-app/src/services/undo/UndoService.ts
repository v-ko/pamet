import { Delta } from "fusion/model/Delta";
import { getLogger } from "fusion/logging";

const log = getLogger("UndoService");

// Public action name constants for filtering and decoration
export const UNDO_ACTION_NAME = 'undo_user_changes';
export const REDO_ACTION_NAME = 'redo_user_changes';

const MAX_UNDO_HISTORY_SIZE = 1000;

class UndoHistory {
  private _steps: Delta[] = [];
  // Position is "between" items, like Python reference:
  // 0 = before any steps; _steps.length = after last step.
  private _position = 0;

  stepsCount(): number {
    return this._steps.length;
  }

  position(): number {
    return this._position;
  }

  canUndo(): boolean {
    return this._position > 0;
  }

  canRedo(): boolean {
    return this._position < this._steps.length;
  }

  addStep(step: Delta): void {
    // Truncate redo tail if we are not at the end
    if (this._position < this._steps.length) {
      this._steps = this._steps.slice(0, this._position);
    }

    // Cap history size (simple FIFO drop from the beginning)
    if (this._steps.length >= MAX_UNDO_HISTORY_SIZE) {
      this._steps.shift();
      // When dropping the first element and if position was at the end,
      // it stays consistent because we also reduced steps length by 1.
      // If position was in the middle, this also keeps it aligned with the new steps.
      if (this._position > 0) {
        this._position = Math.max(0, this._position - 1);
      }
    }

    this._steps.push(step);
    this._position = this._steps.length;
  }

  // Returns the delta to apply for undo (i.e., reverse of the previous step), and moves the pointer back.
  takeUndoDelta(): Delta | null {
    if (!this.canUndo()) return null;
    const prevIndex = this._position - 1;
    const step = this._steps[prevIndex];
    this._position -= 1;
    return step.reversed();
  }

  // Returns the delta to apply for redo (i.e., the next step), and moves the pointer forward.
  takeRedoDelta(): Delta | null {
    if (!this.canRedo()) return null;
    const step = this._steps[this._position];
    this._position += 1;
    return step;
  }

  clear(): void {
    this._steps = [];
    this._position = 0;
  }
}

/**
 * Undo/Redo Service
 * - Maintains per-page undo histories
 * - Records change sets (as Deltas) after root user actions complete (hooked from PametFacade)
 * - Applies undo/redo by directly applying deltas to the store + view (no repo commit, no uncommitted buffering)
 *
 * NOTE: First iteration records the delta for the current page context.
 *       Future iteration can split by page id if needed.
 */
export class UndoService {
  constructor(private _facade: { applyDelta(delta: Delta): void }) {}
  private _historiesByPageId = new Map<string, UndoHistory>();

  private history(pageId: string): UndoHistory {
    let h = this._historiesByPageId.get(pageId);
    if (!h) {
      h = new UndoHistory();
      this._historiesByPageId.set(pageId, h);
    }
    return h;
  }

  /**
   * Record a change set as a single undo step.
   * Caller is expected to gate this to user-originated root actions only.
   * For the initial implementation, the whole delta is attributed to the provided pageId.
   */
  recordChangeSet(delta: Delta, rootActionName: string, pageId: string): void {
    // Ignore empty deltas
    if (delta.isEmpty()) {
      return;
    }
    const h = this.history(pageId);
    h.addStep(delta);
    log.info(`[recordChangeSet] Recorded step for page=${pageId}, action=${rootActionName ?? "unknown"}`);
  }

  canUndo(pageId: string): boolean {
    return this._historiesByPageId.has(pageId) && this.history(pageId).canUndo();
  }

  canRedo(pageId: string): boolean {
    return this._historiesByPageId.has(pageId) && this.history(pageId).canRedo();
  }

  /**
   * Apply one undo step for the page, ignoring failures (conflicts) per spec.
   * No repo commit; strictly local mutation.
   */
  undo(pageId: string) {
    const h = this._historiesByPageId.get(pageId);
    if (!h || !h.canUndo()) {
      return;
    }
    const deltaToApply = h.takeUndoDelta();
    if (!deltaToApply) return;

    try {
      // Apply via facade to ensure normal applyDelta pipeline
      this._facade.applyDelta(deltaToApply);
    } catch (e) {
      // Ignore failed undos per requirement
      log.warning("[undo] Failed to apply undo delta. Ignoring.", e);
      // Roll forward the pointer back since we didn't actually undo
      // so that history remains consistent for the user
      // By design we "ignore" a failed undo — the next undo attempt should
      // try the previous step again, so move the pointer forward to restore.
      // That means we should revert the pointer change we did in takeUndoDelta.
      // The simplest way: immediately advance position back via takeRedoDelta without applying.
      const redoDelta = h.takeRedoDelta();
      // We intentionally do not apply redoDelta; this restores the pointer only.
      void redoDelta;
    }
  }

  /**
   * Apply one redo step for the page, ignoring failures (conflicts) per spec.
   * No repo commit; strictly local mutation.
   */
  redo(pageId: string) {
    const h = this._historiesByPageId.get(pageId);
    if (!h || !h.canRedo()) {
      return;
    }
    const deltaToApply = h.takeRedoDelta();
    if (!deltaToApply) return;

    try {
      this._facade.applyDelta(deltaToApply);
    } catch (e) {
      log.warning("[redo] Failed to apply redo delta. Ignoring.", e);
      // Restore pointer by moving it back (i.e., pretend redo didn't happen)
      const undoDelta = h.takeUndoDelta();
      void undoDelta;
    }
  }

  clearAll(): void {
    this._historiesByPageId.clear();
  }

  clearForPage(pageId: string): void {
    this._historiesByPageId.delete(pageId);
  }
}
