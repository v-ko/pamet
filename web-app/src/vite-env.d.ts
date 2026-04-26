/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_DESKTOP_API_BASE_URL?: string;
    readonly BUILD_MODE?: 'web' | 'desktop';
}
