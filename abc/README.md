# ABC Tune Library

This folder contains tunes authored in ABC notation for the Sound First TuneMastery feature.

## Folder Structure

| Folder                | Difficulty | Description                                 |
| --------------------- | ---------- | ------------------------------------------- |
| `beginner/`           | 1          | Simplest tunes (3-5 notes, stepwise motion) |
| `elementary/`         | 2          | Simple folk songs, limited range            |
| `early_intermediate/` | 3          | More complex melodies, larger intervals     |
| `intermediate/`       | 4          | Jazz standards intro, chromatic passages    |
| `late_intermediate/`  | 5          | Complex jazz & classical excerpts           |
| `advanced/`           | 6          | Virtuosic repertoire                        |

## ABC Conventions

### Storage Keys (No Accidentals)

All tunes are stored in keys with no sharps or flats:

| Mode            | Storage Key | Example                     |
| --------------- | ----------- | --------------------------- |
| Major (Ionian)  | C           | G major → C major           |
| Minor (Aeolian) | Am          | E minor → A minor           |
| Dorian          | Dm          | G dorian → D dorian         |
| Phrygian        | Em          | A phrygian → E phrygian     |
| Lydian          | F           | G lydian → F lydian         |
| Mixolydian      | G           | D mixolydian → G mixolydian |
| Locrian         | Bm          | F# locrian → B locrian      |

### Original Key Metadata

- If a tune has a **traditional/canonical key**, author it in that key
- The converter transposes to the storage key and adds: `<!-- original_key_center: G -->`
- If a tune has **no canonical key** (e.g., "Hot Cross Buns"), author directly in C - no metadata added

### Required Fields

```abc
X:1               % Tune number
T:Title           % Tune title (must match DEFAULT_TUNES)
M:4/4             % Time signature
L:1/4             % Default note length
Q:1/4=100         % Tempo (optional but recommended)
K:C               % Key (original if canonical, else C/Am)
```

### File Naming

- Use snake_case: `hot_cross_buns.abc`
- Match tune title to DEFAULT_TUNES exactly

## Workflow

1. Create ABC file in appropriate difficulty folder
2. Run converter: `python -m tools.abc_to_musicxml abc/beginner/tune.abc --output-dir resources/materials/pending/`
3. Start service and open GenerationPreviewScreen → Tunes tab
4. Select converted file, verify notation/playback/capabilities
5. If validated, move to `resources/materials/` for ingestion

## Batch Conversion

```bash
# Convert all ABC files
python -m tools.abc_to_musicxml abc/ --batch --output-dir resources/materials/pending/

# Dry run (list keys only)
python -m tools.abc_to_musicxml abc/**/*.abc --dry-run
```
