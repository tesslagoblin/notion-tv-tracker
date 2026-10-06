# Notion TV Tracker

A personal TV tracker built on Notion and the TMDB API, with taste-based tagging
and a weekly "here is what is new that you would actually like" digest.

## Why I built it

The tracker app I used for years, TV Time, was shutting down, and its export was broken, so I lost
a decade of watch history. I rebuilt the library by hand from screenshots and
decided that if I was going to do that once, the data should live somewhere I
own. Notion holds it, TMDB fills in everything tedious, and scripts do the parts
I would never keep up with manually.

The other half of the problem: I could never answer "what should I watch
tonight" from my own list. Genre tags are useless for that. So the tracker
tags shows by *vibe* instead, and uses those tags to rank new releases against
what I actually love.

## What it does that TV Time couldn't

- **It knows which streaming services I pay for.** So "what drama on my
  watchlist can I watch tonight?" skips anything on a service I don't have.
  No Disney+ right now, so Disney+ shows just don't come up.
- **It filters by genre.** TV Time couldn't. Every show carries its TMDB
  genres, so "only comedies" is one filter away.
- **It tags by vibe.** `Chaotic Woman`, `British Awkward`, `Killer Costumes`.
  Pick a mood and get a shortlist.

<!-- screenshot: Shows database in Notion -> images/01-shows-database.png -->

## How it works

1. **Shows go in.** `add_show.py` takes a title, finds it on TMDB, and creates a
   Notion page with the poster, genres, episode count, runtime and air dates
   already filled in. Pass `--pick` and it shows you the candidate matches
   instead of guessing, which matters more than you would think for one-word
   titles and remakes.
2. **Metadata gets hydrated.** Separate passes fill in where it is streaming
   right now, the cover image, and TMDB keywords.
3. **Vibes get tagged.** A curated bank of 29 tags like `Dark Comedy`,
   `Chaotic Woman`, `British Awkward` and `Killer Costumes` gets applied
   automatically from TMDB keywords plus hand-picked whitelists. A show gets
   every vibe that matches, with no cap, so most carry two or three and a few
   carry many more. Stacked across a whole library, these become a map of your
   taste in a way "Comedy, Drama" never will.
4. **Progress tracks itself.** Check off episodes on the show's page and a sync
   script counts them, or just set a number. A formula renders `12 / 22 · 55%`. When you hit the end,
   `make sync` flips the status: `Finished` for a show that is over, `Returning`
   for one that is still making episodes. It knows which is which from Return
   Status, which gets filled in from TMDB when you add the show and kept
   current by `make returns`.
5. **Rewatches get their own lane.** Starting a comfort show over does not wipe
   out the fact that you finished it. A separate set of fields holds your place
   this time through and counts how many passes you have made, so a show can
   honestly be both `Finished` at 100% and `Rewatching` at season 2.
6. **Every Sunday it tells me what is new.** One script pulls upcoming and
   recent releases from TMDB, tags them with the same vibe rules, and scores
   them by how much their vibes overlap with what I am watching right now. A
   new library that is mostly Watchlist has nothing marked Watching yet, so it
   falls back to your Fav shows, then to every tagged show. It drops anything
   already in the library or recommended in the last six weeks, and posts the
   top picks with a reason to a Discord channel through a webhook.
7. **And what is coming back.** Another script refreshes return status and next
   air dates, then lists upcoming new episodes, starred where I am caught up.

<!-- screenshot: Weekly digest -> images/02-weekly-digest.png -->

## Built with

- **Notion** as the database and the entire UI. Two databases, Shows and
  Episodes, with a relation, a rollup and two formulas. Notion API version
  `2025-09-03`.
- **TMDB API** for every piece of metadata: posters, genres, keywords, episode
  lists, air dates, watch providers, return status. Free.
- **Python 3**, standard library only. Nothing to `pip install`. It shells out
  to `curl` for HTTP, which is deliberate: it makes every API call trivial to
  copy out and debug by hand. `doctor.py` checks your keys and your whole Notion
  schema before you run anything else.
