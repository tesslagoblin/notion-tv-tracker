"""Apply the Vibes tag bank to shows.

For each show, check every vibe:
 - if show name is on the vibe's whitelist → match
 - or if any of the vibe's keywords are in the show's TMDB keywords → match

First run adds the 'Vibes' multi-select property to the Shows DB if missing,
seeded with all bank names.

Modes:
  --favorites  → tag only Favorites (preview)
  --all        → tag every hydrated show
  --dry        → don't write, just print
"""
import json, sys, time, os
from notion_client import notion, load_db_ids
from vibe_bank import VIBE_BANK

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SHOWS_DS = load_db_ids()['shows']['data_source_id']

KW_PATH = os.path.join(BASE_DIR, 'shows_keywords.json')
if not os.path.exists(KW_PATH):
    sys.exit('shows_keywords.json not found. Run `python3 05_fetch_keywords.py` first.')
with open(KW_PATH) as f:
    KW = json.load(f)


def normalize(s):
    return s.lower().replace('...','').replace('…','').replace('\u2019',"'").strip()


def show_matches_vibe(show_name, show_keywords, show_genres, show_networks, vibe_def):
    """Return True if any of the match rules hit."""
    # 1) whitelist by name
    whitelist = {normalize(x) for x in vibe_def.get('shows', [])}
    if normalize(show_name) in whitelist:
        return True
    # 2) keyword substring match
    for kw_needle in vibe_def.get('keywords', []):
        needle = kw_needle.lower()
        for sk in show_keywords:
            if needle in sk:
                return True
    # 3) network match (used for British Awkward)
    if vibe_def.get('networks'):
        want = set(vibe_def['networks'])
        if want & set(show_networks or []):
            return True
    return False


def ensure_vibes_property():
    """Add Vibes multi-select if missing; seed with all bank names."""
    ds = notion('GET', f'/data_sources/{SHOWS_DS}')
    props = ds.get('properties',{})
    all_vibes = list(VIBE_BANK.keys())
    if 'Vibes' in props and props['Vibes'].get('type') == 'multi_select':
        existing_opts = {o['name'] for o in props['Vibes']['multi_select'].get('options',[])}
        missing = [v for v in all_vibes if v not in existing_opts]
        if not missing:
            print(f'  ✓ Vibes property already has all {len(all_vibes)} tags')
            return
        print(f'  Adding {len(missing)} missing vibe tags to Vibes property...')
    else:
        print(f'  Creating Vibes multi-select property with {len(all_vibes)} tags...')
    color_cycle = ['pink','purple','red','orange','yellow','green','blue','brown','default','gray']
    # Preserve existing options (keep their ids + colors); only append new ones
    if 'Vibes' in props and props['Vibes'].get('type') == 'multi_select':
        options = list(props['Vibes']['multi_select'].get('options', []))
        existing_names = {o['name'] for o in options}
        for i, v in enumerate(all_vibes):
            if v not in existing_names:
                options.append({'name': v, 'color': color_cycle[i % len(color_cycle)]})
    else:
        options = [{'name': v, 'color': color_cycle[i % len(color_cycle)]} for i, v in enumerate(all_vibes)]
    r = notion('PATCH', f'/data_sources/{SHOWS_DS}', {
        'properties': {'Vibes': {'multi_select': {'options': options}}}
    })
    if r.get('object') == 'data_source':
        print('  ✓ Vibes property ready')
    else:
        print(f'  ✗ ERR: {json.dumps(r)[:400]}')
        sys.exit(1)


def list_shows(favs_only=False):
    rows, cursor = [], None
    while True:
        body = {'page_size': 100}
        if favs_only:
            body['filter'] = {'property':'Fav','checkbox':{'equals':True}}
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        rows.extend(r.get('results', []))
        if r.get('has_more'):
            cursor = r.get('next_cursor')
        else:
            break
    return rows


def tag_row(row, dry=False):
    p = row['properties']
    name = ''.join(t.get('plain_text','') for t in p.get('Name',{}).get('title',[]))
    tmdb_id = p.get('TMDB ID',{}).get('number')
    keywords = KW.get(str(int(tmdb_id)) if tmdb_id else '', {}).get('keywords', [])
    genres = [g['name'] for g in p.get('Genre',{}).get('multi_select',[]) or []]
    networks = [n['name'] for n in p.get('Streaming',{}).get('multi_select',[]) or []]
    existing = [v['name'] for v in p.get('Vibes',{}).get('multi_select',[]) or []]

    matched = []
    for vibe_name, defn in VIBE_BANK.items():
        if show_matches_vibe(name, keywords, genres, networks, defn):
            matched.append(vibe_name)

    if not matched:
        return name, [], []

    # Union with existing (don't clobber user edits)
    final = sorted(set(existing + matched))
    if set(final) == set(existing):
        return name, matched, []  # no update needed

    if not dry:
        r = notion('PATCH', f'/pages/{row["id"]}', {
            'properties': {'Vibes': {'multi_select': [{'name': v} for v in final]}}
        })
        if r.get('object') != 'page':
            print(f'  ✗ {name}: {json.dumps(r)[:200]}')
    return name, matched, final


def main():
    favs_only = '--favorites' in sys.argv
    dry = '--dry' in sys.argv

    print('Ensuring Vibes property exists...')
    if not dry:
        ensure_vibes_property()

    print(f'\nQuerying shows{"(favorites only)" if favs_only else ""}...')
    rows = list_shows(favs_only=favs_only)
    print(f'  {len(rows)} shows to process\n')

    tagged = []
    untagged = []
    for i, row in enumerate(rows):
        name, matched, final = tag_row(row, dry=dry)
        if matched:
            tagged.append((name, matched))
            print(f'{i+1}/{len(rows)}  {name}  →  {", ".join(matched)}', flush=True)
        else:
            untagged.append(name)
            print(f'{i+1}/{len(rows)}  {name}  →  (no match)', flush=True)
        if not dry:
            time.sleep(0.3)

    print(f'\n✅ Tagged {len(tagged)}, {len(untagged)} unmatched')
    if untagged:
        print(f'\nUnmatched: {untagged[:30]}')
        if len(untagged) > 30:
            print(f'  ...and {len(untagged)-30} more')

    with open(os.path.join(BASE_DIR, 'vibe_tag_results.json'),'w') as f:
        json.dump({'tagged': tagged, 'untagged': untagged}, f, indent=2)


if __name__ == '__main__':
    main()
