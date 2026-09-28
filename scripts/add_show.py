"""Add one or more shows to the Watchlist by name.

Usage:
  python3 add_show.py "Blackadder" "Father Ted"
  python3 add_show.py --pick "The Office"      # choose from TMDB matches
  python3 add_show.py --id 2316 "The Office"   # skip search, use a known TMDB id

For each name:
  1. Search TMDB /search/tv
  2. Create Notion Shows page with Status=Watchlist + hydrated TMDB fields + cover,
     including Return Status and Next Air Date, so a show you catch up on later
     already knows whether it should land on Finished or Returning
  3. Skip (with warning) if a page with that Name already exists

Without --pick it takes TMDB's first result, which is wrong more often than you
would like for one-word titles, remakes and anything with a recent reboot. It
always prints the matched title and year so you can catch it. When in doubt use
--pick.

After creation, run these to complete hydration:
  python3 03_streaming_hydrate.py
  python3 05_fetch_keywords.py && python3 07_auto_vibe_tag.py --all
Return Status goes stale as shows get renewed or canceled. 10_check_returns.py
(`make returns`) refreshes it for the whole library.
"""
import os, sys, json, subprocess, time, urllib.parse
from notion_client import notion, load_db_ids, tmdb_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def tmdb_get(path, params):
    params = {**params, 'api_key': TMDB_API_KEY}
    q = '&'.join(f'{k}={urllib.parse.quote(str(v), safe="")}' for k, v in params.items())
    url = f'{TMDB_BASE}{path}?{q}'
    r = subprocess.run(['curl', '-s', url], capture_output=True, text=True, timeout=15)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def search_show(name, pick=False):
    r = tmdb_get('/search/tv', {'query': name})
    if not r or not r.get('results'):
        return None
    hits = r['results'][:8]
    if not pick or len(hits) == 1:
        return hits[0]

    print(f'\nMatches for "{name}":')
    for i, h in enumerate(hits, 1):
        year = (h.get('first_air_date') or '????')[:4]
        where = ', '.join(h.get('origin_country') or []) or '??'
        blurb = (h.get('overview') or '')[:80].replace('\n', ' ')
        print(f'  {i}. {h["name"]} ({year}) [{where}] - {blurb}')
    try:
        raw = input('  pick a number, or enter to skip: ').strip()
    except EOFError:
        return hits[0]
    if not raw.isdigit() or not (1 <= int(raw) <= len(hits)):
        return None
    return hits[int(raw) - 1]


def get_details(tmdb_id):
    return tmdb_get(f'/tv/{tmdb_id}', {})


def find_existing(name):
    r = notion('POST', f'/data_sources/{SHOWS_DS}/query', {
        'filter': {'property': 'Name', 'title': {'equals': name}},
        'page_size': 5,
    })
    return r.get('results', [])


def build_properties(name, details):
    props = {
        'Name': {'title': [{'type': 'text', 'text': {'content': name}}]},
        'Status': {'select': {'name': 'Watchlist'}},
        'Fav': {'checkbox': False},
    }
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
    genres = [g['name'] for g in (details.get('genres') or [])][:6]
    if genres:
        props['Genre'] = {'multi_select': [{'name': g} for g in genres]}
    # Same rule as 10_check_returns.py: Canceled folds into Ended.
    tmdb_status = details.get('status') or ''
    if tmdb_status == 'Canceled':
        tmdb_status = 'Ended'
    if tmdb_status:
        props['Return Status'] = {'select': {'name': tmdb_status}}
    next_date = (details.get('next_episode_to_air') or {}).get('air_date')
    if next_date:
        props['Next Air Date'] = {'date': {'start': next_date}}
    return props, poster


def add(name, pick=False, tmdb_id=None):
    existing = find_existing(name)
    if existing:
        return {'name': name, 'skipped': 'already_exists', 'page_id': existing[0]['id']}
    if tmdb_id:
        hit = {'id': tmdb_id}
    else:
        hit = search_show(name, pick=pick)
    if not hit:
        return {'name': name, 'error': 'no_tmdb_hit'}
    details = get_details(hit['id'])
    if not details:
        return {'name': name, 'error': 'no_details'}
    props, poster = build_properties(name, details)
    payload = {
        'parent': {'type': 'data_source_id', 'data_source_id': SHOWS_DS},
        'properties': props,
    }
    if poster:
        payload['cover'] = {'type': 'external', 'external': {'url': f'{TMDB_IMG}{poster}'}}
    r = notion('POST', '/pages', payload)
    if r.get('object') == 'page':
        return {'name': name, 'created': True, 'page_id': r['id'],
                'tmdb_id': details['id'], 'tmdb_name': details.get('name'),
                'tmdb_year': (details.get('first_air_date') or '')[:4]}
    return {'name': name, 'error': json.dumps(r)[:200]}


if __name__ == '__main__':
    if not TMDB_API_KEY:
        print('TMDB_API_KEY missing', file=sys.stderr)
        sys.exit(1)
    args = sys.argv[1:]
    pick = '--pick' in args
    args = [a for a in args if a != '--pick']

    tmdb_id = None
    if '--id' in args:
        i = args.index('--id')
        tmdb_id = int(args[i + 1])
        args = args[:i] + args[i + 2:]

    names = args
    if not names:
        print('usage: python3 add_show.py [--pick] [--id N] "Show 1" "Show 2"', file=sys.stderr)
        sys.exit(1)
    if tmdb_id and len(names) != 1:
        print('--id takes exactly one show name', file=sys.stderr)
        sys.exit(1)

    for n in names:
        res = add(n, pick=pick, tmdb_id=tmdb_id)
        marker = '✓' if res.get('created') else '·' if res.get('skipped') else '✗'
        detail = res.get('tmdb_name') or res.get('skipped') or res.get('error') or ''
        if res.get('created'):
            detail = f"{detail} ({res.get('tmdb_year') or '????'})  tmdb:{res.get('tmdb_id')}"
        print(f'{marker} {n} - {detail}', flush=True)
        time.sleep(0.35)
