"""Sweeps once, now, from your computer, as the Reddit account in server/.env.

From server/:
    python -m dev.sweep                              # posts the first new list article, and records the run like the schedule does
    python -m dev.sweep --dry-run                    # only looks: says what it would post, and posts and records nothing
    python -m dev.sweep --dry-run --site "Screen Rant"   # one site alone, still only looking

Either way it signs in to Reddit, to see what the subreddit already has.
"""
import argparse

import settings  # noqa: F401  (first: loads server/.env before the modules below read it)

from bot.controller import PARSERS, sweep
from bot.helpers.enums import convert_enum_to_string, convert_string_to_articletype_enum
from db.migrations import init_db
from services import runs
from services.sweep import describe, run_sweep


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Sweep the sites once, now.")
    parser.add_argument("--dry-run", action="store_true",
                        help="find the article it would post, without posting it or recording the run")
    parser.add_argument("--site", choices=[convert_enum_to_string(website) for website in PARSERS],
                        help="with --dry-run, search only this site, even one switched off in bot/config.py")
    args = parser.parse_args(argv)
    if args.site and not args.dry_run:
        parser.error("--site only goes with --dry-run")

    if args.dry_run:
        sites = []
        websites = [convert_string_to_articletype_enum(args.site)] if args.site else None
        found = sweep(create_post=False, sites=sites, websites=websites)
        print(f"\nSearched: {', '.join(search.site for search in sites) or 'nothing'}")
        for search in sites:
            if search.error is not None:
                print(f"{search.site} failed: {describe(search.error)}")
        print(f"Would post from {found.site}: {found.title}\n  {found.article_url}" if found else "Nothing new to post.")
        return

    init_db()
    run = runs.get_run(run_sweep())
    print(f"\nSearched: {', '.join(run['sites_searched']) or 'nothing'}")
    for problem in run["site_errors"]:
        print(f"{problem['site']} {problem['status']}: {problem['error']}")
    if run["post"]:
        print(f"Posted from {run['post']['site']}: {run['post']['title']}\n  {run['post']['reddit_url']}")
    elif run["error"]:
        print(f"{run['status']}: {run['error']}")
    else:
        print("Nothing new to post.")


if __name__ == "__main__":
    main()
