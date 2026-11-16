"""Fill the Synopsis field from TMDB so you can tell what a show is while scanning.

    python3 hydrate_synopsis.py            # only shows missing one
    python3 hydrate_synopsis.py --refresh  # rewrite them all

Kept separate from Notes, which is for your own remarks about a show.
"""
import sys, json, subprocess, time
from notion_client import notion, load_db_ids, tmdb_key

TMDB_API_KEY = tmdb_key()
SHOWS_DS = load_db_ids()['shows']['data_source_id']
LIMIT = 1800  # Notion rich_text caps at 2000


def tmdb(tid):
    r = subprocess.run(['curl', '-s', f'https://api.themoviedb.org/3/tv/{tid}?api_key={TMDB_API_KEY}'],
                       capture_output=True, text=True, timeout=20)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def main():
    refresh = '--refresh' in sys.argv
    cursor, done, skipped = None, 0, 0
    while True:
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        for row in r.get('results', []):
            p = row['properties']
            tid = p['TMDB ID']['number']
            have = ''.join(t['plain_text'] for t in p.get('Synopsis', {}).get('rich_text', []))
            if not tid or (have and not refresh):
                skipped += 1
                continue
            d = tmdb(tid)
            text = (d or {}).get('overview') or ''
            if not text:
                skipped += 1
                continue
            notion('PATCH', f"/pages/{row['id']}", {'properties': {
                'Synopsis': {'rich_text': [{'text': {'content': text[:LIMIT]}}]}}})
            done += 1
            if done % 50 == 0:
                print(f'  ...{done} filled', flush=True)
            time.sleep(0.12)
        if not r.get('has_more'):
            break
        cursor = r['next_cursor']
    print(f'done: {done} synopses written, {skipped} skipped')


if __name__ == '__main__':
    main()
