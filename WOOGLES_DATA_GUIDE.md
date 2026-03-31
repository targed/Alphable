# Woogles Data Collection Guide

This repository includes tools for fetching and processing game data from Woogles.io.

## Quick Start

### 1. Fetch Game Metadata

Get basic information about games (no moves):

```bash
# Fetch 500 most recent games for a user
python fetch_more_games.py BestBot

# Fetch all available games
python fetch_more_games.py BasicBot -n 10000

# Specify output file
python fetch_more_games.py BasicBot -o my_games.json
```

### 2. Fetch Full Game Data (GCG Format)

Get complete game data including all moves:

```bash
# Fetch GCG files for games in woogles.json
python fetch_gcg_data.py

# Use a different metadata file
python fetch_gcg_data.py my_games.json

# Adjust delay between API calls (default: 0.1s)
python fetch_gcg_data.py woogles.json 0.2
```

GCG files are saved to `data/gcg/` directory.

### 3. Filter Games

Filter existing metadata by various criteria:

```bash
# Show example filters
python filter_games.py woogles.json

# From the unified tool:
python woogles_data_tool.py filter woogles.json -o filtered.json \
    --min-rating 1800 \
    --lexicon CSW24 \
    --bot-only \
    --max-margin 50
```

Available filters:

- `--min-rating`, `--max-rating`: Rating range
- `--lexicon`: Lexicon(s) like CSW24, NWL23
- `--bot-only`, `--human-only`: Game type
- `--tournament-only`, `--casual-only`: Tournament vs casual
- `--variant`: Game variant (classic, wordsmog, etc.)
- `--time-control`: Time control type
- `--min-margin`, `--max-margin`: Score margin (point difference)

### 4. Process Data

Convert GCG files to structured formats for analysis:

```bash
# Process all GCG files
python process_games.py

# Specify directories
python process_games.py --gcg-dir data/gcg --metadata woogles.json

# Customize output files
python process_games.py --csv games.csv --json games.json --training training.jsonl
```

Output formats:

- **CSV**: Summary format (game_id, players, scores, metadata)
- **JSON**: Detailed format with all moves and metadata
- **JSONL**: Training dataset format (one game per line)

## Unified CLI Tool

The `woogles_data_tool.py` script combines all functionality:

### Commands

#### fetch-metadata

Fetch game metadata with pagination:

```bash
python woogles_data_tool.py fetch-metadata BasicBot -n 2000 -o all_games.json
```

#### fetch-gcg

Fetch GCG move data:

```bash
python woogles_data_tool.py fetch-gcg -m woogles.json -o data/gcg
```

#### filter

Filter games by criteria:

```bash
python woogles_data_tool.py filter woogles.json -o filtered.json \
    --min-rating 2000 \
    --lexicon CSW24 \
    --bot-only
```

#### process

Process GCG files:

```bash
python woogles_data_tool.py process -g data/gcg -m woogles.json
```

#### pipeline

Run everything in sequence:

```bash
# Full pipeline: fetch -> filter -> get GCG -> process
python woogles_data_tool.py pipeline BasicBot \
    -n 1000 \
    --min-rating 1800 \
    --lexicon CSW24 \
    --bot-only \
    -d 0.15
```

## Complete Example Workflow

### Example 1: Collect high-level bot games

```bash
# Get 2000 games, filter to high-level, fetch GCG, process
python woogles_data_tool.py pipeline BasicBot \
    -n 2000 \
    --min-rating 1900 \
    --bot-only \
    -o high_level_games.json
```

This will create:

- `high_level_games.json` - Metadata for all games
- `high_level_games_filtered.json` - Filtered metadata
- `data/gcg/*.gcg` - Individual GCG files
- `data/games_processed.csv` - Summary CSV
- `data/games_processed.json` - Detailed JSON with moves
- `data/training_dataset.jsonl` - Training format

### Example 2: Manual step-by-step

```bash
# Step 1: Fetch metadata
python fetch_more_games.py BasicBot -n 5000 -o all_games.json

# Step 2: Filter to CSW24 games only
python woogles_data_tool.py filter all_games.json \
    -o csw24_games.json \
    --lexicon CSW24

# Step 3: Fetch GCG data
python fetch_gcg_data.py csw24_games.json 0.15

# Step 4: Process into structured formats
python process_games.py --gcg-dir data/gcg --metadata csw24_games.json
```

### Example 3: Analyze close games

```bash
# Find close games (decided by 30 points or less)
python woogles_data_tool.py filter woogles.json \
    -o close_games.json \
    --max-margin 30

# Fetch and process just those games
python fetch_gcg_data.py close_games.json
python process_games.py --metadata close_games.json
```

## Data Formats

### GCG Format

Raw game notation with moves:

```
#player1 Player1Name 1500
#player2 Player2Name 1600
>Player1Name: AEINSTT H8 ENTASIA 76 76
>Player2Name: DEGLORU 8D GOURDE. 18 18
...
```

### CSV Format (Summary)

```csv
game_id,lexicon,player1,player2,num_moves,final_score_p1,final_score_p2,winner,rating_mode,time_control
abc123,CSW24,Player1,Player2,45,412,389,0,RATED,regular
```

### JSON Format (Detailed)

```json
{
  "game_id": "abc123",
  "lexicon": "CSW24",
  "players": ["Player1", "Player2"],
  "moves": [
    {
      "player": "Player1",
      "rack": "AEINSTT",
      "position": "H8",
      "word": "ENTASIA",
      "score": 76,
      "cumulative": 76
    }
  ],
  "final_scores": [412, 389],
  "metadata": {...}
}
```

### JSONL Format (Training)

One game per line, suitable for ML training pipelines.

## API Key

The scripts use an API key defined in the source files. To use your own:

1. Get an API key from https://woogles.io (Settings menu)
2. Update the `API_KEY` variable in:
   - `getWooglesData.py`
   - `fetch_gcg_data.py`
   - `fetch_more_games.py`

## Rate Limiting

The scripts include delays between API calls to respect rate limits:

- Metadata fetching: 0.2s delay (default)
- GCG fetching: 0.1s delay (default)

Adjust with `-d` or `--delay` parameter if needed.

## Resumable Downloads

The GCG fetcher automatically skips files that already exist, so you can resume interrupted downloads.

## Tips

1. **Start small**: Test with a few games before fetching thousands
2. **Filter early**: Apply filters before fetching GCG data to save time
3. **Use pipeline**: For most use cases, the `pipeline` command does everything
4. **Check disk space**: GCG files are ~1-2KB each, so 10,000 games = ~20MB

## Troubleshooting

**No games fetched**: Check API key is valid
**Rate limiting errors**: Increase delay between requests
**Missing GCG files**: Some games may not be available, check error output
