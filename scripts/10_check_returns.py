"""Refresh Return Status + Next Air Date on all non-Dropped shows.

For each show:
- Fetches TMDB /tv/{id}
- Writes: Return Status (Returning Series / Ended / In Production / Pilot / Planned) - Canceled folds into Ended
- Writes: Next Air Date (from next_episode_to_air.air_date if present, else None)
- Writes: Total Episodes (refreshed from TMDB, in case it grew)

Also flags upcoming returns for shows you have caught up on.

Usage: python3 10_check_returns.py [--limit N] [--verbose]
"""
import os, json, sys, subprocess, time
from datetime import date
from notion_client import notion, load_db_ids, tmdb_key, api_ok, api_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def tmdb(tmdb_id):
    r = subprocess.run(['curl', '-s',
        f'https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}'],
        capture_output=True, text=True, timeout=15)
    try: return json.loads(r.stdout)
    except: return None


def query_shows():
    """All shows except Dropped."""
    cursor = None
    while True:
        body = {'filter': {'and': [
            {'property': 'Status', 'select': {'does_not_equal': 'Dropped'}}
        ]}, 'page_size': 100}
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        for pg in r.get('results', []):
            yield pg
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')


def main():
    limit = None
    verbose = '--verbose' in sys.argv
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])

    upcoming = []
    updated = 0
    today = date.today().isoformat()

    for i, pg in enumerate(query_shows()):
        if limit and i >= limit: break
        title = ''.join(t['plain_text'] for t in pg['properties']['Name']['title'])
        tmdb_id = pg['properties'].get('TMDB ID', {}).get('number')
        if not tmdb_id: continue
        status_now = pg['properties'].get('Status', {}).get('select', {})
        status_now = status_now['name'] if status_now else None
        watched_count = pg['properties'].get('Watched Count', {}).get('number') or 0
        total_ep = pg['properties'].get('Total Episodes', {}).get('number') or 0

        d = tmdb(tmdb_id)
        time.sleep(0.05)
        # TMDB error JSON (bad key, rate limit) has no id. Treating it as data
        # would blank out Next Air Date, so skip the show instead.
        if not d or not d.get('id'):
            print(f'  ✗ {title}: TMDB lookup failed, skipped')
            continue

        tmdb_status = d.get('status', '')
        if tmdb_status == 'Canceled':
            tmdb_status = 'Ended'  # collapse Canceled into Ended
        next_ep = d.get('next_episode_to_air') or {}
        next_date = next_ep.get('air_date') if next_ep else None
        new_total = d.get('number_of_episodes')

        props = {
            'Return Status': {'select': {'name': tmdb_status}} if tmdb_status else None,
            'Next Air Date': {'date': {'start': next_date}} if next_date else {'date': None},
        }
        if new_total and new_total != total_ep:
            props['Total Episodes'] = {'number': new_total}

        props = {k: v for k, v in props.items() if v is not None or k == 'Next Air Date'}
        r = notion('PATCH', f'/pages/{pg["id"]}', {'properties': props})
        if not api_ok(r):
            print(f'  ✗ {title}: Notion update failed ({api_error(r)})')
            continue
        updated += 1
        if verbose:
            print(f'  {title}: status={tmdb_status}, next={next_date}, eps={total_ep}→{new_total}')

        # Flag upcoming returns for shows you are caught up on
        if next_date and next_date >= today and status_now in ('Watching', 'Returning', 'Paused', 'Finished'):
            caught_up = watched_count >= total_ep and total_ep > 0
            upcoming.append((next_date, title, next_ep, caught_up, status_now))

    print(f'\n{updated} shows refreshed.')
    if upcoming:
        upcoming.sort()
        print(f'\n=== Upcoming returns ({len(upcoming)}) ===')
        for d_, title, ep, caught, s in upcoming[:30]:
            se = f"S{ep.get('season_number'):02d}E{ep.get('episode_number'):02d}"
            marker = '★' if caught else ' '
            print(f'  {marker} {d_}  {title}  {se}  [{s}]')


if __name__ == '__main__':
    main()
