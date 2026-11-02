/** Words for times and lists, in the reader's own time zone and language. */

const MINUTE_MS = 60_000;

const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

/** 'Today' or 'Yesterday' when the moment is one of those, otherwise null (the date is shown instead). */
export const dayLabel = (moment: Date, now: Date): 'Today' | 'Yesterday' | null => {
  if (sameDay(moment, now)) return 'Today';
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  return sameDay(moment, yesterday) ? 'Yesterday' : null;
};

export const formatTime = (moment: Date): string =>
  moment.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });

/** "Today, 3:05 PM", "Yesterday, 9:40 AM" or "Oct 28, 6:15 PM" */
export const formatWhen = (iso: string, now: Date = new Date()): string => {
  const moment = new Date(iso);
  const day = dayLabel(moment, now) ?? moment.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return `${day}, ${formatTime(moment)}`;
};

/** How long a sweep took: "45 s", "3 min 5 s", "1 h 2 min"; '' when it hasn't finished. */
export const formatDuration = (startIso: string, endIso: string | null): string => {
  if (!endIso) return '';
  const seconds = Math.max(0, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 1000));
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return seconds % 60 ? `${minutes} min ${seconds % 60} s` : `${minutes} min`;
  return minutes % 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${Math.floor(minutes / 60)} h`;
};

/** Time left until a moment: "in 42 min", "in 1 h 5 min", or "any moment now" once it's due. */
export const formatUntil = (iso: string, now: Date = new Date()): string => {
  const minutes = Math.ceil((new Date(iso).getTime() - now.getTime()) / MINUTE_MS);
  if (minutes <= 0) return 'any moment now';
  if (minutes < 60) return `in ${minutes} min`;
  return minutes % 60 ? `in ${Math.floor(minutes / 60)} h ${minutes % 60} min` : `in ${minutes / 60} h`;
};

/** "every 90 minutes", "every hour", "every 2 hours" */
export const formatEvery = (minutes: number): string => {
  if (minutes === 1) return 'every minute';
  if (minutes === 60) return 'every hour';
  if (minutes > 60 && minutes % 60 === 0) return `every ${minutes / 60} hours`;
  return `every ${minutes} minutes`;
};

/** "Cracked", "Cracked and BuzzFeed", "Cracked, BuzzFeed and Screen Rant" */
export const listNames = (names: string[]): string =>
  names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
