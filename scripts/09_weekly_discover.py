"""Weekly new-releases scan - TMDB /discover/tv weighted by my taste profile.

Runs every Sunday morning:
  1. Re-load taste profile (top genres from Notion Shows DB)
  2. Query TMDB /discover/tv - new/upcoming with matching genres
  3. Filter out shows already tracked
  4. Tag each candidate with vibes, then rank by popularity, vote_avg, genre
     match and vibe overlap. A pick has to share a vibe with the shows you are
     Watching (or your Fav shows, or your whole tagged library if you have
     neither yet)
  5. Print the top picks, or with --post send them to a Discord webhook
     (DISCORD_WEBHOOK_URL in .env), each with a why-it-matches blurb
"""
import os, json, subprocess, time, sys, urllib.parse, urllib.request, urllib.error, datetime
from notion_client import notion, load_db_ids, tmdb_key, api_ok, api_error
from vibe_bank import match_vibes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TMDB_API_KEY = tmdb_key()
TMDB_BASE = 'https://api.themoviedb.org/3'
TMDB_IMG = 'https://image.tmdb.org/t/p/w500'

# Optional: where --post sends the weekly digest. Leave unset to just print it.
# Discord: channel settings > Integrations > Webhooks > New Webhook > Copy URL.
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')
DISCORD_LIMIT = 2000  # Discord's max characters per message

SHOWS_DS = load_db_ids()['shows']['data_source_id']

PROFILE_PATH = os.path.join(BASE_DIR, 'taste_profile.json')
if not os.path.exists(PROFILE_PATH):
    sys.exit('taste_profile.json not found. Run `python3 08_taste_profile.py` first.')
with open(PROFILE_PATH) as f:
    profile = json.load(f)


def split_message(msg, limit=DISCORD_LIMIT):
    """Split on blank lines so a pick never gets cut in half. Falls back to a hard
    cut only if a single paragraph is longer than the limit."""
    chunks, cur = [], ''
    for para in msg.split('\n\n'):
        while len(para) > limit:
            if cur:
                chunks.append(cur)
                cur = ''
            chunks.append(para[:limit])
            para = para[limit:]
        candidate = f'{cur}\n\n{para}' if cur else para
        if len(candidate) > limit and cur:
            chunks.append(cur)
            cur = para
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return chunks


def post_to_discord(msg, url):
    """POST the digest to a Discord webhook, split into <=2000 char messages.
    Returns True if every chunk went through."""
    for chunk in split_message(msg):
        req = urllib.request.Request(
            url, data=json.dumps({'content': chunk}).encode('utf-8'), method='POST',
            # Discord rejects urllib's default User-Agent, so send a real one.
            headers={'Content-Type': 'application/json',
                     'User-Agent': 'notion-tv-tracker (weekly digest)'})
        try:
            with urllib.request.urlopen(req, timeout=20):
                pass
        except urllib.error.HTTPError as e:
            print(f'Discord webhook failed: HTTP {e.code} {e.read().decode("utf-8", "replace")[:300]}')
            return False
        except urllib.error.URLError as e:
            print(f'Discord webhook failed: {e.reason}')
            return False
        time.sleep(0.5)  # stay well under the webhook rate limit
    return True


def tmdb(path, params):
    q = '&'.join(f'{k}={urllib.parse.quote(str(v), safe=",")}' for k,v in {**params, 'api_key': TMDB_API_KEY}.items())
    url = f'{TMDB_BASE}{path}?{q}'
    r = subprocess.run(['curl','-s',url], capture_output=True, text=True, timeout=30)
    try: return json.loads(r.stdout)
    except: return None


PAST_DISCOVERS = os.path.join(BASE_DIR, 'past_discovers.json')
KEEP_WEEKS = 6  # exclude anything recommended in the last N weeks


def fresh_exclusion_list():
    """Pull current Shows DB TMDB IDs so we don't re-suggest anything she already has,
    plus the last KEEP_WEEKS of digest picks so recommendations stay fresh."""
    exclude = set()
    cursor = None
    while True:
        body = {'page_size': 100}
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        for row in r.get('results', []):
            tid = row['properties'].get('TMDB ID',{}).get('number')
            if tid: exclude.add(int(tid))
        if r.get('has_more'):
            cursor = r.get('next_cursor')
        else:
            break
    # Layer in recent digest picks
    try:
        with open(PAST_DISCOVERS) as f:
            past = json.load(f)
        for week in past[-KEEP_WEEKS:]:
            for tid in week.get('ids', []):
                exclude.add(int(tid))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return exclude


