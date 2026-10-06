"""Create the two Notion databases this project runs on: Shows and Episodes.

Run order:
  1. python3 01_create_databases.py          -> creates both, writes db_ids.json
  2. python3 01_create_databases.py --link   -> adds the Shows <-> Episodes relation
                                                plus the rollup and formulas that
                                                depend on it

Notion's 2025-09-03 API splits databases into a database_id and a data_source_id.
The schema lives on the data source, and pages are created and queried against
the data_source_id. Both ids get saved into db_ids.json for the other scripts.
"""
import os
import json
import sys
from notion_client import notion, title, TV_PARENT_PAGE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_IDS = os.path.join(BASE_DIR, 'db_ids.json')

STARS = [
    {'name': '⭐⭐⭐⭐⭐', 'color': 'pink'},
    {'name': '⭐⭐⭐⭐', 'color': 'orange'},
    {'name': '⭐⭐⭐', 'color': 'yellow'},
    {'name': '⭐⭐', 'color': 'gray'},
    {'name': '⭐', 'color': 'default'},
]

# "Watching" flips to "Returning" or "Finished" automatically once Watched Count
# catches up to Total Episodes. See sync_watched_count.py.
STATUS_OPTIONS = [
    {'name': 'Watching', 'color': 'green'},
    {'name': 'Returning', 'color': 'blue'},
    {'name': 'Paused', 'color': 'yellow'},
    {'name': 'Watchlist', 'color': 'gray'},
    {'name': 'Finished', 'color': 'purple'},
    {'name': 'Dropped', 'color': 'red'},
]

# TMDB reports "Canceled" separately. 10_check_returns.py folds it into Ended,
# because for watching purposes there is no difference.
RETURN_STATUS_OPTIONS = [
    {'name': 'Returning Series', 'color': 'green'},
    {'name': 'Ended', 'color': 'gray'},
    {'name': 'In Production', 'color': 'blue'},
    {'name': 'Planned', 'color': 'yellow'},
    {'name': 'Pilot', 'color': 'orange'},
]

# Which services count as "I can watch this right now". Edit to match what you pay for,
# and keep it in sync with AVAILABLE_NOW_FORMULA below.
# Matching is by substring, so 'Apple TV' catches TMDB's 'Apple TV Plus' and 'Max' catches 'HBO Max'.
MY_SERVICES = ['Netflix', 'Amazon Prime Video', 'Max', 'Apple TV']


def _contains_service(name):
    return f'contains(join(prop("Streaming"), ", "), "{name}")'


AVAILABLE_NOW_FORMULA = (
    '(' + ' or '.join(_contains_service(s) for s in MY_SERVICES) + ')'
    ' and ('
    '(prop("Status") == "Watching") or (prop("Status") == "Paused")'
    ' or (prop("Status") == "Watchlist"))'
)

# Human readable "12 / 22 · 55%". Prefers the Episodes rollup when episode rows
# exist, falls back to the plain Watched Count number when they do not.
_WATCHED = 'if(prop("Watched Episodes") > 0, prop("Watched Episodes"), prop("Watched Count"))'
PROGRESS_FORMULA = (
    f'if((prop("Total Episodes") > 0) and ({_WATCHED} > 0), '
    f'format({_WATCHED}) + " / " + format(prop("Total Episodes")) + " · " '
    f'+ format(round((100 * {_WATCHED}) / prop("Total Episodes"))) + "%", '
    f'if(prop("Total Episodes") > 0, "0 / " + format(prop("Total Episodes")), ""))'
)


