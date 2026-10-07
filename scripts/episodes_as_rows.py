"""Episode rows with instant progress.

    python3 episodes_as_rows.py "Show Name"
    python3 episodes_as_rows.py --watching

Creates one Episode DB row per episode, related to the show, named
"S01E01 - Title", and ticks Watched up to the show's Current S/E (or Watched
Count if there is no S/E).

Why rows instead of checkboxes in the page body: a to_do block is invisible to
Notion formulas, so body checkboxes only move Progress when a sync script runs.
A related row feeds the Watched Episodes rollup, which the Progress formula
already prefers, so ticking one updates Progress immediately with no script in
the loop at all.

Also clears the old body checkboxes for the show, so there is one source of
truth. Pass --keep-blocks to leave them alone.
"""
import sys, json, subprocess, time, re
from notion_client import notion, load_db_ids, tmdb_key
TMDB_API_KEY = tmdb_key()
_ids = load_db_ids()
SHOWS_DS = _ids['shows']['data_source_id']
EPS_DS = _ids['episodes']['data_source_id']
EPS_DB = _ids['episodes']['database_id']

SE_RE = re.compile(r'S(\d+)\s*E(\d+)', re.I)
MAX_EPS = 400


def tmdb(path):
    r = subprocess.run(['curl', '-s', f'https://api.themoviedb.org/3/{path}?api_key={TMDB_API_KEY}'],
                       capture_output=True, text=True, timeout=25)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def shows(name=None, watching=False):
    body = {'page_size': 100}
    body['filter'] = ({'property': 'Status', 'select': {'equals': 'Watching'}} if watching
                      else {'property': 'Name', 'title': {'equals': name}})
    return notion('POST', f'/data_sources/{SHOWS_DS}/query', body).get('results', [])


def existing_rows(show_id):
    """{(season, episode): page_id} already linked to this show."""
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
                out[(s, e)] = row['id']
        if not r.get('has_more'):
            return out
        cursor = r['next_cursor']


def clear_blocks(page_id):
    """Delete episode to_do blocks and their season headings from the page body."""
    killed, cursor = 0, None
    ids = []
    while True:
        q = '?page_size=100' + (f'&start_cursor={cursor}' if cursor else '')
        r = notion('GET', f'/blocks/{page_id}/children{q}')
        for b in r.get('results', []):
            t = b['type']
            if t == 'to_do':
                ids.append(b['id'])
            elif t in ('heading_2', 'heading_3'):
                txt = ''.join(x['plain_text'] for x in b[t]['rich_text'])
                if txt.startswith('Season ') or 'Episodes' in txt:
                    ids.append(b['id'])
        if not r.get('has_more'):
            break
        cursor = r['next_cursor']
    for bid in ids:
        notion('DELETE', f'/blocks/{bid}')
        killed += 1
        time.sleep(0.12)
    return killed


def run(row, keep_blocks=False):
    p = row['properties']
    name = ''.join(t['plain_text'] for t in p['Name']['title'])
    tid = p['TMDB ID']['number']
    if not tid:
        print(f'  ? {name}: no TMDB ID')
        return
    details = tmdb(f'tv/{tid}')
    if not details:
        print(f'  ! {name}: TMDB lookup failed')
        return
    if (details.get('number_of_episodes') or 0) > MAX_EPS:
        print(f'  - {name}: {details["number_of_episodes"]} episodes, over the {MAX_EPS} cap, skipped')
        return

    se = ''.join(t['plain_text'] for t in p['Current S/E']['rich_text'])
    m = SE_RE.search(se)
    mark = (int(m.group(1)), int(m.group(2))) if m else None
    wc = p['Watched Count']['number'] or 0

    have = existing_rows(row['id'])
    created = ticked = 0
    running = 0

    for s in details.get('seasons', []):
        sn = s['season_number']
        if sn == 0:
            continue
        season = tmdb(f'tv/{tid}/season/{sn}')
        for ep in (season or {}).get('episodes', []) or []:
            en = ep['episode_number']
            running += 1
            watched = (sn, en) <= mark if mark else running <= wc
            label = f'S{sn:02d}E{en:02d}'
            if ep.get('name'):
                label += f' - {ep["name"]}'
            props = {
                'Name': {'title': [{'text': {'content': label}}]},
                'Season': {'number': sn},
                'Episode': {'number': en},
                'Watched': {'checkbox': watched},
                'Related to Shows (Episodes)': {'relation': [{'id': row['id']}]},
            }
            if ep.get('air_date'):
                props['Air Date'] = {'date': {'start': ep['air_date']}}
            if ep.get('runtime'):
                props['Runtime (min)'] = {'number': ep['runtime']}
            if ep.get('id'):
                props['TMDB ID'] = {'number': ep['id']}

            if (sn, en) in have:
                notion('PATCH', f'/pages/{have[(sn, en)]}', {'properties': {
                    'Name': props['Name'], 'Watched': props['Watched']}})
            else:
                notion('POST', '/pages', {'parent': {'type': 'database_id', 'database_id': EPS_DB},
                                          'properties': props})
                created += 1
            ticked += 1 if watched else 0
            time.sleep(0.12)
        time.sleep(0.15)

    removed = 0 if keep_blocks else clear_blocks(row['id'])
    print(f'  + {name}: {running} episodes ({created} new), {ticked} ticked, {removed} old blocks cleared')


def main():
    args = sys.argv[1:]
    keep = '--keep-blocks' in args
    args = [a for a in args if a != '--keep-blocks']
    watching = '--watching' in args
    args = [a for a in args if a != '--watching']
    rows = shows(args[0] if args else None, watching=watching)
    if not rows:
        print('No matching show.')
        sys.exit(1)
    print(f'{len(rows)} show(s)\n')
    for r in rows:
        run(r, keep_blocks=keep)


if __name__ == '__main__':
    main()
