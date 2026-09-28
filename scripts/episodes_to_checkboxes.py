"""Convert Episode DB rows to page-body to_do checkboxes on each show's page.
Groups by season with heading_2 "Season N", then to_do 'S{N}E{M} - Title' per episode.
Deletes the Episode DB rows after conversion, but only for a show whose
checkboxes were confirmed written. If any append fails, that show's rows stay put.
"""
import os
from notion_client import notion, load_db_ids, api_ok, api_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ids = load_db_ids()
EPS_DS = ids['episodes']['data_source_id']
SHOWS_DS = ids['shows']['data_source_id']


def rt(text):
    return [{'type': 'text', 'text': {'content': text}}]

def h2(text):
    return {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': rt(text)}}

def todo(text, checked=False):
    return {'object': 'block', 'type': 'to_do',
            'to_do': {'rich_text': rt(text), 'checked': checked}}


def get_episodes_for_show(show_page_id):
    """Return list of episode rows for this show, sorted by (season, episode).
    None if the query failed."""
    eps = []
    cursor = None
    while True:
        body = {
            'filter': {'property': 'Related to Shows (Episodes)',
                       'relation': {'contains': show_page_id}},
            'page_size': 100
        }
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{EPS_DS}/query', body)
        if not api_ok(r):
            return None  # a half-read show would get half converted, so bail
        eps.extend(r.get('results', []))
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')

    def sort_key(row):
        p = row['properties']
        return (p.get('Season', {}).get('number') or 0,
                p.get('Episode', {}).get('number') or 0)
    eps.sort(key=sort_key)
    return eps


def process_show(show_page_id, show_name):
    """Returns False if the show failed and its Episode rows were kept."""
    eps = get_episodes_for_show(show_page_id)
    if eps is None:
        print(f'  ✗ {show_name}: could not read its Episode rows, skipped')
        return False
    if not eps:
        print(f'  {show_name}: no episodes to convert')
        return True

    # Build blocks grouped by season
    blocks = [h2('📺 Episodes')]
    current_season = None
    for row in eps:
        props = row['properties']
        s = props.get('Season', {}).get('number')
        e = props.get('Episode', {}).get('number')
        title = ''.join(x.get('plain_text', '') for x in props.get('Name', {}).get('title', []))
        watched = props.get('Watched', {}).get('checkbox', False)
        if s != current_season:
            blocks.append({'object': 'block', 'type': 'heading_3',
                           'heading_3': {'rich_text': rt(f'Season {s}')}})
            current_season = s
        label = f'S{s:02d}E{e:02d} - {title}' if title else f'S{s:02d}E{e:02d}'
        blocks.append(todo(label, checked=watched))

    # Append to show page in chunks of 100. notion() does not raise on a failed
    # call, it hands back Notion's error JSON, so check every response before
    # touching the Episode rows. No confirmed append, no delete.
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        r = notion('PATCH', f'/blocks/{show_page_id}/children', {'children': chunk})
        if not api_ok(r) or not r.get('results'):
            print(f'  ✗ {show_name}: appending checkboxes failed ({api_error(r)})')
            if i > 0:
                print(f'    {i} of {len(blocks)} blocks did get written. Clear them off the '
                      f'page before re-running or you will get duplicates.')
            print('    Episode rows NOT deleted. Skipping this show.')
            return False

    # Delete DB rows, now that the checkboxes are safely on the page
    failed = 0
    for row in eps:
        r = notion('DELETE', f'/blocks/{row["id"]}', {})
        if not api_ok(r):
            failed += 1
    if failed:
        print(f'  ! {show_name}: {len(eps)} eps → checkboxes, but {failed} DB rows '
              f'could not be removed. Delete those by hand, re-running would add '
              f'the checkboxes a second time.')
    else:
        print(f'  ✓ {show_name}: {len(eps)} eps → checkboxes, DB rows removed')
    return True


def watching_shows():
    """Every Watching show, paginated (a big library has more than 100)."""
    rows, cursor = [], None
    while True:
        body = {'filter': {'property': 'Status', 'select': {'equals': 'Watching'}},
                'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        if not api_ok(r):
            raise SystemExit(f'Could not query Watching shows: {api_error(r)}')
        rows.extend(r.get('results', []))
        if not r.get('has_more'):
            break
        cursor = r.get('next_cursor')
    return rows


def main():
    shows = watching_shows()
    print(f'Processing {len(shows)} Watching shows...\n')
    failed = []
    for row in shows:
        name = ''.join(x.get('plain_text', '') for x in row['properties']['Name']['title'])
        if process_show(row['id'], name) is False:
            failed.append(name)
    if failed:
        print(f'\n{len(failed)} show(s) failed and kept their Episode rows: {", ".join(failed)}')
    print('\nDone.')


if __name__ == '__main__':
    main()
