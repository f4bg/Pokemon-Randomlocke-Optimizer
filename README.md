# Pokemon Team Optimizer

A self-contained web application for managing your Pokemon team during randomized or nuzlocke playthroughs. Track caught Pokemon, manage items, control level caps, and optimize your team — all with a bilingual (English/Spanish) single-page interface.

## Features

- **Team Management** – Add/remove caught Pokemon with nicknames and regional forms (Alolan, Galarian, Hisuian)
- **Level Cap System** – Set a level cap with preset gym-leader-style limits to simulate level restrictions
- **Evolution Tracking** – See which evolutions are available based on your level cap and items; evolve individually or all at once
- **Team Optimization** – View your best 6 Pokemon sorted by total stats or by a specific stat
- **Pokemon Comparison** – Compare two Pokemon side-by-side with stat bars and type matchup charts
- **Item Inventory** – Manage evolution items (stones, trade items, etc.)
- **Save/Backup System** – Create named save states, restore or delete them
- **Bilingual UI** – Toggle between English and Spanish in-app
- **Live Sprites** – Pokemon sprites fetched from PokeAPI

## Requirements

- Python 3.13+
- Flask
- requests

```
pip install flask requests
```

## Usage

```
python app.py
```

Open http://localhost:5000 in your browser.

### Build standalone executable

```
pip install pyinstaller
pyinstaller app.spec
```

The executable will be placed in `dist/app.exe`.

## Data Files

| File | Purpose |
|---|---|
| `Pokemon.csv` | Master Pokemon database with stats and forms |
| `pokemon_evoluciones.csv` | Evolution relationships and methods |
| `items.csv` | Item catalog |
| `Pokemon Type Chart.csv` | 18x18 type effectiveness matrix |
| `caught.json` | Runtime state — your caught Pokemon |
| `items.json` | Runtime state — your inventory |
| `config.json` | Runtime state — current level cap |

## Project Structure

```
├── app.py                     # Flask server with all API routes
├── templates/index.html       # Single-page frontend (HTML/CSS/JS)
├── types/                     # Type icon images
├── saves/                     # Backup save files
├── otherscript/               # Development/utility scripts
└── app.spec                   # PyInstaller build spec
```

## API

All API endpoints are under `/api/` and return JSON. Key endpoints include:

- `GET /api/pokemon` – Search Pokemon database
- `GET/POST /api/caught` – List or add caught Pokemon
- `GET /api/team/best` – Best team by total stats
- `GET /api/evolutions/available` – Available evolutions
- `POST /api/evolve` – Evolve a Pokemon
- `POST /api/evolve-all` – Evolve all level-based evolutions
- `GET/POST /api/level-cap` – Get or set level cap
- `GET /api/compare?pokemon1=X&pokemon2=Y` – Compare two Pokemon
- `GET /api/backups` – List backups
- `POST /api/backups/save` – Create a named backup

## License

MIT
