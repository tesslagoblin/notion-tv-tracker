"""Report on Vibes coverage across the library.

    python3 vibe_report.py              # summary + the untagged list
    python3 vibe_report.py --untagged   # just the untagged names, one per line

Auto-tagging only fires when a show's TMDB keywords hit one of the vibes in
vibe_bank.py. Shows with thin keyword data come back with nothing, and a show
with no vibes is invisible in every vibe-filtered view. This tells you which
ones need a hand, and why.
"""
import sys
from collections import Counter
from notion_client import notion, load_db_ids

SHOWS_DS = load_db_ids()['shows']['data_source_id']


def all_shows():
    rows, cursor = [], None
    while True:
        body = {'page_size': 100}
        if cursor:
            body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        rows.extend(r.get('results', []))
        if not r.get('has_more'):
            return rows
        cursor = r['next_cursor']


def main():
    quiet = '--untagged' in sys.argv
    rows = all_shows()

    shows = []
    for r in rows:
        p = r['properties']
        shows.append({
            'name': ''.join(t['plain_text'] for t in p['Name']['title']),
            'vibes': [v['name'] for v in p['Vibes']['multi_select']],
            'status': (p['Status']['select'] or {}).get('name'),
            'fav': p['Fav']['checkbox'],
        })

    untagged = [s for s in shows if not s['vibes']]

    if quiet:
        for s in sorted(untagged, key=lambda s: s['name']):
            print(s['name'])
        return

    tagged = [s for s in shows if s['vibes']]
    counts = Counter(v for s in shows for v in s['vibes'])
    pct = 100 * len(tagged) / len(shows) if shows else 0

    print(f'{len(shows)} shows, {len(tagged)} tagged ({pct:.0f}%), {len(untagged)} with no vibes\n')

    print('Most used vibes:')
    for v, c in counts.most_common(10):
        print(f'  {c:4d}  {v}')

    if counts:
        rare = [v for v, c in counts.items() if c <= 2]
        if rare:
            print(f'\nBarely used (2 or fewer): {", ".join(sorted(rare))}')
            print('  Either the keyword needles are too narrow, or the tag is not earning its place.')

    print(f'\nAverage tags per tagged show: {sum(len(s["vibes"]) for s in tagged) / max(len(tagged), 1):.1f}')

    if untagged:
        print(f'\nNo vibes yet ({len(untagged)}). Favorites first, those matter most:')
        for s in sorted(untagged, key=lambda s: (not s['fav'], s['name'])):
            mark = '*' if s['fav'] else ' '
            print(f'  {mark} {s["name"]}  [{s["status"]}]')
        print('\nFix by adding the show to a vibe\'s `shows` whitelist in vibe_bank.py,')
        print('then re-run: python3 07_auto_vibe_tag.py --all')


if __name__ == '__main__':
    main()
