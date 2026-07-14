# Golden BOM fixtures

Each subdirectory is one case:

- `input.txt` — raw MakerWorld-style description / BOM prose
- `expected.json` — locked parse truth (`original_name`, `quantity`, `specification`)

`tests/test_golden_boms.py` scores parser output at 100% name+qty match.
Add cases here when expanding MakerWorld diversity; regenerate expected only with intentional parser changes.
