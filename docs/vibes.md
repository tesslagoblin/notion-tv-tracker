# Vibes: the part that actually matters

Genre is useless for recommendations. "Comedy, Drama" describes half of
television. The Vibes tags are the fix.

A vibe is a small, opinionated descriptor of what a show *feels* like:
`Dark Comedy`, `Chaotic Woman`, `British Awkward`, `Teen Soap`, `Killer Costumes`,
`Sad Girl`, `Y2K Nostalgia`, `Found Family`. There are 29 in `vibe_bank.py`.

A show can carry five of them. That is the point. Stacking tags across a whole
library builds a map of your taste that genre never could.

## How a show gets tagged

`07_auto_vibe_tag.py` checks every show against every vibe and applies each match.
A vibe fires if any of these hit:

1. The show is on that vibe's explicit `shows` whitelist
2. One of the vibe's `keywords` appears in the show's TMDB keywords
3. The show is on one of the vibe's `networks`

Then `anti_shows` removes known false positives.

## Keyword matching is substring matching, so be careful

This is the one real trap. TMDB keywords are free text, and matching is
substring based, so a loose needle catches things you did not mean.

A real example from my library: the `NYC-Set` vibe listed `manhattan` as a
keyword. A show set in **Manhattan, Kansas** got tagged as New York. The fix
was to narrow the needle to `manhattan, new york`.

If a vibe starts showing up on shows that clearly do not fit, look at the
keyword list first. It is almost always too short a string.

## Tuning it

Edit `vibe_bank.py` and re-run:

    python3 05_fetch_keywords.py
    python3 07_auto_vibe_tag.py --all

Re-tagging is idempotent, so run it as often as you like. Shows with thin TMDB
keyword data will end up with no vibes at all. Nothing is broken, there is just
nothing to match on, and those are worth hand-tagging in Notion.