def record_this_week(top_picks):
    """Append this week's picks to the rolling history."""
    try:
        with open(PAST_DISCOVERS) as f:
            past = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        past = []
    past.append({
        'date': datetime.date.today().isoformat(),
        'ids': [s['id'] for s, _ in top_picks],
    })
    past = past[-KEEP_WEEKS*2:]  # keep some extra beyond exclusion window
    with open(PAST_DISCOVERS, 'w') as f:
        json.dump(past, f, indent=2)


TV_GENRE_NAME_TO_ID = None
def genre_map():
    global TV_GENRE_NAME_TO_ID
    if TV_GENRE_NAME_TO_ID is None:
        r = tmdb('/genre/tv/list', {'language':'en-US'})
        TV_GENRE_NAME_TO_ID = {g['name']: g['id'] for g in (r.get('genres') or [])}
    return TV_GENRE_NAME_TO_ID


def discover_new(days_back=60, days_forward=365, min_votes=5):
    """Three passes:
 - aired: last 60 days
 - soon:  today → next 90 days
 - later: 90 days → 12 months out (announced/planned but not yet close)
    """
    today = datetime.date.today()
    back = (today - datetime.timedelta(days=days_back)).isoformat()
    soon = (today + datetime.timedelta(days=90)).isoformat()
    fwd = (today + datetime.timedelta(days=days_forward)).isoformat()

    gmap = genre_map()
    top_genre_ids = []
    for g in profile['top_genres'][:5]:
        gid = gmap.get(g['name'])
        if gid: top_genre_ids.append(gid)
    # OR-join top genres → wider net; scoring handles precision
    genre_query = '|'.join(str(g) for g in top_genre_ids[:5])
    genre_names = {gmap[g['name']]: g['name'] for g in profile['top_genres'][:5] if g['name'] in gmap}

    results = {}
    # Pull first 2 pages per bucket for a bigger pool, English-original leaning
    for label, date_gte, date_lte in [
        ('aired', back, today.isoformat()),
        ('soon', today.isoformat(), soon),
        ('later', soon, fwd),
    ]:
        for page in (1, 2):
            # Real vote-count floors: aired needs traction. soon/later are both
            # unreleased so they can't have votes at all -- floor 0, scored down.
            vc_floor = {'aired': min_votes, 'soon': 0, 'later': 0}[label]
            r = tmdb('/discover/tv', {
                'sort_by': 'popularity.desc',
                'first_air_date.gte': date_gte,
                'first_air_date.lte': date_lte,
                'with_genres': genre_query,
                'with_original_language': 'en',
                'vote_count.gte': vc_floor,
                'language': 'en-US',
                'page': page,
            })
            for r_ in (r.get('results') or []):
                r_['_bucket'] = label
                results[r_['id']] = r_
    return list(results.values()), genre_names


def library_vibe_weights():
    """Read the Vibes column off every show in Notion, in one paginated pass.

    Returns three Counters: vibes on Watching shows, vibes on Fav shows, and
    vibes across every tagged show in the library."""
    from collections import Counter
    watching, favs, everything = Counter(), Counter(), Counter()
    cursor = None
    while True:
        body = {'page_size': 100}
        if cursor: body['start_cursor'] = cursor
        r = notion('POST', f'/data_sources/{SHOWS_DS}/query', body)
        if not api_ok(r):
            print(f'  could not read vibes from Notion: {api_error(r)}')
            break
        for row in r.get('results', []):
            p = row['properties']
            vibes = [v['name'] for v in p.get('Vibes', {}).get('multi_select', []) or []]
            status = (p.get('Status', {}).get('select') or {}).get('name')
            for v in vibes:
                everything[v] += 1
                if status == 'Watching':
                    watching[v] += 1
                if p.get('Fav', {}).get('checkbox'):
                    favs[v] += 1
        if not r.get('has_more'): break
        cursor = r.get('next_cursor')
    return watching, favs, everything


def pick_current_vibes(watching, favs, everything):
    """The vibes a pick has to share to make the digest, plus a label saying
    where they came from.

    Vibes on currently-Watching shows are the best signal, since they are what
    she's ACTIVELY into right now. This is what made Vampire Lestat land -
    Interview With The Vampire (Supernatural Teen) was being watched. A new
    library is mostly Watchlist though, so fall back to Fav shows, then to
    every tagged show, rather than posting an empty digest."""
    for counts, label in ((watching, 'what you are watching'),
                          (favs, 'your favorites'),
                          (everything, 'your whole library')):
        if counts:
            return {v: n * 3 for v, n in counts.items()}, label
    return {}, 'nothing yet (no show has a vibe, run make tag)'


