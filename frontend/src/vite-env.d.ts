/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Versioned style imports bypass CSS cached by the demo CDN before no-store.
declare module "*.css?versioned" {}
