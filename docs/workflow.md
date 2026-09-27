# Day to day

Every command here has a `make` shortcut. Run `make help` to see them.

## Add a show

    python3 add_show.py "Show Name" "Another Show"
    python3 add_show.py --pick "The Office"      # choose from the matches
    python3 add_show.py --id 2316 "The Office"   # skip search, known TMDB id

Searches TMDB, creates the Notion page with metadata and cover, sets it to
Watchlist. Skips anything already in the library. Then:

    python3 03_streaming_hydrate.py
    python3 05_fetch_keywords.py && python3 07_auto_vibe_tag.py --all

### Watch out for wrong TMDB matches

Without `--pick`, `add_show.py` takes the first search result, which is wrong
more often than you would think. "Dawson's Creek" once resolved to a news
channel and "Freaks and Geeks" to The Wonder Years. One-word names, remakes and
anything with a recent reboot are the usual offenders.

It always prints the matched title and year, so a bad match is visible. Use
`--pick` for anything ambiguous, or `--id` when you already know the TMDB id.

## Track progress

Either edit `Current S/E` and `Watched Count` in Notion directly, or check off
episode rows and let the rollup do it.

    python3 hydrate_episodes.py "Show Name"   # pull episode rows from TMDB
    python3 sync_watched_count.py             # read checkboxes -> Watched Count

`sync_watched_count.py` only writes Watched Count for shows that actually have
episode rows, so it will not stomp on numbers you set by hand elsewhere.

For a show you finished long ago and never want to click through:

    # edit TARGETS in the file first
    python3 mark_caught_up.py

## Check your tagging

    python3 vibe_report.py

Coverage summary plus a list of every show with no vibes, favorites first.
Shows land there when TMDB has thin keyword data for them. Fix by adding the
show to a vibe's `shows` whitelist in `vibe_bank.py`, then re-run the tagger.

## Weekly

    python3 08_taste_profile.py     # rebuild taste weights from the library
    python3 09_weekly_discover.py   # dry run, prints the digest
    python3 09_weekly_discover.py --post
    python3 10_check_returns.py     # new seasons for shows you are caught up on

I run the last two on a Sunday morning cron. `09` keeps a six week rolling
exclusion list in `past_discovers.json` so the same show does not get
recommended at you week after week.

## When something breaks

    python3 doctor.py

Checks both API keys, that the integration can see both databases, and that
every property the scripts expect actually exists with the right type. It
changes nothing, it just tells you what is wrong.

The two failures worth knowing about:

- **404 on a database you can see in your browser.** You did not share the page
  with your integration. Notion returns a 404 rather than a permission error,
  which is deeply unhelpful the first time.
- **A property is missing.** Usually because the schema drifted after a rename
  in Notion. Renaming a column in the UI does not rename it in the scripts, and
  writes to the old name fail silently. `doctor.py` catches this.
