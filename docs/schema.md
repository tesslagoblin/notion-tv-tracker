# Notion schema

Two databases. `01_create_databases.py` builds both.

Notion's 2025-09-03 API splits a database into a **database_id** and a
**data_source_id**. Create pages against the database_id, query against the
data_source_id. Both get written to `db_ids.json`.

## Shows

| Property | Type | Who writes it |
|---|---|---|
| Name | title | you |
| Status | select | you, and scripts on catch-up |
| Fav | checkbox | you |
| Rating | select (1-5 stars) | you |
| Priority | select (High / Medium / Low) | you |
| Current S/E | rich_text | you, `mark_caught_up.py` |
| Watched Count | number | `sync_watched_count.py`, `mark_caught_up.py` |
| Total Episodes | number | TMDB |
| Vibes | multi_select | `07_auto_vibe_tag.py` |
| Genre | multi_select | TMDB |
| Streaming | multi_select | `03_streaming_hydrate.py` |
| Return Status | select | `10_check_returns.py` |
| Next Episode | rich_text | `sync_watched_count.py` |
| Next Air Date | date | `10_check_returns.py` |
| First Aired | date | TMDB |
| Last Watched | date | you |
| Runtime (min) | number | TMDB |
| TMDB ID / TMDB URL / Poster | number / url / url | TMDB |
| Notes | rich_text | you |
| Added | created_time | Notion |
| Episodes | relation -> Episodes | `01 --link` |
| Watched Episodes | rollup (count checked) | derived |
| Progress | formula | derived |
| Available Now | formula | derived |

### Status values

`Watching` / `Returning` / `Paused` / `Watchlist` / `Finished` / `Dropped`

`Watching` flips to `Returning` or `Finished` on its own once Watched Count
reaches Total Episodes. `Returning` means "caught up on a show that is still
making episodes", so it is the state that earns you a ping when a new season
lands. `Finished` means the show is over and so are you.

### Progress

A string, not a percent: `12 / 22 · 55%`. It prefers the Episodes rollup when
episode rows exist and falls back to the plain Watched Count number when they
do not. An earlier version used a raw percent rollup and it lied constantly for
shows with only some episodes populated.

### Available Now

True when a show is on one of your services AND you might actually watch it
(Watching, Paused or Watchlist). Caught-up and finished shows are excluded so
the view stays a to-do list. Edit `MY_SERVICES` in `01_create_databases.py` to
match what you pay for.

## Episodes

| Property | Type |
|---|---|
| Name | title |
| Season / Episode | number |
| Watched | checkbox |
| Watched Date / Air Date | date |
| Runtime (min) | number |
| Rating | select |
| TMDB ID | number |
| Notes | rich_text |
| Related to Shows (Episodes) | relation (made by `01 --link`) |

Empty on purpose. Populate a show's episodes when you start watching it, with
`hydrate_episodes.py`. There is no reason to import ten thousand rows of
history you will never look at.
