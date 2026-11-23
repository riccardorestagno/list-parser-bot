import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, readDetail, requestJson } from './api';

// The tests run without a browser: a window with its storage and address, and an API that answers as told
const memoryStorage = (entries: [string, string][] = []) => {
  const stored = new Map(entries);
  return {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => void stored.set(key, value),
    removeItem: (key: string) => void stored.delete(key),
  };
};

const browserSignedInAs = (token: string | null) => {
  const location = { pathname: '/tools/list-parser-bot/', search: '', assign: vi.fn() };
  vi.stubGlobal('window', {
    localStorage: memoryStorage(token ? [['tools.token', token]] : []),
    sessionStorage: memoryStorage(),
    location,
  });
  return location;
};

const apiAnswering = (status: number, body: unknown = {}) => {
  const fetch = vi.fn<typeof globalThis.fetch>(async () => new Response(JSON.stringify(body), { status }));
  vi.stubGlobal('fetch', fetch);
  return fetch;
};

const sentHeaders = (fetch: ReturnType<typeof apiAnswering>) => new Headers(fetch.mock.calls[0][1]?.headers);

afterEach(() => vi.unstubAllGlobals());

describe('readDetail', () => {
  it('reads an HTTPException message', () => {
    expect(readDetail({ detail: 'No profile with id 4' }, 'fallback')).toBe('No profile with id 4');
  });

  it('joins request-validation errors', () => {
    const payload = { detail: [{ msg: 'Field required' }, { msg: 'Too long' }] };
    expect(readDetail(payload, 'fallback')).toBe('Field required; Too long');
  });

  it('falls back when there is nothing to read', () => {
    expect(readDetail(null, 'fallback')).toBe('fallback');
    expect(readDetail({ message: 'x' }, 'fallback')).toBe('fallback');
  });
});

describe('apiFetch', () => {
  it('sends the token the dashboard stored, and none when nobody has signed in', async () => {
    browserSignedInAs('a-token');
    const signedIn = apiAnswering(200);
    await apiFetch('/api/runs');
    expect(sentHeaders(signedIn).get('Authorization')).toBe('Bearer a-token');

    browserSignedInAs(null);
    const signedOut = apiAnswering(200);
    await apiFetch('/api/runs');
    expect(sentHeaders(signedOut).has('Authorization')).toBe(false);
  });

  it('sends someone to sign in when the API refuses their token, and not for other failures', async () => {
    const refused = browserSignedInAs('an-expired-token');
    apiAnswering(401);
    await apiFetch('/api/runs');
    expect(refused.assign).toHaveBeenCalledWith('/tools/login?next=%2Ftools%2Flist-parser-bot%2F');

    const failing = browserSignedInAs('a-token');
    apiAnswering(503);
    await apiFetch('/api/runs');
    expect(failing.assign).not.toHaveBeenCalled();
  });
});

describe('requestJson', () => {
  it('returns what the API sent, or throws its message', async () => {
    browserSignedInAs('a-token');
    apiAnswering(200, { runs: [] });
    await expect(requestJson('/api/runs')).resolves.toEqual({ runs: [] });

    apiAnswering(503, { detail: 'The database is locked' });
    await expect(requestJson('/api/runs')).rejects.toThrow('The database is locked');
  });
});
