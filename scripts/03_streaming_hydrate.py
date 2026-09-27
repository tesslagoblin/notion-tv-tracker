"""Populate Streaming property on each Show from TMDB watch providers (US region).

- flatrate → actual subscription content (what her plan includes)
- free/ads tiers skipped: these are usually Freevee/ad-supported content that lives
  behind the Amazon Prime interface but isn't part of the Prime subscription proper.
  Including them caused false positives (Joanna Lumley shows showing as "available"
  on Prime when they were only on Freevee).
- rent/buy is skipped
- Overwrites existing Streaming value with fresh data

Usage: python3 12_streaming_hydrate.py [--limit N]
"""
import os, json, sys, subprocess, urllib.parse, time
from notion_client import notion, tmdb_key

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()


def all_shows():
    cursor = None
    while True:
        body = {'page_size': 100}
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        for pg in r.get('results', []):
            yield pg
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')


def main():
    limit = None
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])

    updated, empty, skipped = 0, 0, 0
    for i, pg in enumerate(all_shows()):
        if limit and i >= limit: break
        title = ''.join(t['plain_text'] for t in pg['properties']['Name']['title'])
        tmdb_id = pg['properties'].get('TMDB ID', {}).get('number')
        if not tmdb_id:
            skipped += 1
            continue

        provs = tmdb_providers(tmdb_id)
        time.sleep(0.05)  # gentle TMDB throttle

        payload = {'properties': {'Streaming': {'multi_select': [{'name': p} for p in provs]}}}
        notion('PATCH', f'/pages/{pg["id"]}', payload)
        if provs:
            updated += 1
            if i % 20 == 0:
                print(f'  [{i}] {title}: {", ".join(provs[:3])}{"..." if len(provs) > 3 else ""}')
        else:
            empty += 1

    print(f'\nDone: {updated} updated, {empty} no US providers, {skipped} skipped (no TMDB ID)')

if __name__ == '__main__':
    main()
