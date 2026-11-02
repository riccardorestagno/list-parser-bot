"""Sweeps once, now, from your computer, as the Reddit account in server/.env.

From server/:
    python -m dev.sweep              # posts the first new list article, and records the run like the schedule does
    python -m dev.sweep --dry-run    # only looks: says what it would post, and posts and records nothing

Either way it signs in to Reddit, to see what the subreddit already has.
"""
import argparse

import settings  # noqa: F401  (first: loads server/.env before the modules below read it)

from bot.controller import sweep
from db.migrations import init_db
from services import runs
from services.sweep import run_sweep


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Sweep the sites once, now.")
    parser.add_argument("--dry-run", action="store_true",
                        help="find the article it would post, without posting it or recording the run")
    args = parser.parse_args(argv)

    if args.dry_run:
        searched = []
        found = sweep(create_post=False, searched=searched)
        print(f"\nSearched: {', '.join(searched) or 'nothing'}")
        print(f"Would post from {found.site}: {found.title}\n  {found.article_url}" if found else "Nothing new to post.")
        return

    init_db()
    run = runs.get_run(run_sweep())
    print(f"\nSearched: {', '.join(run['sites_searched']) or 'nothing'}")
    if run["post"]:
        print(f"Posted from {run['post']['site']}: {run['post']['title']}\n  {run['post']['reddit_url']}")
    elif run["error"]:
        print(f"{run['status']}: {run['error']}")
    else:
        print("Nothing new to post.")


if __name__ == "__main__":
    main()
