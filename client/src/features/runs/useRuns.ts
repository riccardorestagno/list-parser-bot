import { useCallback, useEffect, useState } from 'react';
import { requestJson } from '@/utils/api';
import { API_BASE_URL, RUNS_SHOWN } from '@/utils/constants';
import type { BotStatus, Run, RunList } from '@/utils/types';

// A page left open keeps up with the schedule: a sweep's result shows without a reload
const REFRESH_MS = 60_000;

/** The latest sweeps and the bot's schedule, loaded together and refreshed every minute while the page is in view. */
export const useRuns = () => {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [runList, botStatus] = await Promise.all([
        requestJson<RunList>(`${API_BASE_URL}/runs?limit=${RUNS_SHOWN}`),
        requestJson<BotStatus>(`${API_BASE_URL}/status`),
      ]);
      setRuns(runList.runs);
      setStatus(botStatus);
      setError(null);
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'The API could not be reached');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load();
    }, REFRESH_MS);
    // Back on the tab after a while: catch up straight away rather than at the next tick
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [load]);

  return { runs, status, error, loading, reload: load };
};
