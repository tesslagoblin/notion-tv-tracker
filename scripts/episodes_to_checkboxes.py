"""Convert Episode DB rows to page-body to_do checkboxes on each show's page.
Groups by season with heading_2 "Season N", then to_do 'S{N}E{M} - Title' per episode.
Deletes the Episode DB rows after conversion.
"""
import os
from notion_client import notion, load_db_ids

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
    """Return list of episode rows for this show, sorted by (season, episode)."""
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
    eps = get_episodes_for_show(show_page_id)
    if not eps:
        print(f'  {show_name}: no episodes to convert')
        return

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

    # Append to show page in chunks of 100
    for i in range(0, len(blocks), 100):
        chunk = blocks[i:i+100]
        notion('PATCH', f'/blocks/{show_page_id}/children', {'children': chunk})

    # Delete DB rows
    for row in eps:
        try:
            notion('DELETE', f'/blocks/{row["id"]}', {})
        except Exception:
            pass

    print(f'  ✓ {show_name}: {len(eps)} eps → checkboxes, DB rows removed')


def main():
    # Get all Watching shows
    r = notion('POST', f'/data_sources/{SHOWS_DS}/query', {
        'filter': {'property': 'Status', 'select': {'equals': 'Watching'}},
        'page_size': 100,
    })
    shows = r.get('results', [])
    print(f'Processing {len(shows)} Watching shows...\n')
    for row in shows:
        name = ''.join(x.get('plain_text', '') for x in row['properties']['Name']['title'])
        process_show(row['id'], name)
    print('\nDone.')


if __name__ == '__main__':
    main()
