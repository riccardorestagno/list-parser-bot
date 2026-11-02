/**
 * Sign-in comes from the tools dashboard (riccardorestagno.com/tools/login). It keeps the
 * token in this browser's storage under `tools.token`, which every page of the site
 * shares; this app reads it from there and sends it to its API.
 *
 * The contract is the dashboard's docs/apps.md: change it there first.
 */
import { LOGIN_URL } from './constants';

export const TOKEN_STORAGE_KEY = 'tools.token';

// When this app last sent someone to sign in, to stop a loop (below)
const SENT_KEY = 'list-parser-bot:sent-to-sign-in';
const LOOP_WINDOW_MS = 30_000;

export const readToken = (): string | null => {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
};

export interface SignedInPerson {
  email: string;
  name: string;
}

/** Who the token names, read without checking it: that's the API's job. */
export const readPerson = (token: string | null): SignedInPerson | null => {
  if (!token) return null;
  try {
    const claims = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
    return typeof claims.email === 'string' ? { email: claims.email, name: claims.name ?? '' } : null;
  } catch {
    return null;
  }
};

/** The dashboard's sign-in page, coming back to this page afterwards. */
export const signInUrl = (location: Pick<Location, 'pathname' | 'search'>): string =>
  `${LOGIN_URL}?next=${encodeURIComponent(location.pathname + location.search)}`;

/**
 * Whether to send someone to sign in again. If this app sent them less than 30 seconds ago
 * and the API still refuses the token, signing in again wouldn't help (the API's key or
 * settings are wrong), and the two pages would bounce them back and forth forever.
 */
export const shouldSendToSignIn = (lastSent: number | null, now: number): boolean =>
  lastSent === null || now - lastSent > LOOP_WINDOW_MS;

/** The API refused the token: off to sign in, unless that's just been tried. */
export const sendToSignIn = (): boolean => {
  let lastSent: number | null = null;
  try {
    const stored = Number(window.sessionStorage.getItem(SENT_KEY));
    lastSent = stored > 0 ? stored : null;
    window.sessionStorage.setItem(SENT_KEY, String(Date.now()));
  } catch {
    // Without storage there's no loop check; the redirect still beats a dead page
  }
  if (!shouldSendToSignIn(lastSent, Date.now())) return false;
  window.location.assign(signInUrl(window.location));
  return true;
};

/** Signs out of every app on this browser: they share the token. */
export const signOut = () => {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Nothing stored to remove
  }
  window.location.assign(LOGIN_URL);
};
