"""Sync checked to_do blocks per Show → Watched Count property, and auto-transition
Watching → Returning/Finished when caught up.

For each show with Status in {Watching, Paused}:
- Walks page-body to_do blocks, counts how many are checked
- Writes that number to Watched Count (only if there ARE to_do blocks - never
  clobber a manually-set Watched Count on shows with no to_do hydration)
- Writes the first unchecked label to Next Episode
- If Watched Count >= Total Episodes: flip to Finished (if Return Status is Ended)
  or Returning (else - still coming back)

Idempotent - safe to run repeatedly.
"""
import os
from notion_client import notion, load_db_ids, api_ok, api_error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SHOWS_DS = load_db_ids()['shows']['data_source_id']

def scan_todos(page_id):
    """Returns (todo_count, checked_count, next_unchecked_label)."""
    total = 0
    checked = 0
    next_label = ''
    cursor = None
    while True:
        path = f'/blocks/{page_id}/children?page_size=100'
        if cursor: path += f'&start_cursor={cursor}'
        r = notion('GET', path, None)
        for b in r.get('results', []):
            if b['type'] != 'to_do': continue
            total += 1
            if b['to_do'].get('checked'):
                checked += 1
            elif not next_label:
                text = ''.join(t.get('plain_text', '') for t in b['to_do'].get('rich_text', []))
                next_label = text
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')
    return total, checked, next_label

def next_status(current, watched, total_ep, return_status):
    """Auto-transition rule: caught-up Watching → Returning or Finished."""
    if current != 'Watching': return None
    if not total_ep or watched < total_ep: return None
    if return_status == 'Ended':
        return 'Finished'
    return 'Returning'

def active_shows():
    """Every Watching or Paused show, paginated."""
    cursor = None
    while True:
        q = {'filter': {'or': [
            {'property': 'Status', 'select': {'equals': 'Watching'}},
            {'property': 'Status', 'select': {'equals': 'Paused'}},
        ]}, 'page_size': 100}
        if cursor: q['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', q)
        yield from r.get('results', [])
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')

def main():
    updated = 0
    for pg in active_shows():
        title = ''.join(t['plain_text'] for t in pg['properties']['Name']['title'])
        cur_count = pg['properties'].get('Watched Count', {}).get('number') or 0
        cur_next = ''.join(t.get('plain_text', '') for t in pg['properties'].get('Next Episode', {}).get('rich_text', []))
        cur_status = (pg['properties'].get('Status', {}).get('select') or {}).get('name')
        total_ep = pg['properties'].get('Total Episodes', {}).get('number') or 0
        ret = (pg['properties'].get('Return Status', {}).get('select') or {}).get('name')
        todo_total, checked, next_label = scan_todos(pg['id'])
        props = {}
        # Only touch Watched Count if to_do blocks exist (otherwise a manual value
        # from mark_caught_up.py or elsewhere is the source of truth)
        if todo_total > 0 and checked != cur_count:
            props['Watched Count'] = {'number': checked}
            cur_count = checked
        if next_label and next_label != cur_next:
            props['Next Episode'] = {'rich_text': [{'type': 'text', 'text': {'content': next_label}}]}
        # Auto-transition Watching → Returning/Finished on caught-up
        new_st = next_status(cur_status, cur_count, total_ep, ret)
        if new_st:
            props['Status'] = {'select': {'name': new_st}}
        if props:
            r = notion('PATCH', f'/pages/{pg["id"]}', {'properties': props})
            if not api_ok(r):
                print(f'  ✗ {title}: update failed ({api_error(r)})')
                continue
            changes = []
            if 'Watched Count' in props: changes.append(f'count → {checked}')
            if 'Next Episode' in props: changes.append(f'next → {next_label}')
            if 'Status' in props: changes.append(f'status → {new_st}')
            print(f'  {title}: {", ".join(changes)}')
            updated += 1
    print(f'\n{updated} shows updated.')

if __name__ == '__main__':
    main()
