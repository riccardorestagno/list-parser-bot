/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** The API's address when it isn't the relative /api (set by the deploy workflow) */
  readonly VITE_API_URL?: string;
  /** The release being deployed (v1.4.0), set by the deploy workflow */
  readonly VITE_APP_VERSION?: string;
}
