# Day to day

Most commands here have a `make` shortcut (`make help` lists them). The episode
tools (`hydrate_episodes.py`, `episodes_to_checkboxes.py`, `mark_caught_up.py`)
run directly with `python3` from `scripts/`.

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

Either edit `Current S/E` and `Watched Count` in Notion directly, or give the
show a checklist of episodes and tick them off as you go.

    python3 hydrate_episodes.py "Show Name"   # pull episode rows from TMDB into Episodes
    python3 episodes_to_checkboxes.py         # turn those rows into checkboxes on the show page
    python3 sync_watched_count.py             # count ticked checkboxes -> Watched Count

`episodes_to_checkboxes.py` works on every show with Status `Watching`. It
writes one `S01E01 - Title` checkbox per episode into the show's page, grouped
by season, then deletes the Episode rows it converted. It only deletes once
Notion has confirmed the checkboxes were written. If that fails for a show, it
says so, leaves that show's rows alone and moves on to the next one.

`sync_watched_count.py` looks at every show that is `Watching` or `Paused` and
reads the checkboxes in the page body, not the Episodes database. It writes the
number ticked to Watched Count and the first unticked episode to Next Episode.
When Watched Count reaches Total Episodes, a `Watching` show flips to
`Finished` (Return Status is Ended) or `Returning` (anything else). It only
writes Watched Count for shows that actually have checkboxes, so it will not
stomp on numbers you set by hand elsewhere.

For a show you finished long ago and never want to click through:

    # edit TARGETS in the file first
    python3 mark_caught_up.py

It sets Watched Count to every aired episode, ticks any episode checkboxes up
to the latest one, and sets Status to `Finished` or `Returning`. With `TARGETS`
empty it stops and tells you to fill it in.

## Check your tagging

    python3 vibe_report.py

Coverage summary plus a list of every show with no vibes, favorites first.
Shows land there when TMDB has thin keyword data for them. Fix by adding the
show to a vibe's `shows` whitelist in `vibe_bank.py`, then re-run the tagger.

## Ticking episodes off, and the one-tap button

    python3 episodes_as_rows.py --watching
    python3 sync_from_count.py

Each show you are watching gets one Episode row per episode, related back to
the show and ticked up to where you already are.

The reason it is rows and not checkboxes in the page body: a to_do block is
invisible to Notion formulas, so body checkboxes cannot move Progress without a
script running. A related row feeds the Watched Episodes rollup, and Progress
updates the moment you tick one. No script in the loop.

### The +1 button

The nicest version of this is a **Button** property on Shows that bumps
Watched Count by one, so you can mark an episode straight from a gallery card.
The Notion API cannot create button properties, so add it by hand once:

New property, type **Button**, then Edit automation: *Edit* -> *This page* ->
**Watched Count** -> and for the value use Notion's formula AI box with
"add 1 to the Watched Count property". It produces `This page.Watched Count + 1`.

Type that formula by hand and it will probably fail. In a button formula the
property has to be reached through `This page.`, and typed quotes often come
out curly, which the parser rejects without saying so clearly. Let the AI box
write it.

A second button with *Edit* -> *This page* -> **Status** -> **Dropped** gives
you a one-tap bail-out that leaves Watched Count alone, so a dropped show still
remembers how far you got.

### Keeping the labels honest

The button only writes Watched Count, so Current S/E, Next Episode and the row
ticks go stale the second you tap it. `sync_from_count.py` reads the count,
works out which episode that is from TMDB, and rewrites all three. It skips any
show that has not drifted, so a quiet run is a single Notion query and it is
cheap to run hourly.

## Rewatching something

Tick **Rewatching** and put your place in **Rewatch S/E**. Leave Status on
`Finished` and leave Watched Count alone, both describe the first time through
and should stay true. Bump **Times Watched** when you finish a pass.

Nothing automated writes these. They are yours.

## Weekly

    python3 08_taste_profile.py     # rebuild taste weights from the library
    python3 09_weekly_discover.py   # dry run, prints the digest
    python3 09_weekly_discover.py --post   # sends to DISCORD_WEBHOOK_URL
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
