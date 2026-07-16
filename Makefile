.PHONY: build preview etl data clean

build:
	@echo "{\"date\": \"$$(gh api /repos/:owner/:repo/commits?per_page=1 --jq '.[0].commit.committer.date' 2>/dev/null || git log -1 --format=%cI)\"}" > data/last_updated.json
	$(MAKE) data
	rm -rf docs/.observable
	yarn build

preview:
	yarn preview

# Expensive, auth-gated: pull cargo-level LNG trades from Kpler into the
# committed CSV. Needs `gcloud auth login` against project data-desk-web.
# Run locally when refreshing the data, then commit data/benoa_lng_trades.csv.
etl:
	python3 scripts/fetch_benoa_lng.py
	python3 scripts/fetch_vessel_tracks.py

# CI-safe: rebuild the DuckDB tables from the committed CSV. No Kpler auth.
data:
	@mkdir -p data
	duckdb data/data.duckdb < scripts/build_benoa_lng.sql
	@echo "Data updated"

clean:
	rm -rf docs/.observable/dist