_WATCHING, _FAVS, LIBRARY_VIBES = library_vibe_weights()
# LIBRARY_VIBES: how many shows in the whole library carry each vibe.
# CURRENT_VIBES: the vibes a pick must overlap with (see pick_current_vibes).
CURRENT_VIBES, CURRENT_SOURCE = pick_current_vibes(_WATCHING, _FAVS, LIBRARY_VIBES)

# Format/structure vibes rather than taste vibes - a show being a "limited series"
# or "true crime" doesn't say much about whether you'll like it. Drop these
# from taste scoring so content vibes (Teen Soap / Supernatural / Girly Pop) win.
FORMAT_VIBES = {'Anthology / Limited', 'True Crime'}


def candidate_vibes(show, keywords):
    """Same match rules as 07_auto_vibe_tag (vibe_bank.match_vibes), applied to a
    TMDB candidate. Genres come from its TMDB genre_ids. There is no Streaming
    column for a show you have not added, so networks rules never fire here."""
    id_to_name = {gid: name for name, gid in genre_map().items()}
    genres = [id_to_name[g] for g in (show.get('genre_ids') or []) if g in id_to_name]
    return match_vibes(show.get('name') or '', keywords, genres)


def fetch_keywords(tmdb_id):
    r = tmdb(f'/tv/{tmdb_id}/keywords', {})
    if not r: return []
    return [k['name'].lower() for k in (r.get('results') or [])]


def score(show, genre_names, kw_cache=None):
    """Vibe-first scoring, gated on CURRENT_VIBES (Watching shows, or the
    fallback). A pick MUST share ≥1 content vibe with those
    or it gets a heavy penalty. This is what makes Vampire Lestat surface
    over generic-crime-limited-series filler."""
    pop = show.get('popularity') or 0
    vote = show.get('vote_average') or 0
    genre_hits = sum(1 for g in show.get('genre_ids') or [] if g in genre_names)
    base = pop * 0.05 + vote * 3 + genre_hits * 5
    if kw_cache and show['id'] in kw_cache:
        vibes = candidate_vibes(show, kw_cache[show['id']])
        content_vibes = [v for v in vibes if v not in FORMAT_VIBES]
        if not content_vibes:
            # Only format vibes (Anthology/True Crime) or nothing → not a taste signal
            return base * 0.1, vibes
        cur_hits = [v for v in content_vibes if v in CURRENT_VIBES]
        if not cur_hits:
            # No overlap with what she's currently into - deprioritize
            return base * 0.3, vibes
        lib_score = sum(LIBRARY_VIBES.get(v, 0) for v in content_vibes)
        cur_score = sum(CURRENT_VIBES.get(v, 0) for v in content_vibes)
        multi_bonus = 20 if len(content_vibes) >= 2 else 0
        return base + lib_score * 3 + cur_score * 8 + multi_bonus, vibes
    return base * 0.3, []


def format_pick(show, genre_names, vibes=None):
    name = show.get('name') or show.get('original_name') or '?'
    first_air = show.get('first_air_date') or 'TBA'
    bucket = show.get('_bucket', '')
    bucket_label = {'aired':'📅 aired','soon':'⏳ soon','later':'🔮 later'}.get(bucket, '')
    overview = (show.get('overview') or '').strip()
    if len(overview) > 180:
        overview = overview[:177] + '…'
    hit_genres = [genre_names[g] for g in (show.get('genre_ids') or []) if g in genre_names]
    genre_str = ' / '.join(hit_genres[:3]) if hit_genres else 'unlisted'
    tmdb_url = f'https://www.themoviedb.org/tv/{show["id"]}'
    vibe_line = f'\n_vibes:_ {", ".join(vibes[:4])}' if vibes else ''
    return f'**{name}** ({first_air}) {bucket_label} - {genre_str}{vibe_line}\n{overview}\n{tmdb_url}'


