import { describe, expect, it } from 'vitest';
import { readDetail } from './api';

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
