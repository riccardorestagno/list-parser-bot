import { CircleCheck, CircleMinus, CircleX, ExternalLink, LoaderCircle, LucideIcon, TriangleAlert } from 'lucide-react';
import { formatDuration, formatWhen, listNames } from '@/utils/format';
import type { Run, RunStatus } from '@/utils/types';

const LOOKS: Record<RunStatus, { icon: LucideIcon; color: string; spin?: boolean }> = {
  posted: { icon: CircleCheck, color: 'text-green-600 dark:text-green-400' },
  'nothing-new': { icon: CircleMinus, color: 'text-gray-400 dark:text-gray-500' },
  unreachable: { icon: TriangleAlert, color: 'text-amber-500 dark:text-amber-400' },
  failed: { icon: CircleX, color: 'text-red-600 dark:text-red-400' },
  running: { icon: LoaderCircle, color: 'text-blue-600 dark:text-blue-400', spin: true },
};

const headline = (run: Run): string => {
  switch (run.status) {
    case 'posted':
      return run.post ? `Posted from ${run.post.site}` : 'Posted';
    case 'nothing-new':
      return 'Nothing new to post';
    case 'unreachable':
      return "Couldn't reach Reddit or a site";
    case 'failed':
      return 'Failed';
    case 'running':
      return 'Sweeping now';
  }
};

const linkClass = 'text-blue-600 dark:text-blue-400 hover:underline focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500 rounded-sm';

const Searched = ({ sites }: { sites: string[] }) =>
  sites.length ? <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Searched {listNames(sites)}</p> : null;

/** One sweep: how it went, when, and what it posted or why it stopped. */
export const RunItem = ({ run }: { run: Run }) => {
  const look = LOOKS[run.status];
  const Icon = look.icon;
  const duration = formatDuration(run.started_at, run.finished_at);

  return (
    <li className="flex gap-3 px-4 py-4 sm:px-5">
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${look.color} ${look.spin ? 'animate-spin' : ''}`} aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
          <p className="font-medium">{headline(run)}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 tabular-nums">
            <time dateTime={run.started_at} title={new Date(run.started_at).toLocaleString()}>
              {formatWhen(run.started_at)}
            </time>
            {duration && <span> · {duration}</span>}
          </p>
        </div>

        {run.status === 'posted' && run.post && (
          <div className="mt-1 text-sm">
            {run.post.reddit_url ? (
              <a href={run.post.reddit_url} target="_blank" rel="noreferrer" className={`break-words ${linkClass}`}>
                {run.post.title}
              </a>
            ) : (
              <span className="break-words">{run.post.title}</span>
            )}
            <a href={run.post.article_url} target="_blank" rel="noreferrer"
              className="ml-2 inline-flex items-center gap-0.5 whitespace-nowrap text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400">
              Article
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            </a>
          </div>
        )}

        {run.status === 'nothing-new' && <Searched sites={run.sites_searched} />}

        {run.status === 'running' && (
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Searching the sites' latest articles</p>
        )}

        {(run.status === 'unreachable' || run.status === 'failed') && (
          <>
            <p className="mt-1 text-sm break-words text-gray-700 dark:text-gray-300">
              {run.error}
              {run.status === 'unreachable' && <span className="text-gray-500 dark:text-gray-400">. The next sweep tries again.</span>}
            </p>
            {run.sites_searched.length > 0 && (
              // The sweep adds a site before searching it, so the last one is where it stopped
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                Stopped while searching {run.sites_searched[run.sites_searched.length - 1]}
              </p>
            )}
            {run.error_details && (
              <details className="mt-2 text-sm">
                <summary className="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
                  Details
                </summary>
                <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-gray-100 dark:bg-gray-800 p-3 text-xs leading-relaxed">
                  {run.error_details}
                </pre>
              </details>
            )}
          </>
        )}
      </div>
    </li>
  );
};
