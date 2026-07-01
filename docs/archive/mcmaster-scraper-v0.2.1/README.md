# Vendored `mcmaster-scraper`

Full upstream source from [thedjchi/mcmaster-scraper](https://github.com/thedjchi/mcmaster-scraper) (MIT), vendored in-tree — **not** installed from PyPI.

| Field | Value |
|-------|-------|
| Upstream version | See `VERSION` |
| Upstream commit | See `UPSTREAM_COMMIT` |
| Package path | `vendor/mcmaster_scraper/mcmaster_scraper/` |
| License | `LICENSE` (MIT, Copyright thedjchi) |

## Usage in this repo

```python
from mcmaster_scraper.sync_api import get_products_from_url
from mcmaster_scraper.async_api import get_products_from_url as aget_products_from_url

df = get_products_from_url("https://www.mcmaster.com/products/screws/socket-head-screws-2~/...")
```

Bridge module: `backend.services.vendors.mcmaster.scraper_bridge`

- `get_products_table_from_json()` normalizes string JSON keys to ints before calling upstream `table_parser` (live API compatibility).

Example script: `scripts/mcmaster_scraper_example.py`  
Test notebook: `notebooks/vendor/01_mcmaster_scraper.ipynb`

## Dependencies

Requires the `[playwright]` extra (`pip install -e '.[playwright]'`) and `playwright install chromium`.

Upstream also uses `diskcache`, `platformdirs`, and `playwright-stealth` (listed in our `pyproject.toml`).

## Updating from upstream

```bash
git clone https://github.com/thedjchi/mcmaster-scraper.git /tmp/mcmaster-scraper
cp -R /tmp/mcmaster-scraper/src/mcmaster_scraper vendor/mcmaster_scraper/
cp /tmp/mcmaster-scraper/docs/example.py vendor/mcmaster_scraper/docs/
# Re-record VERSION and UPSTREAM_COMMIT; run tests
```

The upstream repo has **no Jupyter notebooks** — only `docs/example.py`. Our `vendor/01_mcmaster_scraper.ipynb` exercises the vendored package in this repo.
