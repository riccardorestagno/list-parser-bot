import { describe, expect, it } from 'vitest';
import { readPerson, shouldSendToSignIn, signInUrl } from './auth';

const token = (claims: object) => `header.${btoa(JSON.stringify(claims)).replace(/=+$/, '')}.signature`;

describe('signInUrl', () => {
  it('comes back to this page, query included', () => {
    expect(signInUrl({ pathname: '/tools/list-parser-bot/', search: '?x=1' })).toBe(
      '/tools/login?next=%2Ftools%2Flist-parser-bot%2F%3Fx%3D1'
    );
  });
});

describe('shouldSendToSignIn', () => {
  it('sends the first time, and again after a while', () => {
    expect(shouldSendToSignIn(null, 100_000)).toBe(true);
    expect(shouldSendToSignIn(10_000, 100_000)).toBe(true);
  });

  it("doesn't bounce someone straight back", () => {
    expect(shouldSendToSignIn(95_000, 100_000)).toBe(false);
  });
});

describe('readPerson', () => {
  it('reads who the token names', () => {
    expect(readPerson(token({ email: 'a@example.com', name: 'A' }))).toEqual({ email: 'a@example.com', name: 'A' });
  });

  it('gives nobody for no token or an unreadable one', () => {
    expect(readPerson(null)).toBeNull();
    expect(readPerson('nonsense')).toBeNull();
  });
});