def create_shows_db():
    return notion('POST', '/databases', {
        'parent': {'type': 'page_id', 'page_id': TV_PARENT_PAGE},
        'title': title('Shows'),
        'icon': {'type': 'emoji', 'emoji': '📺'},
        'is_inline': False,
        # 2025-09-03 API: the schema lives on the initial data source, not the database.
        'initial_data_source': {'properties': {
            'Name': {'title': {}},
            'Status': {'select': {'options': STATUS_OPTIONS}},
            'Fav': {'checkbox': {}},
            'Rating': {'select': {'options': STARS}},
            'Priority': {'select': {'options': [
                {'name': '🔥 High', 'color': 'red'},
                {'name': '⭐ Medium', 'color': 'yellow'},
                {'name': '🌱 Low', 'color': 'green'},
            ]}},
            # Free-text bookmark, e.g. "S03E10". Yours to edit, no script writes it
            # except the ones you run by hand.
            'Current S/E': {'rich_text': {}},
            'Watched Count': {'number': {'format': 'number'}},
            'Total Episodes': {'number': {'format': 'number'}},
            'Vibes': {'multi_select': {'options': []}},
            'Genre': {'multi_select': {'options': []}},
            'Streaming': {'multi_select': {'options': []}},
            'Return Status': {'select': {'options': RETURN_STATUS_OPTIONS}},
            'Next Episode': {'rich_text': {}},
            'Next Air Date': {'date': {}},
            'First Aired': {'date': {}},
            'Last Watched': {'date': {}},
            'Runtime (min)': {'number': {'format': 'number'}},
            'TMDB ID': {'number': {'format': 'number'}},
            'TMDB URL': {'url': {}},
            'Poster': {'url': {}},
            'Notes': {'rich_text': {}},
            'Added': {'created_time': {}},
            'Available Now': {'formula': {'expression': AVAILABLE_NOW_FORMULA}},
            # Rewatch tracking. Deliberately separate from Status and Watched
            # Count so starting a show over never erases the fact that you
            # finished it. A rewatch is a second lane, not a reset.
            'Rewatching': {'checkbox': {}},
            'Rewatch S/E': {'rich_text': {}},
            'Rewatch Count': {'number': {'format': 'number'}},
            'Times Watched': {'number': {'format': 'number'}},
        }},
    })


def create_episodes_db():
    return notion('POST', '/databases', {
        'parent': {'type': 'page_id', 'page_id': TV_PARENT_PAGE},
        'title': title('Episodes'),
        'icon': {'type': 'emoji', 'emoji': '🎬'},
        'is_inline': False,
        'initial_data_source': {'properties': {
            'Name': {'title': {}},
            'Season': {'number': {'format': 'number'}},
            'Episode': {'number': {'format': 'number'}},
            'Watched': {'checkbox': {}},
            'Watched Date': {'date': {}},
            'Air Date': {'date': {}},
            'Runtime (min)': {'number': {'format': 'number'}},
            'Rating': {'select': {'options': STARS}},
            'TMDB ID': {'number': {'format': 'number'}},
            'Notes': {'rich_text': {}},
        }},
    })


def link_databases(ids):
    """Second pass. Adds the relation, the rollup that counts watched episodes,
    and the Progress formula that reads it."""
    shows_ds = ids['shows']['data_source_id']
    episodes_ds = ids['episodes']['data_source_id']

    r = notion('PATCH', f'/data_sources/{shows_ds}', {'properties': {
        'Episodes': {'relation': {
            'data_source_id': episodes_ds,
            'type': 'dual_property',
            'dual_property': {},
        }},
    }})
    print('relation:', 'ok' if r.get('object') == 'data_source' else json.dumps(r)[:300])

    r = notion('PATCH', f'/data_sources/{shows_ds}', {'properties': {
        'Watched Episodes': {'rollup': {
            'relation_property_name': 'Episodes',
            'rollup_property_name': 'Watched',
            'function': 'checked',
        }},
    }})
    print('rollup:', 'ok' if r.get('object') == 'data_source' else json.dumps(r)[:300])

    r = notion('PATCH', f'/data_sources/{shows_ds}', {'properties': {
        'Progress': {'formula': {'expression': PROGRESS_FORMULA}},
    }})
    print('progress formula:', 'ok' if r.get('object') == 'data_source' else json.dumps(r)[:300])


def db_id(r):
    return r.get('id')


def data_source_id(r):
    """The create response carries data_sources: [{id, name}]. A new database
    has exactly one. If it is missing for any reason, fetch the database again."""
    ds = r.get('data_sources')
    if not ds and r.get('id'):
        ds = notion('GET', f'/databases/{r["id"]}').get('data_sources')
    if ds and isinstance(ds, list):
        return ds[0].get('id')
    return None


if __name__ == '__main__':
    if '--link' in sys.argv:
        with open(DB_IDS) as f:
            link_databases(json.load(f))
        raise SystemExit(0)

    out = {}
    for label, fn in [('shows', create_shows_db), ('episodes', create_episodes_db)]:
        print(f'Creating {label} DB...')
        r = fn()
        if r.get('object') != 'database':
            print('  failed:', json.dumps(r)[:400])
            raise SystemExit(1)
        out[label] = {'database_id': db_id(r), 'data_source_id': data_source_id(r)}
        print(' ', out[label])
        if not out[label]['data_source_id']:
            print('  no data_source_id in the response. Check NOTION_API_KEY and that the')
            print('  integration can see the parent page, then delete the half-made database.')
            raise SystemExit(1)

    with open(DB_IDS, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'\nSaved {DB_IDS}')
    print('Now run: python3 01_create_databases.py --link')
