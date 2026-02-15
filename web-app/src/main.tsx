const buildMode = (import.meta.env.BUILD_MODE as 'web' | 'desktop' | undefined) ?? 'web';

// Choose the correct runtime entry at build time. The condition stays for clarity,
// but Vite will tree-shake the unused branch after replacing BUILD_MODE.
switch (buildMode) {
  case 'desktop':
    void import('./main-desktop');
    break;
  case 'web':
    void import('./main-web');
    break;
  default:
    throw new Error(`Unsupported build mode: ${buildMode}`);
}
