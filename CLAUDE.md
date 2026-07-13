# Data Desk Index

This is the homepage for Data Desk research notebooks at research.datadesk.eco.

## What it does

- `make data` fetches all public repos from the `data-desk-eco` GitHub org and stores them in `data/data.duckdb`
- The notebook (`docs/index.html`) displays the list of projects with links

## Data pipeline

No scripts directory — data fetching is done directly in the Makefile via `gh api`.
