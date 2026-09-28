# What it actually produces

The digest and report output below uses placeholder titles. The vibe
whitelists in `vibe_bank.py` are my real library, left in on purpose as a
starting point.

## The weekly digest

```
Refreshing exclusion list from Notion...
  551 shows already tracked

Querying TMDB /discover for matches to top genres...
  83 raw candidates before filtering

Fetching keywords for 35 pre-ranked candidates...

Top 3 picks (vibe-weighted, mixed buckets):
  1. Some New Comedy (soon, pop=12, vote=0.0) - vibes: ['British Awkward', 'Ensemble Hangout']
  2. A Period Thing (aired, pop=9, vote=7.4) - vibes: ['Period Piece', 'Killer Costumes']
  3. Spooky Teen Show (later, pop=6, vote=0.0) - vibes: ['Supernatural Teen', 'Witchy / Occult']
```

And the message it posts:

```
new for the watchlist - Sep 27
ranked by vibe overlap with what you are watching - aired / soon / later announced

1. Some New Comedy (2026-10-01) soon - Comedy / Drama
vibes: British Awkward, Ensemble Hangout
Their relationship is over. Their tenancy is not...
https://www.themoviedb.org/tv/000000
```

The useful part is the vibes line. It is not saying "you like comedy", it is
saying "you have 62 British Awkward shows and 93 Ensemble Hangouts, and this is
both".

## Vibe coverage

```
550 shows, 488 tagged (89%), 62 with no vibes

Most used vibes:
   105  Sitcom Classic
    93  Ensemble Hangout
    92  Teen Soap
    84  Dark Comedy
    62  British Awkward

Barely used (2 or fewer): Travel Doc, Absurdist / Sketch
  Either the keyword needles are too narrow, or the tag is not earning its place.

Average tags per tagged show: 2.5
```

That distribution is the actual output of the taste map. Reading it back is how
I found out "Chaotic Woman" was a real pattern for me and not a joke tag.

## Doctor

```
TV tracker doctor

--- keys ---
[  ok  ] Notion token valid (integration: my-tracker)
[  ok  ] TMDB key valid

--- databases ---
[  ok  ] shows: found, 26 properties
[  ok  ] episodes: found, 11 properties

All good. You are ready to run the other scripts.
```

When something is wrong it tells you which property is missing and which script
to run. The most common failure by far is forgetting to share the Notion page
with your integration, which otherwise just returns a confusing 404.
