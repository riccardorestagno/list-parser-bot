/** How a sweep ended, or that it hasn't yet (the server's schemas/enums.py: RunStatus) */
export type RunStatus = 'running' | 'posted' | 'nothing-new' | 'unreachable' | 'failed';

/** The list article a sweep posted */
export interface PostedArticle {
  site: string;
  title: string;
  article_url: string;
  reddit_url: string | null;
}

export interface Run {
  id: number;
  /** UTC, ISO 8601 */
  started_at: string;
  finished_at: string | null;
  status: RunStatus;
  sites_searched: string[];
  post: PostedArticle | null;
  /** One line on why it didn't finish */
  error: string | null;
  /** The traceback, for a failure */
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

export interface BotStatus {
  subreddit: string;
  sites: string[];
  schedule: Schedule;
}
