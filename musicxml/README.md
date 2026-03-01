# MusicXML Files

This folder contains MusicXML files for the Sound First curriculum.

## Structure

- `index.json` - Metadata index for all files (required for seeding to database)
- `*.musicxml` - The actual MusicXML score files

## Two Types of Metadata

| Type | Source | Purpose |
|------|--------|---------|
| **Human-curated** | `index.json` | Teaching intent, category, source, focus cards, difficulty |
| **Auto-extracted** | music21 analyzer | Actual notes, rhythms, intervals, range, capabilities present |

The seed script merges both: human intent + machine analysis.

## Adding New Files

1. Add your `.musicxml` file to this folder
2. Copy the template entry in `index.json` and fill in the human-curated fields
3. Run `python -m app.seed_data` to:
   - Analyze the file with music21 (populates `_extracted_by_music21`)
   - Load into SQLite database

## Key Concepts

### Capabilities: Required vs Teaching vs Incidental

| Type | Meaning | Example |
|------|---------|---------|
| **Required** | User MUST know before attempting | `cap_clef_treble_known` for any treble clef music |
| **Teaching** | We TEACH alongside this piece (mini-lesson) | `cap_articulation_staccato_known` if that's the focus |
| **Incidental** | Present in score but not our focus | Dynamics that happen to be there but we're teaching rhythm |

### Pitch Reference Types

| Type | Use Case | Example |
|------|----------|---------|
| **TONAL** | Piece has a key center | "Autumn Leaves" in G minor |
| **ANCHOR_INTERVAL** | Pattern-based, no fixed key | "Do-Re-Do" = [0, +2, 0] semitones from any starting pitch |

ANCHOR_INTERVAL is for exercises where the *pattern* matters, not the key. A "Do-Re-Do" exercise can start on any note - we're teaching the interval relationship, not a specific key.

### Interval Tracking

Instead of tracking 24+ individual interval capabilities per user, we use a **progressive interval range**:

- Each material has a `largest_interval` field (e.g., "P5", "M6", "P8")
- Each user has a `max_melodic_interval` field that expands as they learn
- Materials are eligible when `user.max_melodic_interval >= material.largest_interval`

**Interval order (smallest to largest):**
```
m2 → M2 → m3 → M3 → P4 → A4 → P5 → m6 → M6 → m7 → M7 → P8
```

Users start with M2 (major 2nd / whole step) and progressively expand.
When teaching a new interval, we teach it in **both directions** before expanding further.

### Pitch Language

Describes the harmonic/melodic system:
- `tonal` - Traditional major/minor keys
- `modal` - Dorian, mixolydian, etc.
- `chromatic` - Uses all 12 pitches freely
- `atonal` / `serial` - No tonal center, 12-tone rows
- `blues` / `pentatonic` - Blues scale, pentatonic patterns

### Transposition

- **disallowed_keys**: Keys that don't work (rare - most pieces work in all keys)
- **preferred_keys**: Keys that work especially well
- Spelling (F# vs Gb) is handled at runtime with user toggle, not stored

## Focus Cards

Each material can specify:
- `recommended`: Focus cards that pair well
- `always_include`: Focus cards always offered for this material

## Category Reference

| Category | Description |
|----------|-------------|
| `tune` | Complete melody/song |
| `excerpt` | Orchestral or solo excerpt |
| `etude` | Study piece with musical context |
| `technical_exercise` | Focused on specific technique |
| `scale_pattern` | Scale or arpeggio patterns |
| `warmup` | Daily warm-up routine material |
| `long_tone` | Sustained note exercises |
| `lip_slur` | Flexibility/slur exercises |
| `articulation_study` | Tonguing patterns |
| `sight_reading` | New material for reading practice |
| `improvisation_template` | Framework for improvisation practice |
