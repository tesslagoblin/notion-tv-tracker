"""Collapse the Streaming list down to one entry per actual service.

    python3 collapse_streaming.py --dry-run
    python3 collapse_streaming.py

TMDB returns every reseller separately, so one show ends up tagged
"Paramount+", "Paramount+ Amazon Channel" and "Paramount Plus Apple TV channel"
when all three mean the same subscription. This folds the variants into the
base brand, on existing rows and from here on.
"""
import sys, time
from notion_client import notion, load_db_ids

SHOWS_DS = load_db_ids()['shows']['data_source_id']

# variant -> canonical
COLLAPSE = {
    'Netflix Standard with Ads': 'Netflix', 'Netflix Kids': 'Netflix', 'Netflix basic with Ads': 'Netflix',
    'Amazon Prime Video with Ads': 'Amazon Prime Video', 'Amazon Prime Video Free with Ads': 'Amazon Prime Video',
    'HBO Max': 'Max', 'HBO Max Amazon Channel': 'Max',
    'Hulu (ads)': 'Hulu',
    'Disney Plus': 'Disney+', 'DisneyNOW': 'Disney+',
    'Peacock Premium': 'Peacock', 'Peacock Premium Plus': 'Peacock',
    'Paramount+ Amazon Channel': 'Paramount+', 'Paramount Plus Apple TV channel': 'Paramount+',
    'Paramount Plus Apple TV Channel ': 'Paramount+', 'Paramount+ Roku Premium Channel': 'Paramount+',
    'Paramount Plus Premium': 'Paramount+', 'Paramount Plus Essential': 'Paramount+',
    'Paramount+ with Showtime': 'Paramount+',
    'Britbox Apple TV channel': 'BritBox', 'Britbox Apple TV Channel ': 'BritBox',
    'BritBox Amazon Channel': 'BritBox',
    'AMC+ Amazon Channel': 'AMC+', 'AMC Plus Apple TV channel': 'AMC+',
    'AMC Plus Apple TV Channel ': 'AMC+', 'AMC+ Roku Premium Channel': 'AMC+',
    'Starz Amazon Channel': 'STARZ', 'Starz Apple TV Channel': 'STARZ',
    'Starz Roku Premium Channel': 'STARZ',
    'Shudder Amazon Channel': 'Shudder', 'Shudder Apple TV Channel': 'Shudder',
    'AcornTV Amazon Channel': 'Acorn TV', 'Acorn TV Apple TV channel': 'Acorn TV',
    'Acorn TV Apple TV': 'Acorn TV',
    'MGM Plus': 'MGM+', 'MGM Plus Roku Premium Channel': 'MGM+', 'MGM+ Amazon Channel': 'MGM+',
    'Lionsgate+ Amazon Channel': 'Lionsgate+', 'Lionsgate+ Amazon Channels': 'Lionsgate+',
    'Discovery +': 'Discovery+', 'Discovery+ Amazon Channel': 'Discovery+',
    'CuriosityStream Apple TV Channel': 'Curiosity Stream',
    'CuriosityStream Amazon Channel': 'Curiosity Stream', 'CuriosityStream': 'Curiosity Stream',
    'Mhz Choice': 'MHz Choice', 'MZ Choice Amazon Channel': 'MHz Choice',
    'Crunchyroll Amazon Channel': 'Crunchyroll',
    'MUBI Amazon Channel': 'MUBI',
    'PBS Masterpiece Amazon Channel': 'PBS',
    'UP Faith & Family Amazon Channel ': 'UP Faith & Family',
    'UP Faith & Family Apple TV Channel': 'UP Faith & Family',
}


def all_rows():
    out, cursor = [], None
    while True:
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        out.extend(r.get('results', []))
        if not r.get('has_more'):
            return out
        cursor = r['next_cursor']


def main():
    dry = '--dry-run' in sys.argv
    changed = 0
    for row in all_rows():
        p = row['properties']
        cur = [s['name'] for s in p['Streaming']['multi_select']]
        if not cur:
            continue
        new = []
        for s in cur:
            c = COLLAPSE.get(s, s)
            if c not in new:
                new.append(c)
        if new == cur:
            continue
        name = ''.join(t['plain_text'] for t in p['Name']['title'])
        changed += 1
        if changed <= 8:
            print(f'  {name[:26]:28} {len(cur)} -> {len(new)}   {", ".join(new)[:52]}')
        if not dry:
            notion('PATCH', f"/pages/{row['id']}",
                   {'properties': {'Streaming': {'multi_select': [{'name': n} for n in new]}}})
            time.sleep(0.12)
    print(f'\n{changed} shows {"would be" if dry else ""} cleaned')


if __name__ == '__main__':
    main()
