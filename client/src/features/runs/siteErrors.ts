import { CircleX, LucideIcon, TriangleAlert } from 'lucide-react';
import type { SiteError } from '@/utils/types';

/** How a site's problem looks, in a sweep's row and in the page's header: red when it's failing (its page changed,
 *  or it blocks the bot), amber when it was out of reach for a moment. */
export const siteErrorLook = (
  status: SiteError['status']
): { icon: LucideIcon; color: string; inRun: string; inHeader: string } =>
  status === 'failed'
    ? { icon: CircleX, color: 'text-red-700 dark:text-red-400', inRun: 'failed', inHeader: 'is failing' }
    : {
        icon: TriangleAlert,
        color: 'text-amber-700 dark:text-amber-400',
        inRun: "couldn't be reached",
        inHeader: "couldn't be reached",
      };
