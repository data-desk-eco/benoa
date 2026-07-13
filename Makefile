.PHONY: build preview data clean

build:
	@echo "{\"date\": \"$$(gh api /repos/:owner/:repo/commits?per_page=1 --jq '.[0].commit.committer.date' 2>/dev/null || git log -1 --format=%cI)\"}" > data/last_updated.json
	yarn build

preview:
	yarn preview

data:
	@mkdir -p data
	@echo "Fetching repository data from GitHub API..."
	gh api "/orgs/data-desk-eco/repos" --paginate -q \
		'[.[] | select(.name != "data-desk-eco.github.io" and .private == false and .has_pages == true and .description != null and .description != "") | {name: .name, description: .description, url: "https://research.datadesk.eco/\(.name)/", repo_url: .html_url, created_at: .created_at}]' \
		| jq -s 'add' \
		| duckdb data/data.duckdb "CREATE OR REPLACE TABLE projects AS SELECT * FROM read_json('/dev/stdin')"
	@echo "Data updated"

clean:
	rm -rf docs/.observable/dist
