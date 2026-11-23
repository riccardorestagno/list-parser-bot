/** How a sweep ended, or that it hasn't yet (the server's schemas/enums.py: RunStatus) */
export type RunStatus = 'running' | 'posted' | 'nothing-new' | 'unreachable' | 'failed';

/** The list article a sweep posted */
export interface PostedArticle {
  site: string;
  title: string;
  article_url: string;
  reddit_url: string | null;
}

/** A site a sweep couldn't search to the end (the server's schemas/run.py: SiteError) */
export interface SiteError {
  site: string;
  /** Out of reach for a moment, or failing (its page changed, or it blocks the bot) */
  status: 'unreachable' | 'failed';
  error: string;
}

export interface Run {
  id: number;
  /** UTC, ISO 8601 */
  started_at: string;
  finished_at: string | null;
  status: RunStatus;
  sites_searched: string[];
  /** The sites it couldn't search to the end; the others went fine */
  site_errors: SiteError[];
  post: PostedArticle | null;
  /** One line on what stopped the sweep as a whole (Reddit, or the bot itself) */
  error: string | null;
  /** The tracebacks, for a failure: each failing site's under its name */
  error_details: string | null;
}

export interface RunList {
  runs: Run[];
}

export interface Schedule {
  /** False on a server that doesn't sweep on its own, such as your computer */
  enabled: boolean;
  interval_minutes: number;
  next_run_at: string | null;
}

/** A site whose latest search went wrong, since the first of the searches in a row that did */
export interface SiteProblem extends SiteError {
  /** UTC, ISO 8601 */
  since: string;
}

export interface BotStatus {
  subreddit: string;
  sites: string[];
  /** Cleared by the next sweep that finds the site working */
  site_problems: SiteProblem[];
  schedule: Schedule;
}
