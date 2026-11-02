import { ArrowLeft, LogOut } from 'lucide-react';
import { readPerson, readToken, signOut } from '@/utils/auth';
import { DASHBOARD_URL } from '@/utils/constants';

/**
 * Back to the tools dashboard, and who is signed in. Hidden with nobody signed in:
 * on your own computer, where the API lets everyone through (LISTBOT_AUTH_DISABLED).
 */
export const ToolsBar = () => {
  const person = readPerson(readToken());
  if (!person) return null;

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-2 text-sm sm:px-6">
        <a href={DASHBOARD_URL} className="inline-flex items-center gap-1 font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
          <ArrowLeft className="h-4 w-4" aria-hidden />
          Tools
        </a>
        <div className="flex min-w-0 items-center gap-3">
          <span className="truncate text-gray-500 dark:text-gray-400" title={person.email}>
            {person.name || person.email}
          </span>
          <button
            type="button"
            onClick={signOut}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <LogOut className="h-4 w-4" aria-hidden />
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
};
