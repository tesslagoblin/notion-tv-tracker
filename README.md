# Notion TV Tracker

A personal TV tracker built on Notion and the TMDB API, with taste-based tagging
and a weekly "here is what is new that you would actually like" digest.

## Why I built it

The tracker app I used for years shut down, and its export was broken, so I lost
a decade of watch history. I rebuilt the library by hand from screenshots and
decided that if I was going to do that once, the data should live somewhere I
own. Notion holds it, TMDB fills in everything tedious, and scripts do the parts
I would never keep up with manually.

The other half of the problem: I could never answer "what should I watch
tonight" from my own list. Genre tags are useless for that. So the tracker
tags shows by *vibe* instead, and uses those tags to rank new releases against
what I actually love.

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
   automatically from TMDB keywords plus hand-picked whitelists. A show can
   carry five of them. Stacked across a whole library, these become a map of
   your taste in a way "Comedy, Drama" never will.
4. **Progress tracks itself.** Check off episodes and a rollup counts them, or
   just set a number. A formula renders `12 / 22 · 55%`. When you hit the end,
   the status flips on its own: `Finished` for a show that is over, `Returning`
   for one that is still making episodes.
5. **Every Sunday it tells me what is new.** One script pulls upcoming and
   recent releases from TMDB, scores them by how much their vibes overlap with
   my favorites, drops anything already in the library or recommended in the
   last six weeks, and posts the top picks with posters and a reason.
6. **And what is coming back.** Another script checks shows I am caught up on
   and flags returning seasons within two weeks.

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
4. Copy `.env.example` to `.env` and fill it in.
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

   `make digest` is a dry run, it only prints. `make post` actually sends.

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
- **Track rewatches.** There is nowhere to say "I have seen this four times",
  which for a comfort show is the most interesting fact about it.
- **Per-episode ratings that add up.** The Episodes table has a Rating field
  nothing uses yet. Season-level averages would be a nice way to see where a
  show fell apart.

## Docs

- [Schema](docs/schema.md) - every field, who writes it, and what the formulas do
- [Vibes](docs/vibes.md) - how the tagging works and how to tune it
- [Workflow](docs/workflow.md) - the day to day commands
- [Example output](docs/example-output.md) - what the digest and reports look like

## A note on the code

These scripts grew over months of actual use, not as a designed system. They are
numbered roughly in the order you would run them. They are chatty, they print a
lot, and they are meant to be read and edited rather than installed. If you want
different vibes, edit `vibe_bank.py`. If you want a different schema, edit
`01_create_databases.py` before you run it.
