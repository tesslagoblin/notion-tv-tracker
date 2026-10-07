"""Catch Current S/E, Next Episode and the episode rows up to Watched Count.

    python3 sync_from_count.py            # only shows that have drifted
    python3 sync_from_count.py --all      # every Watching/Paused show

Watched Count is the source of truth, because that is what the +1 button in
Notion writes. Tapping the button moves Progress instantly but leaves the
labels behind, so this fills the gap: it reads the count, works out which
episode that actually is from TMDB, and rewrites Current S/E, Next Episode and
the Watched ticks on the episode rows.

Cheap by default: it only touches TMDB for shows where the count and the ticked
rows disagree, so a run with nothing to do costs one Notion query.
"""
import sys, json, subprocess, time
from notion_client import notion, load_db_ids, tmdb_key

TMDB_API_KEY = tmdb_key()
_ids = load_db_ids()
SHOWS_DS = _ids['shows']['data_source_id']
EPS_DS = _ids['episodes']['data_source_id']


def tmdb(path):
    r = subprocess.run(['curl', '-s', f'https://api.themoviedb.org/3/{path}?api_key={TMDB_API_KEY}'],
                       capture_output=True, text=True, timeout=25)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def episode_order(tmdb_id):
    d = tmdb(f'tv/{tmdb_id}')
    out = []
    for s in (d or {}).get('seasons', []):
        if s['season_number'] == 0:
            continue
        season = tmdb(f'tv/{tmdb_id}/season/{s["season_number"]}')
        for ep in (season or {}).get('episodes', []) or []:
            out.append((s['season_number'], ep['episode_number'], ep.get('name') or ''))
        time.sleep(0.15)
    return out


def rows_for(show_id):
    out, cursor = {}, None
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
                out[(s, e)] = (row['id'], p['Watched']['checkbox'])
        if not r.get('has_more'):
            return out
        cursor = r['next_cursor']


def main():
    force = '--all' in sys.argv
    body = {'page_size': 100, 'filter': {'or': [
        {'property': 'Status', 'select': {'equals': 'Watching'}},
        {'property': 'Status', 'select': {'equals': 'Paused'}},
    ]}}
    touched = 0
    for row in notion('POST', f'/data_sources/{SHOWS_DS}/query', body).get('results', []):
        p = row['properties']
        name = ''.join(t['plain_text'] for t in p['Name']['title'])
        wc = p['Watched Count']['number']
        roll = p['Watched Episodes']['rollup'].get('number')
        tid = p['TMDB ID']['number']
        if wc is None or not tid:
            continue
        if not force and roll == wc:
            continue  # nothing moved since last time

        order = episode_order(tid)
        if not order:
            print(f'  ! {name}: no TMDB episode list')
            continue
        target = max(0, min(wc, len(order)))

        rows = rows_for(row['id'])
        fixed = 0
        for i, (s, e, _t) in enumerate(order, 1):
            want = i <= target
            if (s, e) in rows:
                pid, cur = rows[(s, e)]
                if cur != want:
                    notion('PATCH', f'/pages/{pid}', {'properties': {'Watched': {'checkbox': want}}})
                    fixed += 1
                    time.sleep(0.12)

        props = {}
        if target > 0:
            s, e, _ = order[target - 1]
            props['Current S/E'] = {'rich_text': [{'text': {'content': f'S{s:02d}E{e:02d}'}}]}
        if target < len(order):
            ns, ne, nt = order[target]
            nxt = f'S{ns:02d}E{ne:02d}' + (f' - {nt}' if nt else '')
            props['Next Episode'] = {'rich_text': [{'text': {'content': nxt}}]}
        else:
            props['Next Episode'] = {'rich_text': []}
            nxt = ''
        notion('PATCH', f"/pages/{row['id']}", {'properties': props})
        touched += 1
        print(f'  = {name}: {target}/{len(order)}, {fixed} rows re-ticked'
              + (f', next {nxt[:32]}' if nxt else ', caught up'))

    if touched == 0:
        print('nothing drifted')


if __name__ == '__main__':
    main()