- **Claude** (Anthropic) did most of the writing, and more usefully, ran the
  thing day to day. I would send a message like "watched up to season 3 episode
  10 of Vampire Diaries" or "rate The Gentlemen 5 stars" and it would work out
  which rows to touch and do it. Voice notes got transcribed with Whisper, which
  turned out to be the fastest way to log forty shows at once.

<!-- screenshot: Vibes on a show page -> images/03-vibes-tags.png -->


## How to use it yourself

You need a Notion account and a free TMDB key.

1. Create a Notion integration at
   [notion.so/my-integrations](https://www.notion.so/my-integrations) and copy
   the token.
2. Make a page in Notion for the tracker to live on, and share that page with
   the integration. Nothing works until you do this and the error message will
   not tell you.
3. Get a TMDB v3 key at
   [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api).
4. Copy `.env.example` to `.env` and fill it in. `DISCORD_WEBHOOK_URL` is
   optional and only needed for `make post`.
5. Open `scripts/01_create_databases.py` and edit `MY_SERVICES` to the streaming
   services you actually pay for. That list drives the Available Now formula.
6. Create the databases:

        make setup
        make link

   That writes `scripts/db_ids.json`, which every other script reads.
7. Check everything is wired up:

        make check

   This verifies both keys, both databases, and every property the scripts
   expect. Run it any time something behaves oddly.
8. Add your first show:

        make add SHOW="Somebody Somewhere"
        make hydrate
        make tag

9. Once you have a few dozen shows, build the taste profile and try a digest:

        make taste
        make digest

   `make digest` is a dry run, it only prints. `make post` sends it to the
   Discord webhook in `DISCORD_WEBHOOK_URL`. To get one, open the channel's
   settings in Discord, go to Integrations, then Webhooks, and copy the URL.
   The digest ranks against what you are Watching, so mark a few shows
   `Watching` (or tick `Fav`) for the best picks.
10. Check what is coming back:

        make returns

    This refreshes Return Status and Next Air Date for the whole library and
    prints upcoming new episodes, starred where you are caught up. New shows
    already get Return Status when you add them, but renewals and
    cancellations only show up when you run this. I run it every Sunday.

`make help` lists everything. Every target is just a `python3` call, so you can
skip make entirely and run the scripts directly from `scripts/`.

### Views worth building in Notion

- **Available Now** - filter on the formula. Your "what can I watch tonight"
  list, already narrowed to things you can actually stream.
- **Gallery by Status** - covers on. This is the one that makes it feel like an
  app instead of a spreadsheet.
- **Filter by Vibe** - pick a mood, get a shortlist. The whole reason the tags
  exist.

<!-- screenshot: Available Now view -> images/04-available-now.png -->

## What I would build next

- **Automatic tagging for the last 11%.** `vibe_report.py` now tells you which
  shows have no vibes, but fixing them is still a manual edit to `vibe_bank.py`.
  Sending the synopsis to an LLM for a suggested tag set would close the gap
  without me picking keywords by hand.
- **Let it read my actual viewing.** Everything is self-reported. Pulling from
  streaming service history would make progress tracking automatic.
- **Per-episode ratings that add up.** The Episodes table has a Rating field
  nothing uses yet. Season-level averages would be a nice way to see where a
  show fell apart.

## Docs

- [Schema](docs/schema.md) - every field, who writes it, and what the formulas do
- [Vibes](docs/vibes.md) - how the tagging works and how to tune it
- [Workflow](docs/workflow.md) - the day to day commands
- [Example output](docs/example-output.md) - what the digest and reports look like

## A note on the code

These scripts were built through months of daily use, each one added when a
real need showed up. They are numbered roughly in the order you would run them. They are chatty, they print a
lot, and they are meant to be read and edited rather than installed. If you want
different vibes, edit `vibe_bank.py`. If you want a different schema, edit
`01_create_databases.py` before you run it.
