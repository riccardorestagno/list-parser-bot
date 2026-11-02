/**
 * Small helpers shared by everything that talks to the API.
 *
 * FastAPI reports errors two different ways, so unpacking them lives here
 * rather than being re-implemented next to every fetch call.
 */
import { readToken, sendToSignIn } from './auth';

/** FastAPI returns `detail` as a string for HTTPException, but as an array of
 *  error objects for request-validation failures. Normalize both. */
export const readDetail = (payload: unknown, fallback: string): string => {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          item && typeof item === 'object' && 'msg' in item
            ? String((item as { msg: unknown }).msg)
            : String(item)
        )
        .join('; ');
    }
  }
  return fallback;
};

/**
 * fetch with the signed-in person's token. Every call to the API goes through here:
 * a 401 means the token is missing, expired or doesn't open this app, so the person
 * goes to the dashboard's sign-in page and comes back here once signed in.
 */
export const apiFetch = async (url: string, init: RequestInit = {}): Promise<Response> => {
  const headers = new Headers(init.headers);
  const token = readToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(url, { ...init, headers });
  if (response.status === 401) sendToSignIn();
  return response;
};

/** fetch + JSON + error unpacking, so callers only handle the happy path. */
export const requestJson = async <T>(
  url: string,
  init?: RequestInit
): Promise<T> => {
  const response = await apiFetch(url, init);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(readDetail(payload, `Request failed (${response.status})`));
  }

  return payload as T;
};

export const jsonBody = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
