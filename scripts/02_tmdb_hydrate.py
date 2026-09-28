"""Hydrate Shows with TMDB metadata: poster, network, genre, ep count, first-aired, TMDB URL.

Uses TMDB public API. Requires TMDB_API_KEY env var (v3 API key).
Sign up free: https://www.themoviedb.org/settings/api

Search strategy per show:
  1. Search TV endpoint with the show's Name
  2. Take top result; extract fields
  3. Optional year hint (many titles have "(2024)" etc - strip and use as year filter)

Skips shows that already have TMDB ID set.
"""
import os, json, subprocess, time, sys, re
from notion_client import notion, load_db_ids, tmdb_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def tmdb_get(path, params):
    if not TMDB_API_KEY:
        return None
    params = {**params, 'api_key': TMDB_API_KEY}
    q = '&'.join(f'{k}={requests_quote(str(v))}' for k,v in params.items())
    url = f'{TMDB_BASE}{path}?{q}'
    r = subprocess.run(['curl','-s',url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        return None


def requests_quote(s):
    import urllib.parse
    return urllib.parse.quote(s, safe='')


YEAR_RE = re.compile(r'\((\d{4})\)\s*$')


def parse_year(name):
    m = YEAR_RE.search(name)
    if m:
        base = YEAR_RE.sub('', name).strip()
        return base, int(m.group(1))
    return name, None


def search_show(name):
    base, year = parse_year(name)
    params = {'query': base}
    if year:
        params['first_air_date_year'] = year
    r = tmdb_get('/search/tv', params)
    if not r or not r.get('results'):
        return None
    return r['results'][0]


def get_details(tmdb_id):
    return tmdb_get(f'/tv/{tmdb_id}', {})


def query_shows(cursor=None):
    body = {'page_size': 100}
    if cursor: body['start_cursor'] = cursor
    return notion('POST', f'/data_sources/{SHOWS_DS}/query', body)


def list_all_shows():
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


def build_update(details):
    """Turn TMDB details into Notion property updates."""
    props = {}
    tmdb_id = details.get('id')
    if tmdb_id:
        props['TMDB ID'] = {'number': tmdb_id}
        props['TMDB URL'] = {'url': f'https://www.themoviedb.org/tv/{tmdb_id}'}
    poster = details.get('poster_path')
    if poster:
        props['Poster'] = {'url': f'{TMDB_IMG}{poster}'}
    if details.get('first_air_date'):
        props['First Aired'] = {'date': {'start': details['first_air_date']}}
    if details.get('number_of_episodes') is not None:
        props['Total Episodes'] = {'number': details['number_of_episodes']}
    ep_runtime = details.get('episode_run_time') or []
    if ep_runtime:
        props['Runtime (min)'] = {'number': ep_runtime[0]}
    # Note: the Streaming column is filled by 03_streaming_hydrate.py from TMDB's
    # watch-provider data, which is what you can actually stream it on today.
    # TMDB's 'networks' is the original broadcaster, which is a different thing.
    genres = [g['name'] for g in (details.get('genres') or [])][:6]
    if genres:
        props['Genre'] = {'multi_select': [{'name': g} for g in genres]}
    # Same rule as 10_check_returns.py: Canceled folds into Ended.
    tmdb_status = details.get('status') or ''
    if tmdb_status == 'Canceled':
        tmdb_status = 'Ended'
    if tmdb_status:
        props['Return Status'] = {'select': {'name': tmdb_status}}
    return props


def cover_from_poster(details):
    poster = details.get('poster_path')
    if not poster:
        return None
    return {'type':'external','external':{'url': f'{TMDB_IMG}{poster}'}}


def hydrate_row(row):
    props = row['properties']
    title_prop = props.get('Name',{}).get('title', [])
    name = ''.join(t.get('plain_text','') for t in title_prop)
    existing_tmdb = props.get('TMDB ID',{}).get('number')
    if existing_tmdb:
        return {'name': name, 'skipped': 'has_tmdb_id'}

    hit = search_show(name)
    if not hit:
        return {'name': name, 'skipped': 'no_search_hit'}
    details = get_details(hit['id'])
    if not details:
        return {'name': name, 'skipped': 'no_details'}

    updates = build_update(details)
    payload = {'properties': updates}
    cover = cover_from_poster(details)
    if cover:
        payload['cover'] = cover
    r = notion('PATCH', f'/pages/{row["id"]}', payload)
    if r.get('object') == 'page':
        return {'name': name, 'tmdb_id': details['id'], 'tmdb_name': details.get('name')}
    return {'name': name, 'error': json.dumps(r)[:200]}


if __name__ == '__main__':
    if not TMDB_API_KEY:
        print('⚠️  TMDB_API_KEY not set. Set it via:  export TMDB_API_KEY=...')
        print('    Get a key free at https://www.themoviedb.org/settings/api')
        sys.exit(1)

    rows = list_all_shows()
    print(f'Hydrating {len(rows)} shows...\n')
    results = []
    for i, row in enumerate(rows):
        res = hydrate_row(row)
        results.append(res)
        marker = '·' if res.get('skipped') else '✓' if res.get('tmdb_id') else '✗'
        print(f'{i+1}/{len(rows)} {marker} {res.get("name","?")} - {res.get("tmdb_name") or res.get("skipped") or res.get("error","?")}', flush=True)
        time.sleep(0.25)  # TMDB rate limit: ~50/sec; Notion: ~3/sec - cap on Notion

    with open(os.path.join(BASE_DIR, 'hydrate_results.json'),'w') as f:
        json.dump(results, f, indent=2)
    ok = sum(1 for r in results if r.get('tmdb_id'))
    skip = sum(1 for r in results if r.get('skipped'))
    err = sum(1 for r in results if r.get('error'))
    print(f'\n✅ Hydrated {ok} • Skipped {skip} • Errors {err}')
