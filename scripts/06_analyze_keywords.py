"""Cluster analysis on TMDB keywords to find my through-lines.

Compares keyword frequency in Favorites+Finished vs the general library
to surface what she gravitates toward vs what's just "in the library."
"""
import os
import json
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'shows_keywords.json')) as f:
    data = json.load(f)

fav_shows = [s for s in data.values() if s['favorite']]
finished = [s for s in data.values() if s['status'] == 'Finished']
loved = [s for s in data.values() if s['favorite'] or s['status'] == 'Finished']
watchlist = [s for s in data.values() if s['status'] in ('Watchlist','Paused')]

def cnt(shows):
    c = Counter()
    for s in shows:
        for k in set(s['keywords']):
            c[k] += 1
    return c

fav_kw = cnt(fav_shows)
loved_kw = cnt(loved)
watch_kw = cnt(watchlist)
all_kw = cnt(list(data.values()))

print(f'Corpus: {len(data)} shows total | {len(fav_shows)} favorites | {len(finished)} finished | {len(watchlist)} watchlist\n')

print('━━━ TOP 40 KEYWORDS IN FAVORITES ━━━')
for k, v in fav_kw.most_common(40):
    pct_fav = v / len(fav_shows) * 100
    lib_pct = all_kw[k] / len(data) * 100
    lift = pct_fav / lib_pct if lib_pct > 0 else 0
    print(f'  {v:3d} ({pct_fav:4.1f}%)  lift={lift:4.1f}x  {k}')

print('\n━━━ TOP 40 IN LOVED (fav + finished) ━━━')
for k, v in loved_kw.most_common(40):
    print(f'  {v:3d}  {k}')

print('\n━━━ KEYWORDS WITH HIGHEST LIFT vs library (fav rate > 3x + at least 3 hits) ━━━')
lifts = []
for k, v in fav_kw.items():
    if v < 3: continue
    pct_fav = v / len(fav_shows)
    lib_pct = all_kw[k] / len(data)
    if lib_pct == 0: continue
    lift = pct_fav / lib_pct
    if lift >= 3.0:
        lifts.append((lift, v, k))
lifts.sort(reverse=True)
for lift, v, k in lifts[:30]:
    print(f'  lift={lift:4.1f}x  {v:3d} hits  {k}')
