# Quick Start: Woogles Data Collection

## What You Have

✅ **All 4 capabilities implemented:**

1. **Fetch Full Game Moves (GCG)** - `fetch_gcg_data.py`
2. **Pagination Support** - `fetch_more_games.py`
3. **Game Filtering** - `filter_games.py`
4. **Data Processing** - `process_games.py`

Plus: **Unified CLI** - `woogles_data_tool.py`

## Fastest Way to Get Started

### Option 1: Use Your Existing Data (500 games already fetched!)

```bash
# You already have 500 games in woogles.json!
# Just fetch the GCG files and process them:

# 1. Fetch GCG data for all 500 games (~50 seconds with 0.1s delay)
python fetch_gcg_data.py woogles.json 0.1

# 2. Process into structured formats
python process_games.py
```

This creates:
- `data/gcg/*.gcg` - 500 GCG files with full game moves
- `data/games_processed.csv` - Summary CSV
- `data/games_processed.json` - Detailed JSON with all moves
- `data/training_dataset.jsonl` - ML training format

### Option 2: Full Pipeline with Filtering

```bash
# Fetch, filter, and process in one command
python woogles_data_tool.py pipeline BasicBot \
    -n 1000 \
    --min-rating 1800 \
    --lexicon CSW24
```

### Option 3: Custom Workflow

```bash
# 1. Fetch more games
python fetch_more_games.py SomeUser -n 2000 -o more_games.json

# 2. Filter to what you want
python woogles_data_tool.py filter more_games.json -o filtered.json \
    --min-rating 2000 \
    --bot-only

# 3. Get GCG data
python fetch_gcg_data.py filtered.json

# 4. Process
python process_games.py --metadata filtered.json
```

## Current Status

- ✅ 500 games metadata already fetched (woogles.json)
- ✅ 45 GCG files fetched (data/gcg/)
- ✅ Processed demo with 45 games
- ✅ All tools tested and working

## Next Steps

Run this to fetch GCG for all your existing 500 games:
```bash
python fetch_gcg_data.py woogles.json 0.1
```

See `WOOGLES_DATA_GUIDE.md` for detailed documentation!
