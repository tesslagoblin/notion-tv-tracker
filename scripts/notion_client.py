"""Shared helpers: config loading and a thin Notion API wrapper.

Every other script imports from here.
"""
import os
import json
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BASE_DIR)
DB_IDS_PATH = os.path.join(BASE_DIR, 'db_ids.json')
NOTION_VERSION = '2025-09-03'


def load_env():
    """Load .env into the environment if the vars are not already exported.

    Looks in the repo root first, then alongside the scripts, so it works
    whichever place you dropped the file.
    """
    for path in (os.path.join(REPO_DIR, '.env'), os.path.join(BASE_DIR, '.env')):
        if not os.path.exists(path):
            continue
        for line in open(path):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        return


load_env()

TV_PARENT_PAGE = os.environ.get('NOTION_PARENT_PAGE_ID', '[YOUR_NOTION_PARENT_PAGE_ID]')


def require_key(name, hint):
    val = os.environ.get(name, '')
    if not val or val.startswith('['):
        sys.exit(f'{name} is not set.\n  {hint}\n  Run `python3 doctor.py` to check your setup.')
    return val


def tmdb_key():
    return require_key('TMDB_API_KEY',
                       'Get a free v3 key at themoviedb.org/settings/api, then put it in .env')


def load_db_ids():
    """Read db_ids.json, with a useful error instead of a traceback."""
    if not os.path.exists(DB_IDS_PATH):
        sys.exit('db_ids.json not found.\n'
                 '  Run `python3 01_create_databases.py` first, then '
                 '`python3 01_create_databases.py --link`.')
    with open(DB_IDS_PATH) as f:
        return json.load(f)


def shows_ds():
    return load_db_ids()['shows']['data_source_id']


def episodes_ds():
    return load_db_ids()['episodes']['data_source_id']


def notion(method, path, payload=None):
    """Call the Notion API. Returns parsed JSON, or a dict with 'raw' on a parse failure."""
    key = require_key('NOTION_API_KEY',
                      'Create an integration at notion.so/my-integrations, then put the token in .env')
    cmd = ['curl', '-s', '-X', method, f'https://api.notion.com/v1{path}',
           '-H', f'Authorization: Bearer {key}',
           '-H', f'Notion-Version: {NOTION_VERSION}',
           '-H', 'Content-Type: application/json']
    if payload is not None:
        cmd += ['-d', json.dumps(payload)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'raw': r.stdout, 'err': r.stderr}


def api_ok(r):
    """True if a notion() response looks like a real success.

    notion() never raises. A failed call comes back as Notion's error JSON
    ({"object": "error", ...}) or as {'raw': ...} when curl got nothing usable,
    so anything that writes or deletes has to check this before trusting it.
    """
    return isinstance(r, dict) and r.get('object') not in (None, 'error') and 'raw' not in r


def api_error(r):
    """Short printable reason for a failed notion() call."""
    if not isinstance(r, dict):
        return repr(r)[:200]
    if r.get('object') == 'error':
        return f"{r.get('status')} {r.get('code')}: {r.get('message')}"[:300]
    return json.dumps(r)[:300]


def title(text):
    return [{'type': 'text', 'text': {'content': text}}]
