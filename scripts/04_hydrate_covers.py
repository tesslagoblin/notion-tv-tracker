"""Set Notion page cover on shows that don't have one, using the Poster URL.

Gallery view previews read the page cover, not the Poster property. Shows added
without a cover show blank cards. This backfills.
"""
import os
from notion_client import notion, load_db_ids, api_ok, api_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SHOWS_DS = load_db_ids()['shows']['data_source_id']

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
    fixed = 0
    skipped = 0
    for pg in all_shows():
        if pg.get('cover'): continue
        title = ''.join(t['plain_text'] for t in pg['properties']['Name']['title'])
        poster = pg['properties'].get('Poster', {}).get('url')
        if not poster:
            skipped += 1
            print(f' - {title}: no Poster url, skipped')
            continue
        r = notion('PATCH', f'/pages/{pg["id"]}', {
            'cover': {'type': 'external', 'external': {'url': poster}}
        })
        if not api_ok(r):
            print(f'  ✗ {title}: {api_error(r)}')
            continue
        fixed += 1
        print(f'  ✓ {title}')
    print(f'\n{fixed} covers set, {skipped} skipped (no Poster url).')

if __name__ == '__main__':
    main()
