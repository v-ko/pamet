# Refactoring Plan: Localize CanvasPageRenderer in PageView (Corrected)

## 1. Goal
Fix rendering regressions by modifying the existing `CanvasPageRenderer` to be instantiated and used locally within the `PageView` component's lifecycle, removing its dependency on the global `pamet` facade.

## 2. Corrected Plan

### Step A: Refactor `CanvasPageRenderer` (in `DirectRenderer.ts`)
1.  **Update Constructor**: Change the constructor to accept the local `PageViewState` and the canvas `2d_context` it needs, removing the need for `setContext`.
    ```typescript
    constructor(ctx: CanvasRenderingContext2D, pageVS: PageViewState)
    ```
2.  **Localize `renderCurrentPage`**: The method signature will remain the same, but its implementation will be changed to use the `pageVS` and `ctx` provided during instantiation, instead of fetching them from the global `pamet.appViewState`.

### Step B: Refactor `PageController` (in `PageView.tsx`)
1.  **Add Property**: `private renderer?: CanvasPageRenderer;`
2.  **Update `bindEvents`**:
    -   Change signature to `bindEvents(canvas: HTMLCanvasElement)`.
    -   Get the context: `const ctx = canvas.getContext('2d');`
    -   Instantiate the renderer locally: `this.renderer = new CanvasPageRenderer(ctx, this.pageVS);`.
3.  **Update `reaction`**: The existing `reaction` inside `bindEvents` will be modified. The call to `pamet.pageRenderer.renderCurrentPage()` will be changed to `this.renderer?.renderCurrentPage();`.

### Step C: Refactor `PageView.tsx` (Component)
1.  **Update `bindEvents` call**: In the `useEffect` hook (around L458), change the call to pass the canvas element: `controller.bindEvents(canvasRef.current)`.
2.  **Remove Obsolete `useEffect` logic**: The `useEffect` hook (around L472) that calls `pamet.pageRenderer.setContext` is now redundant and will be removed. Paper.js setup will remain if needed in a separate hook.

### Step D: Clean up Global Instantiation
1.  **Remove Global Instance**: Find and delete the line in the project (likely high-level setup) where the global `pamet.pageRenderer` is created (i.e., `new CanvasPageRenderer()`).
