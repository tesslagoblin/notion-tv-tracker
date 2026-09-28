# Vibes: the part that actually matters

Genre is useless for recommendations. "Comedy, Drama" describes half of
television. The Vibes tags are the fix.

A vibe is a small, opinionated descriptor of what a show *feels* like:
`Dark Comedy`, `Chaotic Woman`, `British Awkward`, `Teen Soap`, `Killer Costumes`,
`Sad Girl`, `Y2K Nostalgia`, `Found Family`. There are 29 in `vibe_bank.py`.

There is no cap. A show gets every vibe that matches, so most land on two or
three and a few rack up many more. That is the point. Stacking tags across a
whole library builds a map of your taste that genre never could.

## How a show gets tagged

`07_auto_vibe_tag.py` checks every show against every vibe and applies each match.
The rules live in `vibe_bank.py` (`show_matches_vibe`), and the weekly digest
uses the same ones on new shows. A vibe fires if any of these hit:

1. The show is on that vibe's explicit `shows` whitelist
2. One of the vibe's `keywords` appears in the show's TMDB keywords
3. One of the vibe's `networks` is in the show's Streaming column

Two things narrow that down:

- `genres`, if a vibe has it, means rules 2 and 3 only count when the show has
  at least one of those genres. `Sitcom Classic` uses it so the `sitcom`
  keyword only lands on things TMDB also calls Comedy. Whitelisted shows skip
  this check.
- `anti_shows` beats everything, whitelist included. Put a show there when a
  keyword keeps tagging it and it clearly does not fit.

`networks` is a slightly misleading name. It is matched against Streaming,
which holds the services you can watch on today (Netflix, Max, Hulu). The
original broadcaster, like BBC One or Channel 4, is not stored anywhere, so a
broadcaster name in `networks` will never match.

## Keyword matching is whole words, and that is on purpose

TMDB keywords are free text. Matching used to be plain substring matching,
and a loose needle caught things nobody meant.

A real example from my library: the `NYC-Set` vibe listed `manhattan` as a
keyword. A show set in **Manhattan, Kansas** got tagged as New York. The fix
was to narrow the needle to `manhattan, new york`. The same trap was sitting
in Reality Comfort, where `drag` would also hit `dragon`.

So now a needle has to match whole words. `drag` hits `drag` and `drag queen`
but not `dragon`. `witch` hits `teen witch` but not `witchcraft`. A phrase like
`manhattan, new york` has to appear as that exact phrase. If you want both
forms of a word, list both.

If a vibe starts showing up on shows that clearly do not fit, look at the
keyword list first. It is usually a needle that is too general, and the fix is
a longer phrase or an `anti_shows` entry.

## Tuning it

Edit `vibe_bank.py` and re-run:

    python3 05_fetch_keywords.py
    python3 07_auto_vibe_tag.py --all

Re-tagging is idempotent, so run it as often as you like. Shows with thin TMDB
keyword data will end up with no vibes at all. Nothing is broken, there is just
nothing to match on, and those are worth hand-tagging in Notion.
