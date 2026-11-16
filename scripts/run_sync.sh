#!/bin/bash
# Fast label catch-up. Runs from the system crontab every 5 minutes so the
# Next Episode label keeps up with the +1 button in Notion without burning an
# agent turn. Cheap: one Notion query when nothing has drifted.
cd "$(dirname "$0")" || exit 1
export NOTION_API_KEY="$(grep -m1 '^NOTION_API_KEY=' .env 2>/dev/null | cut -d= -f2- | tr -d '"')"
[ -z "$NOTION_API_KEY" ] && exit 1
/usr/bin/python3 sync_from_count.py >> /tmp/tv-sync.log 2>&1
/usr/bin/python3 auto_status.py >> /tmp/tv-sync.log 2>&1
