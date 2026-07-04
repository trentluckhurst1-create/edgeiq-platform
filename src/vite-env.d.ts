/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CLERK_PUBLISHABLE_KEY: string
  readonly VITE_ALLOWED_EMAILS: string
  readonly VITE_EDGEIQ_DEV_PREVIEW?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
