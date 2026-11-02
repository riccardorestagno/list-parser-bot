/**
 * Where the API lives, from the browser's point of view.
 *
 * Deployed, the web app and the API are on different hosts, so the deploy
 * workflow builds VITE_API_URL into the app (it's public, never a secret).
 * Unset, it's a relative /api, which `yarn dev` proxies to the API on your
 * computer (see vite.config.ts).
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_URL || '/api';
export const APP_VERSION: string = import.meta.env.VITE_APP_VERSION || 'dev';

/**
 * The tools dashboard's pages, on the same site but outside this app (which is served
 * under VITE_BASE_PATH), so they're written from the site's root.
 */
export const LOGIN_URL = '/tools/login';
export const DASHBOARD_URL = '/tools/dashboard';

/** How many of the latest sweeps the page lists */
export const RUNS_SHOWN = 20;