def main():
    posting = '--post' in sys.argv
    if posting and (not DISCORD_WEBHOOK_URL or DISCORD_WEBHOOK_URL.startswith('[')):
        sys.exit('--post needs DISCORD_WEBHOOK_URL in .env. Nothing was sent.')

    print(f'Scoring against vibes from {CURRENT_SOURCE} ({len(CURRENT_VIBES)} vibes)')
    print('Refreshing exclusion list from Notion...')
    already_have = fresh_exclusion_list()
    print(f'  {len(already_have)} shows already tracked')

    print('\nQuerying TMDB /discover for matches to top genres...')
    candidates, genre_names = discover_new()
    print(f'  {len(candidates)} raw candidates before filtering')

    filtered = [c for c in candidates if c['id'] not in already_have]
    # Pre-rank by genre+popularity per bucket so no bucket gets crowded out
    by_bucket = {'aired': [], 'soon': [], 'later': []}
    for c in filtered:
        by_bucket.setdefault(c.get('_bucket','aired'), []).append(c)
    for k in by_bucket:
        by_bucket[k].sort(key=lambda s: score(s, genre_names)[0], reverse=True)

    # Pre-rank pool: top 15 aired + top 10 soon + top 10 later (for keyword fetch)
    prelim_top = by_bucket['aired'][:15] + by_bucket['soon'][:10] + by_bucket['later'][:10]
    print(f'\nFetching keywords for {len(prelim_top)} pre-ranked candidates...')
    kw_cache = {}
    for s in prelim_top:
        kw_cache[s['id']] = fetch_keywords(s['id'])
        time.sleep(0.05)

    # Re-rank with vibe boost, per bucket
    def rank_bucket(items):
        return sorted(
            ((s, *score(s, genre_names, kw_cache)) for s in items),
            key=lambda t: t[1], reverse=True)

    ranked_aired = rank_bucket(by_bucket['aired'][:15])
    ranked_soon = rank_bucket(by_bucket['soon'][:10])
    ranked_later = rank_bucket(by_bucket['later'][:10])

    # Quality-gated slot allocation. Every pick needs ≥1 vibe match (candidate_vibes non-empty).
    # Bucket targets: 3 aired + 2 soon + 1 later. If a bucket runs out of vibe-matched shows,
    # skip rather than backfill filler - better to post 4 great picks than 6 with 2 duds.
    def is_quality(entry):
        _, _, vibes = entry
        content_vibes = [v for v in vibes if v not in FORMAT_VIBES]
        return any(v in CURRENT_VIBES for v in content_vibes)

    slot_targets = [(ranked_aired, 3, 'aired'), (ranked_soon, 2, 'soon'), (ranked_later, 1, 'later')]
    top = []
    seen = set()
    for pool, n, _label in slot_targets:
        count = 0
        for entry in pool:
            if not is_quality(entry): continue
            s, _, vibes = entry
            if s['id'] in seen: continue
            top.append((s, vibes))
            seen.add(s['id'])
            count += 1
            if count >= n: break
    # Backfill from best remaining quality picks across all buckets (still vibe-gated)
    all_ranked = sorted(ranked_aired + ranked_soon + ranked_later, key=lambda t: t[1], reverse=True)
    for entry in all_ranked:
        if len(top) >= 6: break
        if not is_quality(entry): continue
        s, _, vibes = entry
        if s['id'] in seen: continue
        top.append((s, vibes))
        seen.add(s['id'])

    print(f'\n▓ Top {len(top)} picks (vibe-weighted, mixed buckets):')
    for i, (s, vibes) in enumerate(top, 1):
        print(f'  {i}. {s.get("name")} ({s.get("_bucket")}, pop={s.get("popularity"):.0f}, vote={s.get("vote_average")}) - vibes: {vibes}')

    # Build Discord message
    header = f'📺 **new for the watchlist** - {datetime.date.today().strftime("%b %d")}\n'
    header += f'_ranked by vibe overlap with {CURRENT_SOURCE} - 📅 aired / ⏳ soon / 🔮 later announced_\n\n'
    body = '\n\n'.join(f'{i+1}. {format_pick(s, genre_names, vibes)}' for i, (s, vibes) in enumerate(top))
    msg = header + body

    # Save preview locally
    with open(os.path.join(BASE_DIR, 'last_discover.json'),'w') as f:
        json.dump({
            'date': datetime.date.today().isoformat(),
            'picks': top,
            'message': msg,
        }, f, indent=2)

    if posting:
        if not post_to_discord(msg, DISCORD_WEBHOOK_URL):
            sys.exit(1)
        # Only add to rolling exclusion after actually posting so dry-runs don't pollute history
        record_this_week(top)
        print('✓ Posted to your Discord channel')
    else:
        print('\n--- preview ---')
        print(msg)
        print('\n(dry-run - pass --post to actually send)')


if __name__ == '__main__':
    main()
