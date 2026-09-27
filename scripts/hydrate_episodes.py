"""Hydrate the Episodes DB for one show. Usage:
    python3 hydrate_episodes.py "Show Name"
    python3 hydrate_episodes.py --tmdb 1418
    python3 hydrate_episodes.py --page <notion-page-id>

Reads seasons from TMDB, creates one Episode row per episode, related to the Show.
Skips seasons already fully populated (idempotent - safe to re-run).
"""
import os, json, sys, subprocess, urllib.parse, time
from notion_client import notion, load_db_ids, tmdb_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()
TMDB_BASE = 'https://api.themoviedb.org/3'

ids = load_db_ids()
SHOWS_DS = ids['shows']['data_source_id']
EPS_DS = ids['episodes']['data_source_id']


def tmdb(path, **params):
    params['api_key'] = TMDB_API_KEY
    q = '&'.join(f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in params.items())
    r = subprocess.run(['curl', '-s', f'{TMDB_BASE}{path}?{q}'],
                       capture_output=True, text=True, timeout=20)
    try: return json.loads(r.stdout)
    except: return None


def find_show(query):
    """Locate the Show row by name (case-insensitive) or by TMDB ID."""
    if query.startswith('--tmdb'):
        tmdb_id = int(sys.argv[sys.argv.index('--tmdb') + 1])
        f = {'property': 'TMDB ID', 'number': {'equals': tmdb_id}}
    else:
        f = {'property': 'Name', 'title': {'equals': query}}
    r = notion('POST', f'/data_sources/{SHOWS_DS}/query', {'filter': f, 'page_size': 5})
    results = r.get('results', [])
    if not results:
        # Try contains
        f = {'property': 'Name', 'title': {'contains': query}}
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', {'filter': f, 'page_size': 5})
        results = r.get('results', [])
    return results


def get_existing_episode_keys(show_page_id):
    """Return set of (season, episode) tuples already in the DB for this show."""
    keys = set()
    cursor = None
    while True:
        body = {
            'filter': {'property': 'Related to Shows (Episodes)',
                       'relation': {'contains': show_page_id}},
            'page_size': 100
        }
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{EPS_DS}/query', body)
        for row in r.get('results', []):
            props = row['properties']
            s = props.get('Season', {}).get('number')
            e = props.get('Episode', {}).get('number')
            if s is not None and e is not None:
                keys.add((s, e))
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')
    return keys


def create_episode(show_page_id, season, ep_num, name, air_date, runtime, tmdb_ep_id):
    props = {
        'Name': {'title': [{'text': {'content': name or f'Episode {ep_num}'}}]},
        'Season': {'number': season},
        'Episode': {'number': ep_num},
        'Related to Shows (Episodes)': {'relation': [{'id': show_page_id}]},
    }
    if air_date:
        props['Air Date'] = {'date': {'start': air_date}}
    if runtime:
        props['Runtime (min)'] = {'number': runtime}
    if tmdb_ep_id:
        props['TMDB ID'] = {'number': tmdb_ep_id}
    notion('POST', '/pages', {
        'parent': {'type': 'data_source_id', 'data_source_id': EPS_DS},
        'properties': props,
    })


def hydrate(show_page_id, tmdb_id):
    show = tmdb(f'/tv/{tmdb_id}')
    if not show or 'seasons' not in show:
        print(f'  ✗ TMDB returned no data for id {tmdb_id}')
        return 0
    name = show.get('name', f'TV#{tmdb_id}')
    print(f'  hydrating "{name}" (TMDB {tmdb_id}) - {len(show["seasons"])} seasons')
    existing = get_existing_episode_keys(show_page_id)
    if existing:
        print(f'    {len(existing)} episodes already present - will skip duplicates')

    created = 0
    for season in show['seasons']:
        s_num = season['season_number']
        if s_num == 0:  # skip specials by default
            continue
        detail = tmdb(f'/tv/{tmdb_id}/season/{s_num}')
        if not detail or 'episodes' not in detail:
            continue
        for ep in detail['episodes']:
            e_num = ep.get('episode_number')
            if e_num is None:
                continue
            if (s_num, e_num) in existing:
                continue
            create_episode(
                show_page_id, s_num, e_num,
                ep.get('name'),
                ep.get('air_date'),
                ep.get('runtime'),
                ep.get('id'),
            )
            created += 1
        time.sleep(0.05)  # gentle TMDB throttle
        print(f'    S{s_num}: {len(detail["episodes"])} eps ({created} new so far)')
    return created


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)

    if sys.argv[1] == '--tmdb':
        tmdb_id = int(sys.argv[2])
        # find show by tmdb id
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query',
                   {'filter': {'property': 'TMDB ID', 'number': {'equals': tmdb_id}}})
        results = r.get('results', [])
    elif sys.argv[1] == '--page':
        page_id = sys.argv[2]
        p = notion('GET', f'/pages/{page_id}', None)
        results = [p]
    else:
        query = sys.argv[1]
        results = find_show(query)

    if not results:
        print('No matching show found.')
        sys.exit(1)

    for show_page in results[:1]:
        show_page_id = show_page['id']
        props = show_page['properties']
        tmdb_id = props.get('TMDB ID', {}).get('number')
        name = ''.join(x.get('plain_text', '') for x in props.get('Name', {}).get('title', []))
        if not tmdb_id:
            print(f'"{name}" has no TMDB ID - cannot hydrate.')
            continue
        n = hydrate(show_page_id, tmdb_id)
        print(f'\n✓ Created {n} new episodes for "{name}"')


if __name__ == '__main__':
    main()
