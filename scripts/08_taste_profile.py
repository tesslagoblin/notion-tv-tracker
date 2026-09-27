"""Analyze hydrated Shows DB to derive my TV taste profile.

Pulls all shows, weights by:
 - Favorites: 3x
 - Finished: 2x
 - Watching / Returning: 1.5x
 - Watchlist / Paused: 1x

Aggregates genre + network + decade + TMDB IDs.
Writes taste_profile.json for the discover cron to use.
"""
import json, os
from collections import Counter, defaultdict
from notion_client import notion, load_db_ids

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def query_shows(cursor=None):
    body = {'page_size': 100}
    if cursor: body['start_cursor'] = cursor
    return notion('POST', f'/data_sources/{SHOWS_DS}/query', body)


def list_all():
    rows = []
    cursor = None
    while True:
        r = query_shows(cursor)
        rows.extend(r.get('results', []))
        if r.get('has_more'):
            cursor = r.get('next_cursor')
        else:
            break
    return rows


def weight(status, favorite):
    base = {'Finished': 2, 'Watching': 1.5, 'Returning': 1.5,
            'Watchlist': 1, 'Paused': 1, 'Dropped': 0.3}
    w = base.get(status, 1)
    if favorite:
        w = max(w, 3)  # favorites always weigh 3x minimum
    return w


def main():
    rows = list_all()
    print(f'Analyzing {len(rows)} shows...')

    genre_weight = Counter()
    network_weight = Counter()
    decade_weight = Counter()
    tmdb_ids = []          # for exclusion list in /discover
    favorite_tmdb = []     # for the "more like these" seed
    genre_by_favorite = Counter()
    network_by_favorite = Counter()

    for row in rows:
        p = row['properties']
        name = ''.join(t.get('plain_text','') for t in p.get('Name',{}).get('title',[]))
        status = (p.get('Status',{}).get('select') or {}).get('name')
        favorite = p.get('Fav',{}).get('checkbox', False)
        genres = [g['name'] for g in p.get('Genre',{}).get('multi_select',[]) or []]
        networks = [n['name'] for n in p.get('Streaming',{}).get('multi_select',[]) or []]
        first_aired = (p.get('First Aired',{}).get('date') or {}).get('start')
        tmdb_id = p.get('TMDB ID',{}).get('number')

        w = weight(status, favorite)
        for g in genres:
            genre_weight[g] += w
            if favorite:
                genre_by_favorite[g] += 1
        for n in networks:
            network_weight[n] += w
            if favorite:
                network_by_favorite[n] += 1
        if first_aired:
            try:
                year = int(first_aired[:4])
                decade = f'{(year // 10) * 10}s'
                decade_weight[decade] += w
            except:
                pass
        if tmdb_id:
            tmdb_ids.append(int(tmdb_id))
            if favorite:
                favorite_tmdb.append({'id': int(tmdb_id), 'name': name})

    top_genres = genre_weight.most_common(10)
    top_networks = network_weight.most_common(10)
    top_decades = decade_weight.most_common()

    print('\n▓ Top genres (weighted):')
    for g, w in top_genres:
        fav_flag = f' ⭐{genre_by_favorite[g]}' if genre_by_favorite[g] else ''
        print(f'   {w:6.1f}  {g}{fav_flag}')
    print('\n▓ Top networks:')
    for n, w in top_networks:
        fav_flag = f' ⭐{network_by_favorite[n]}' if network_by_favorite[n] else ''
        print(f'   {w:6.1f}  {n}{fav_flag}')
    print('\n▓ Decade distribution:')
    for d, w in sorted(top_decades):
        print(f'   {w:6.1f}  {d}')
    print(f'\n▓ Favorites: {len(favorite_tmdb)} shows with TMDB id')
    print(f'▓ Total tracked: {len(tmdb_ids)} shows (exclusion list for /discover)')

    profile = {
        'top_genres': [{'name':g,'weight':w} for g,w in top_genres],
        'top_networks': [{'name':n,'weight':w} for n,w in top_networks],
        'decade_weight': dict(top_decades),
        'favorites': favorite_tmdb,
        'all_tmdb_ids': tmdb_ids,
        'total_shows': len(rows),
    }
    with open(os.path.join(BASE_DIR, 'taste_profile.json'),'w') as f:
        json.dump(profile, f, indent=2)
    print('\n✅ Wrote taste_profile.json')


if __name__ == '__main__':
    main()
