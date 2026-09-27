# Common tasks. Everything runs from scripts/ with plain python3, no deps.
PY := python3
S  := scripts

.PHONY: help check setup link add hydrate tag taste digest post returns sync vibes

help:
	@echo "make check     - verify keys, db ids and Notion schema"
	@echo "make setup     - create the Notion databases"
	@echo "make link      - add the relation, rollup and formulas"
	@echo "make add SHOW='Show Name'  - add a show (use PICK=1 to choose the match)"
	@echo "make hydrate   - refresh streaming providers and covers"
	@echo "make tag       - refetch TMDB keywords and re-apply vibe tags"
	@echo "make vibes     - report on vibe coverage, list untagged shows"
	@echo "make taste     - rebuild the taste profile"
	@echo "make digest    - dry run this week's recommendations"
	@echo "make post      - send this week's recommendations"
	@echo "make returns   - check for returning seasons"
	@echo "make sync      - sync watched counts from episode checkboxes"

check:   ; cd $(S) && $(PY) doctor.py
setup:   ; cd $(S) && $(PY) 01_create_databases.py
link:    ; cd $(S) && $(PY) 01_create_databases.py --link
add:     ; cd $(S) && $(PY) add_show.py $(if $(PICK),--pick,) "$(SHOW)"
hydrate: ; cd $(S) && $(PY) 03_streaming_hydrate.py && $(PY) 04_hydrate_covers.py
tag:     ; cd $(S) && $(PY) 05_fetch_keywords.py && $(PY) 07_auto_vibe_tag.py --all
vibes:   ; cd $(S) && $(PY) vibe_report.py
taste:   ; cd $(S) && $(PY) 08_taste_profile.py
digest:  ; cd $(S) && $(PY) 09_weekly_discover.py
post:    ; cd $(S) && $(PY) 09_weekly_discover.py --post
returns: ; cd $(S) && $(PY) 10_check_returns.py
sync:    ; cd $(S) && $(PY) sync_watched_count.py
