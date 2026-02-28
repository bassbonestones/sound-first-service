# Soundfonts Directory

This directory holds SoundFont (.sf2) files for audio rendering.

## How to Get a Soundfont

### Option 1: GeneralUser GS (Recommended)
Free, high-quality General MIDI soundfont (51 MB):
1. Download from: https://schristiancollins.com/generaluser.php
2. Rename to `GeneralUser_GS.sf2`
3. Place in this directory

### Option 2: FluidR3 GM
Full General MIDI soundfont (141 MB):
1. Download from: https://packages.debian.org/bullseye/all/fluid-soundfont-gm/download
2. Extract and place `FluidR3_GM.sf2` here

### Option 3: Instrument-Specific Soundfonts
For higher quality instrument-specific audio:
- `trumpet.sf2` - Trumpet soundfont
- `flute.sf2` - Flute soundfont
- etc.

The system will look for instrument-specific files first, then fall back to the default.

## FluidSynth Requirement

midi2audio uses FluidSynth for audio rendering. Install it:

### Windows
```
winget install FluidSynth.FluidSynth
```
Or download from: https://github.com/FluidSynth/fluidsynth/releases

### macOS
```
brew install fluidsynth
```

### Linux
```
apt install fluidsynth
```

## Testing

Check if audio rendering is working:
```
curl http://localhost:8000/audio/status
```

Should return:
```json
{
  "music21_available": true,
  "midi2audio_available": true,
  "soundfont_found": true,
  "can_render_audio": true
}
```
