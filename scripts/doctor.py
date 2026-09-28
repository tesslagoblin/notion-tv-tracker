"""Preflight check. Run this before anything else, and any time something breaks.

    python3 doctor.py

Checks your keys, your db_ids.json, that the integration can actually see the
databases, and that the Notion schema has every property the scripts expect.
Prints what is wrong and how to fix it. Changes nothing.
"""
import os
import json
import subprocess
import sys

# Same .env loader every other script uses (repo root, then scripts/).
from notion_client import load_env

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_IDS = os.path.join(BASE_DIR, 'db_ids.json')
NOTION_VERSION = '2025-09-03'

OK, WARN, FAIL = '  ok  ', ' warn ', ' FAIL '
problems = []


def say(level, msg, fix=None):
    print(f'[{level}] {msg}')
    if level == FAIL:
        problems.append((msg, fix))
    if fix and level != OK:
        print(f'         -> {fix}')


def http(url, headers):
    cmd = ['curl', '-s', '-w', '\n%{http_code}', url]
    for h in headers:
        cmd += ['-H', h]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    body, _, code = r.stdout.rpartition('\n')
    try:
        return int(code), json.loads(body)
    except Exception:
        return int(code) if code.isdigit() else 0, {'raw': body[:200]}


# Every property the scripts read or write, and who needs it.
REQUIRED_SHOWS = {
    'Name': 'title', 'Status': 'select', 'Fav': 'checkbox', 'Rating': 'select',
    'Watched Count': 'number', 'Total Episodes': 'number',
    'Vibes': 'multi_select', 'Genre': 'multi_select', 'Streaming': 'multi_select',
    'Return Status': 'select', 'Next Episode': 'rich_text', 'Next Air Date': 'date',
    'Current S/E': 'rich_text', 'First Aired': 'date', 'Last Watched': 'date',
    'Runtime (min)': 'number', 'TMDB ID': 'number', 'TMDB URL': 'url',
    'Poster': 'url', 'Notes': 'rich_text',
}
REQUIRED_EPISODES = {
    'Name': 'title', 'Season': 'number', 'Episode': 'number',
    'Watched': 'checkbox', 'Air Date': 'date', 'TMDB ID': 'number',
}


def check_keys():
    print('\n--- keys ---')
    notion_key = os.environ.get('NOTION_API_KEY', '')
    tmdb_key = os.environ.get('TMDB_API_KEY', '')

    if not notion_key or notion_key.startswith('['):
        say(FAIL, 'NOTION_API_KEY not set', 'copy .env.example to .env and fill it in')
    else:
        code, r = http('https://api.notion.com/v1/users/me',
                       [f'Authorization: Bearer {notion_key}',
                        f'Notion-Version: {NOTION_VERSION}'])
        if code == 200:
            say(OK, f"Notion token valid (integration: {r.get('name', 'unnamed')})")
        else:
            say(FAIL, f'Notion token rejected (HTTP {code})',
                'check the token at notion.so/my-integrations')

    if not tmdb_key or tmdb_key.startswith('['):
        say(FAIL, 'TMDB_API_KEY not set', 'get a free v3 key at themoviedb.org/settings/api')
    else:
        code, _ = http(f'https://api.themoviedb.org/3/tv/1396?api_key={tmdb_key}', [])
        say(OK if code == 200 else FAIL,
            'TMDB key valid' if code == 200 else f'TMDB key rejected (HTTP {code})')

    return notion_key


def check_schema(notion_key):
    print('\n--- databases ---')
    if not os.path.exists(DB_IDS):
        say(FAIL, 'db_ids.json missing', 'run: python3 01_create_databases.py')
        return
    ids = json.load(open(DB_IDS))
    headers = [f'Authorization: Bearer {notion_key}', f'Notion-Version: {NOTION_VERSION}']

    for label, required in [('shows', REQUIRED_SHOWS), ('episodes', REQUIRED_EPISODES)]:
        ds = ids.get(label, {}).get('data_source_id')
        if not ds:
            say(FAIL, f'no data_source_id for {label} in db_ids.json',
                'run: python3 01_create_databases.py')
            continue
        code, r = http(f'https://api.notion.com/v1/data_sources/{ds}', headers)
        if code == 404:
            say(FAIL, f'{label} database not visible to the integration',
                'open the page in Notion, click ... > Connections, add your integration')
            continue
        if code != 200:
            say(FAIL, f'{label} lookup failed (HTTP {code})')
            continue

        props = r.get('properties', {})
        say(OK, f'{label}: found, {len(props)} properties')

        missing = [p for p in required if p not in props]
        wrong = [f'{p} is {props[p]["type"]}, expected {t}'
                 for p, t in required.items()
                 if p in props and props[p]['type'] != t]
        if missing:
            say(FAIL, f'{label} missing: {", ".join(missing)}',
                'add them in Notion, or recreate with 01_create_databases.py')
        if wrong:
            say(FAIL, f'{label} wrong types: {"; ".join(wrong)}')

        if label == 'shows':
            for derived, hint in [('Episodes', 'relation'), ('Watched Episodes', 'rollup'),
                                  ('Progress', 'formula'), ('Available Now', 'formula')]:
                if derived not in props:
                    fix = ('run: python3 01_create_databases.py --link' if derived in ('Episodes', 'Watched Episodes')
                           else 'created by the first setup run; add it back in Notion or recreate with 01_create_databases.py')
                    say(WARN, f'shows missing derived field "{derived}" ({hint})', fix)


def main():
    load_env()
    print('TV tracker doctor')
    notion_key = check_keys()
    if notion_key and not notion_key.startswith('['):
        check_schema(notion_key)

    print()
    if problems:
        print(f'{len(problems)} problem(s) to fix. Details above.')
        sys.exit(1)
    print('All good. You are ready to run the other scripts.')


if __name__ == '__main__':
    main()
