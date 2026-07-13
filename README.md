# Data Desk Research Index

This repository serves two purposes:
1. The central index for all Data Desk research notebooks at [`https://research.datadesk.eco/`](https://research.datadesk.eco/)
2. A template for creating new research notebooks

## Creating a new research notebook

1. Use this repository as a template to create a new repo (the name becomes the URL)
2. Go to "Settings" → "Pages" → "Build and deployment" and select "GitHub Actions"
3. Clone your new repository and install dependencies: `yarn` (or `npm install`)
4. Run preview: `make preview` (or `yarn preview`)
5. Edit `docs/index.html` in your text editor or [Observable Desktop](https://observablehq.com/notebook-kit/desktop)
6. Build: `make build` (or `yarn build`)
7. Commit and push - GitHub Actions will automatically deploy to `https://research.datadesk.eco/[repo-name]`

## Makefile targets

- `make preview` - Start local dev server with hot reload
- `make build` - Build notebook to `docs/.observable/dist/`
- `make etl` - Run expensive local computation (if needed)
- `make data` - Lightweight data refresh (runs in GitHub Actions)
- `make clean` - Remove build artifacts

## How the index works

- A GitHub Action runs daily (or on push) to fetch all public repos with Pages enabled
- Data is written to `data/data.duckdb` as a `projects` table with repo names, descriptions, and last-updated dates
- The notebook queries this DuckDB database and displays projects sorted by most recently updated
- Built using [Observable Notebook Kit](https://observablehq.com/notebook-kit/kit) and deployed via GitHub Actions
