"""Keep a runway of unwatched episode rows ahead of where you are.

    python3 extend_episodes.py              # top up anything running low
    python3 extend_episodes.py --buffer 100

Very long shows are filled a few seasons at a time rather than all at once,
because one row per episode means one API call per episode. This tops them up:
for every Watching show, if fewer than BUFFER unwatched rows remain ahead of
Watched Count and the show has more episodes on TMDB, it fills the next season.

That matters because the Up Next formula indexes the sorted episode rows at
Watched Count. Run out of rows and Up Next goes blank. This keeps that from
happening without anyone having to notice.
"""
import sys, json, subprocess, time
from notion_client import notion, load_db_ids, tmdb_key

TMDB_API_KEY = tmdb_key()
_ids = load_db_ids()
SHOWS_DS = _ids['shows']['data_source_id']
EPS_DS = _ids['episodes']['data_source_id']
EPS_DB = _ids['episodes']['database_id']

DEFAULT_BUFFER = 75
MAX_FILL_PER_RUN = 150   # keep a single run short and polite to the API


def tmdb(path):
    r = subprocess.run(['curl', '-s', f'https://api.themoviedb.org/3/{path}?api_key={TMDB_API_KEY}'],
                       capture_output=True, text=True, timeout=25)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def existing(show_id):
    """{(season, episode)} already present, and the highest season filled."""
    have, cursor = set(), None
    while True:
        body = {'page_size': 100, 'filter': {'property': 'Related to Shows (Episodes)',
                                             'relation': {'contains': show_id}}}
        if cursor:
            body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{EPS_DS}/query', body)
        for row in r.get('results', []):
            p = row['properties']
            s, e = p.get('Season', {}).get('number'), p.get('Episode', {}).get('number')
            if s is not None and e is not None:
                have.add((s, e))
        if not r.get('has_more'):
            return have
        cursor = r['next_cursor']


def main():
    buffer = DEFAULT_BUFFER
    if '--buffer' in sys.argv:
        buffer = int(sys.argv[sys.argv.index('--buffer') + 1])

    body = {'page_size': 100, 'filter': {'property': 'Status', 'select': {'equals': 'Watching'}}}
    for row in notion('POST', f'/data_sources/{SHOWS_DS}/query', body).get('results', []):
        p = row['properties']
        name = ''.join(t['plain_text'] for t in p['Name']['title'])
        tid = p['TMDB ID']['number']
        total = p['Total Episodes']['number'] or 0
        wc = p['Watched Count']['number'] or 0
        if not tid:
            continue

        have = existing(row['id'])
        if not have:
            continue  # never filled at all, that is episodes_as_rows.py's job
        runway = len(have) - wc
        if len(have) >= total or runway >= buffer:
            continue

        details = tmdb(f'tv/{tid}')
        if not details:
            print(f'  ! {name}: TMDB lookup failed')
            continue

        added = 0
        for s in details.get('seasons', []):
            sn = s['season_number']
            if sn == 0 or added >= MAX_FILL_PER_RUN:
                continue
            missing = [e for e in range(1, (s.get('episode_count') or 0) + 1) if (sn, e) not in have]
            if not missing:
                continue
            season = tmdb(f'tv/{tid}/season/{sn}')
            for ep in (season or {}).get('episodes', []) or []:
                en = ep['episode_number']
                if (sn, en) in have or added >= MAX_FILL_PER_RUN:
                    continue
                label = f'S{sn:02d}E{en:02d}'
                if ep.get('name'):
                    label += f' - {ep["name"]}'
                props = {
                    'Name': {'title': [{'text': {'content': label}}]},
                    'Season': {'number': sn},
                    'Episode': {'number': en},
                    'Watched': {'checkbox': False},
                    'Related to Shows (Episodes)': {'relation': [{'id': row['id']}]},
                }
                if ep.get('air_date'):
                    props['Air Date'] = {'date': {'start': ep['air_date']}}
                notion('POST', '/pages', {'parent': {'type': 'database_id', 'database_id': EPS_DB},
                                          'properties': props})
                added += 1
                time.sleep(0.12)
            time.sleep(0.15)
        if added:
            print(f'  + {name}: runway was {runway}, added {added} rows '
                  f'({len(have) + added}/{total} banked)')


if __name__ == '__main__':
    main()
