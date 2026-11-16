"""Move shows between Watching, Returning and Finished on their own.

    python3 auto_status.py            # apply
    python3 auto_status.py --dry-run  # just report

The rule, based on episodes that have actually AIRED (not the TMDB total,
which counts announced-but-unaired episodes):

  Watching, caught up, show ended        -> Finished
  Watching, caught up, show continuing   -> Returning
  Returning, new episodes have aired     -> Watching

So a show you are current on drops out of your watching view by itself, and
comes back the moment there is something new to watch. Watched Count is never
touched, so nothing is lost either direction.
"""
import sys, json, subprocess, time
from notion_client import notion, load_db_ids, tmdb_key

TMDB_API_KEY = tmdb_key()
SHOWS_DS = load_db_ids()['shows']['data_source_id']

ENDED = {'Ended', 'Canceled'}


def tmdb(path):
    r = subprocess.run(['curl', '-s', f'https://api.themoviedb.org/3/{path}?api_key={TMDB_API_KEY}'],
                       capture_output=True, text=True, timeout=25)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def aired_count(details):
    """Episodes actually broadcast so far."""
    last = details.get('last_episode_to_air') or {}
    if not last:
        return 0
    ls, le = last.get('season_number'), last.get('episode_number')
    n = 0
    for s in details.get('seasons', []):
        sn = s['season_number']
        if sn == 0:
            continue
        if sn < ls:
            n += s.get('episode_count') or 0
        elif sn == ls:
            n += le or 0
    return n


def main():
    dry = '--dry-run' in sys.argv
    body = {'page_size': 100, 'filter': {'or': [
        {'property': 'Status', 'select': {'equals': 'Watching'}},
        {'property': 'Status', 'select': {'equals': 'Returning'}},
    ]}}
    changed = 0
    for row in notion('POST', f'/data_sources/{SHOWS_DS}/query', body).get('results', []):
        p = row['properties']
        name = ''.join(t['plain_text'] for t in p['Name']['title'])
        status = (p['Status']['select'] or {}).get('name')
        wc = p['Watched Count']['number']
        tid = p['TMDB ID']['number']
        if not tid or wc is None:
            continue

        d = tmdb(f'tv/{tid}')
        if not d:
            print(f'  ! {name}: TMDB lookup failed')
            continue
        aired = aired_count(d)
        ended = d.get('status') in ENDED
        if aired == 0:
            continue

        new = None
        why = ''
        if status == 'Watching' and wc >= aired:
            new = 'Finished' if ended else 'Returning'
            why = f'caught up at {wc}/{aired} aired, show {"ended" if ended else "continuing"}'
        elif status == 'Returning' and wc < aired:
            new = 'Watching'
            why = f'{aired - wc} new episode(s) aired since you caught up'

        if not new:
            continue
        changed += 1
        print(f'  {"would set" if dry else "set"} {name}: {status} -> {new}  ({why})')
        if not dry:
            props = {'Status': {'select': {'name': new}}}
            nxt = d.get('next_episode_to_air') or {}
            if nxt.get('air_date'):
                props['Next Air Date'] = {'date': {'start': nxt['air_date']}}
            notion('PATCH', f"/pages/{row['id']}", {'properties': props})
            time.sleep(0.2)

    if changed == 0:
        print('no status changes')


if __name__ == '__main__':
    main()
