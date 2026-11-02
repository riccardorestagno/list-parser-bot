import { describe, expect, it } from 'vitest';
import { dayLabel, formatDuration, formatEvery, formatUntil, listNames } from './format';

const NOW = new Date(2026, 10, 1, 12, 0);

describe('dayLabel', () => {
  it('names today and yesterday, and leaves earlier days to their date', () => {
    expect(dayLabel(new Date(2026, 10, 1, 0, 5), NOW)).toBe('Today');
    expect(dayLabel(new Date(2026, 9, 31, 23, 55), NOW)).toBe('Yesterday');
    expect(dayLabel(new Date(2026, 9, 30, 12, 0), NOW)).toBeNull();
  });
});

describe('formatDuration', () => {
  const start = '2026-11-01T12:00:00+00:00';

  it('counts seconds, then minutes, then hours', () => {
    expect(formatDuration(start, '2026-11-01T12:00:45+00:00')).toBe('45 s');
    expect(formatDuration(start, '2026-11-01T12:03:05+00:00')).toBe('3 min 5 s');
    expect(formatDuration(start, '2026-11-01T12:03:00+00:00')).toBe('3 min');
    expect(formatDuration(start, '2026-11-01T13:02:00+00:00')).toBe('1 h 2 min');
  });

  it("says nothing for a sweep that hasn't finished", () => {
    expect(formatDuration(start, null)).toBe('');
  });
});

describe('formatUntil', () => {
  it('counts down in minutes, then hours', () => {
    expect(formatUntil(new Date(2026, 10, 1, 12, 42).toISOString(), NOW)).toBe('in 42 min');
    expect(formatUntil(new Date(2026, 10, 1, 13, 5).toISOString(), NOW)).toBe('in 1 h 5 min');
    expect(formatUntil(new Date(2026, 10, 1, 14, 0).toISOString(), NOW)).toBe('in 2 h');
  });

  it('is due once the moment has come', () => {
    expect(formatUntil(new Date(2026, 10, 1, 11, 59).toISOString(), NOW)).toBe('any moment now');
  });
});

describe('formatEvery', () => {
  it('reads like a schedule', () => {
    expect(formatEvery(90)).toBe('every 90 minutes');
    expect(formatEvery(60)).toBe('every hour');
    expect(formatEvery(120)).toBe('every 2 hours');
  });
});

describe('listNames', () => {
  it('joins names the way a sentence does', () => {
    expect(listNames([])).toBe('');
    expect(listNames(['Cracked'])).toBe('Cracked');
    expect(listNames(['Cracked', 'BuzzFeed'])).toBe('Cracked and BuzzFeed');
    expect(listNames(['Cracked', 'BuzzFeed', 'Screen Rant'])).toBe('Cracked, BuzzFeed and Screen Rant');
  });
});
