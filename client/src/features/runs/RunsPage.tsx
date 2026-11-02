import { Clock, RefreshCw } from 'lucide-react';
import { APP_VERSION } from '@/utils/constants';
import { formatEvery, formatTime, formatUntil, listNames } from '@/utils/format';
import type { BotStatus } from '@/utils/types';
import { RunItem } from './RunItem';
import { useRuns } from './useRuns';

const card = 'rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm';

/** When the next sweep is, or that this server doesn't sweep on its own. */
const NextSweep = ({ status, sweeping }: { status: BotStatus; sweeping: boolean }) => {
  const { enabled, interval_minutes: interval, next_run_at: next } = status.schedule;

  return (
    <div className={`${card} mt-6 flex items-start gap-3 px-4 py-3 sm:px-5`}>
      <Clock className="mt-0.5 h-5 w-5 shrink-0 text-orange-600 dark:text-orange-400" aria-hidden />
      {enabled && sweeping ? (
        // The schedule only names the next sweep once this one is done
        <p>
          <span className="font-medium">Sweeping now</span>
          <span className="text-gray-500 dark:text-gray-400">, then {formatEvery(interval)}</span>
        </p>
      ) : enabled && next ? (
        <p>
          <span className="font-medium">Next sweep {formatUntil(next)}</span>
          <span className="text-gray-500 dark:text-gray-400">
            {' '}at {formatTime(new Date(next))}, then {formatEvery(interval)}
          </span>
        </p>
      ) : (
        <p>
          <span className="font-medium">This server doesn't sweep on a schedule</span>
          <span className="block text-sm text-gray-500 dark:text-gray-400">
            LISTBOT_SCHEDULE_ENABLED turns it on; the deployed API has it on.
          </span>
        </p>
      )}
    </div>
  );
};

/** The bot's page: what it does, when it next sweeps, and how the latest sweeps went. */
export const RunsPage = () => {
  const { runs, status, error, loading, reload } = useRuns();

  return (
    <main className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-10">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight">
            List Parser Bot
            <span className="ml-2 align-middle text-xs font-normal text-gray-400">{APP_VERSION}</span>
          </h1>
          {status && (
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Posts list articles from {listNames(status.sites)} to{' '}
              <a href={`https://www.reddit.com/r/${status.subreddit}`} target="_blank" rel="noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:underline">
                r/{status.subreddit}
              </a>
              .
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => void reload()}
          disabled={loading}
          aria-label="Refresh"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60 focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </header>

      {status && <NextSweep status={status} sweeping={runs?.[0]?.status === 'running'} />}

      {error && (
        <div role="alert" className="mt-6 rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-sm text-red-800 dark:text-red-300 sm:px-5">
          {runs ? "Couldn't refresh" : "Couldn't load the sweeps"}: {error}
        </div>
      )}

      <section className="mt-8" aria-labelledby="recent-sweeps">
        <h2 id="recent-sweeps" className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Recent sweeps
        </h2>

        {runs === null && !error && (
          <div className={`${card} mt-3 space-y-4 p-5`} aria-busy="true" aria-label="Loading">
            {[0, 1, 2].map((row) => (
              <div key={row} className="h-5 animate-pulse rounded bg-gray-100 dark:bg-gray-800" />
            ))}
          </div>
        )}

        {runs?.length === 0 && (
          <p className={`${card} mt-3 px-4 py-6 text-center text-sm text-gray-600 dark:text-gray-400 sm:px-5`}>
            No sweeps yet. The first one starts with the API, then one {formatEvery(status?.schedule.interval_minutes ?? 90)}.
          </p>
        )}

        {runs && runs.length > 0 && (
          <ul className={`${card} mt-3 divide-y divide-gray-200 dark:divide-gray-700`}>
            {runs.map((run) => <RunItem key={run.id} run={run} />)}
          </ul>
        )}
      </section>
    </main>
  );
};
