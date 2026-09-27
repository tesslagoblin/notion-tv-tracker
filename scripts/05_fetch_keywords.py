"""Fetch TMDB keywords per show - much richer signal than genres.

Keywords are curated micro-descriptors like 'coming-of-age', 'workplace comedy',
'female friendship', 'ensemble cast', 'small town', etc. Perfect for finding
through-lines you are actually chasing beyond broad genre buckets.

Writes shows_keywords.json: { tmdb_id: {"name": str, "keywords": [str], "status": str, "favorite": bool} }
"""
import os, json, subprocess, time, urllib.parse
from notion_client import notion, load_db_ids, tmdb_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def tmdb(path, params=None):
    params = {**(params or {}), 'api_key': TMDB_API_KEY}
    q = '&'.join(f'{k}={urllib.parse.quote(str(v), safe="")}' for k,v in params.items())
    url = f'https://api.themoviedb.org/3{path}?{q}'
    r = subprocess.run(['curl','-s',url], capture_output=True, text=True, timeout=20)
    try: return json.loads(r.stdout)
    except: return None


def list_shows():
    rows, cursor = [], None
    while True:
        body = {'page_size': 100}
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        rows.extend(r.get('results', []))
        if r.get('has_more'):
            cursor = r.get('next_cursor')
        else:
            break
    return rows


def main():
    rows = list_shows()
    out = {}
    total_with_id = sum(1 for r in rows if r['properties'].get('TMDB ID',{}).get('number'))
    print(f'Fetching keywords for {total_with_id} hydrated shows...\n')
    i = 0
    for row in rows:
        p = row['properties']
        tmdb_id = p.get('TMDB ID',{}).get('number')
        if not tmdb_id:
            continue
        i += 1
        name = ''.join(t.get('plain_text','') for t in p.get('Name',{}).get('title',[]))
        status = (p.get('Status',{}).get('select') or {}).get('name')
        favorite = p.get('Fav',{}).get('checkbox', False)

        r = tmdb(f'/tv/{tmdb_id}/keywords')
        if not r:
            print(f'{i}/{total_with_id} ✗ {name} - fetch failed', flush=True)
            continue
        kws = [k['name'].lower() for k in (r.get('results') or [])]
        out[int(tmdb_id)] = {
            'name': name,
            'status': status,
            'favorite': favorite,
            'keywords': kws,
            'notion_id': row['id'],
        }
        marker = '⭐' if favorite else '·'
        print(f'{i}/{total_with_id} {marker} {name} - {len(kws)} kw', flush=True)
        time.sleep(0.05)

    with open(os.path.join(BASE_DIR, 'shows_keywords.json'),'w') as f:
        json.dump(out, f, indent=2)
    print(f'\n✅ Wrote shows_keywords.json ({len(out)} shows)')


if __name__ == '__main__':
    main()
