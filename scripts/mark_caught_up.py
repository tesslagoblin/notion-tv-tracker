"""Mark a list of shows as caught-up: Watched Count = aired episodes.

For each show:
- Fetch TMDB /tv/{id} to get last_episode_to_air + number_of_episodes
- Set Watched Count = aired episodes (last_episode_to_air's absolute number,
  or number_of_episodes if the show has ended)
- Ended shows → Status = Finished
- Returning shows → Status = Returning + Current S/E = last aired episode label
- Check off all to_do blocks in page body up to & including last aired episode

Usage: edit TARGETS below, then python3 mark_caught_up.py
"""
import os, json, sys, subprocess, time, re
from notion_client import notion, load_db_ids, tmdb_key, api_ok, api_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# The shows to mark as caught up, spelled exactly as the Name in Notion.
# Example:
#   TARGETS = [
#       'Gilmore Girls',
#       'Parks and Recreation',
#   ]
TARGETS = []

# Episode labels are written as S03E10 (zero padded) in Current S/E and in the
# page-body checkboxes ("S03E10 - Title"). Also accepts S3E10 and s3e10.
SE_RE = re.compile(r'S(\d{1,3})\s*E(\d{1,4})', re.IGNORECASE)

if __name__ == '__main__' and not TARGETS:
    sys.exit('TARGETS is empty. Open mark_caught_up.py, list the show names you want\n'
             'marked as caught up in TARGETS near the top, then run it again.')

TMDB_API_KEY = tmdb_key()

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def tmdb(path):
    r = subprocess.run(['curl', '-s',
        f'https://api.themoviedb.org/3/{path}?api_key={TMDB_API_KEY}'],
        capture_output=True, text=True, timeout=20)
    try: return json.loads(r.stdout)
    except: return None


def find_show(name):
    r = notion('POST', f'/data_sources/{SHOWS_DS}/query',
        {'filter': {'property': 'Name', 'title': {'equals': name}}, 'page_size': 2})
    return (r.get('results') or [None])[0]


def aired_episode_count(tmdb_id):
    """Return (aired_count, last_se_label) where last_se_label is 'SxxEyy'."""
    d = tmdb(f'tv/{tmdb_id}')
    if not d: return None, None
    status = d.get('status', '')
    last_ep = d.get('last_episode_to_air') or {}
    total = d.get('number_of_episodes') or 0

    if status == 'Ended':
        # All released - walk seasons to get last SxxEyy
        seasons = [s for s in d.get('seasons', []) if s.get('season_number', 0) > 0]
        if seasons:
            last = seasons[-1]
            se = f"S{last['season_number']:02d}E{last.get('episode_count', 0):02d}"
        else:
            se = None
        return total, se

    # Returning - count aired only
    if last_ep:
        sn = last_ep.get('season_number')
        en = last_ep.get('episode_number')
        se = f"S{sn:02d}E{en:02d}" if sn and en else None
        # Sum all episodes in prior seasons + episode_number in current season
        aired = 0
        for s in d.get('seasons', []):
            if s.get('season_number', 0) < 1: continue
            if s['season_number'] < sn:
                aired += s.get('episode_count', 0)
            elif s['season_number'] == sn:
                aired += en
                break
        return aired, se
    return total, None


def get_todos(page_id):
    out = []
    cursor = None
    while True:
        path = f'/blocks/{page_id}/children?page_size=100'
        if cursor: path += f'&start_cursor={cursor}'
        r = notion('GET', path, None)
        for b in r.get('results', []):
            if b['type'] != 'to_do': continue
            text = ''.join(t.get('plain_text', '') for t in b['to_do'].get('rich_text', []))
            m = SE_RE.search(text)
            se = (int(m.group(1)), int(m.group(2))) if m else None
            out.append((b['id'], se, b['to_do'].get('checked', False)))
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')
    return out


def main():
    for name in TARGETS:
        pg = find_show(name)
        if not pg:
            print(f'  ? {name}: not in Notion')
            continue
        tmdb_id = pg['properties'].get('TMDB ID', {}).get('number')
        if not tmdb_id:
            print(f'  ? {name}: no TMDB ID')
            continue

        aired, last_se = aired_episode_count(int(tmdb_id))
        time.sleep(0.1)
        if not aired:
            print(f'  ! {name}: could not determine aired count')
            continue

        ret_status = (pg['properties'].get('Return Status', {}).get('select') or {}).get('name')
        new_status = 'Finished' if ret_status == 'Ended' else 'Returning'

        props = {
            'Watched Count': {'number': aired},
            'Status': {'select': {'name': new_status}},
        }
        if new_status == 'Returning' and last_se:
            props['Current S/E'] = {'rich_text': [{'type': 'text', 'text': {'content': last_se}}]}

        r = notion('PATCH', f'/pages/{pg["id"]}', {'properties': props})
        if not api_ok(r):
            print(f'  ✗ {name}: update failed ({api_error(r)}), skipped')
            continue

        # Check off any to_do blocks up to the aired episode
        checked_extra = 0
        todos = get_todos(pg['id'])
        if todos and last_se:
            m = SE_RE.search(last_se)
            tgt = (int(m.group(1)), int(m.group(2)))
            for bid, se, was_checked in todos:
                if se and se <= tgt and not was_checked:
                    if api_ok(notion('PATCH', f'/blocks/{bid}', {'to_do': {'checked': True}})):
                        checked_extra += 1

        print(f'  ✓ {name}: {new_status}, watched={aired}, current={last_se}, todos checked={checked_extra}')


if __name__ == '__main__':
    main()
