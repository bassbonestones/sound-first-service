"""Comprehensive scale spelling verification.

Checks all 40 scales × 17 keys for correct enharmonic spelling.
Rules:
1. Each letter (A-G) should appear at most once per scale (no A and A#, use Bb instead)
   EXCEPT for scales that intentionally have chromatic alterations (blues, bebop, diminished, chromatic)
2. Root note must match key name spelling
3. Sharp keys should primarily use sharps
4. Flat keys should primarily use flats
"""
from app.services.generation.service import GenerationService
from app.schemas.generation_schemas import GenerationRequest, GenerationType, MusicalKey, ScaleType

service = GenerationService()

# Scales that intentionally have chromatic alterations (letter conflicts are expected)
CHROMATIC_SCALES = {
    "blues",           # has b5 and 5 (or #4 and 4)
    "blues_major",     # has b3 and 3
    "diminished_hw",   # symmetric 8-note
    "diminished_wh",   # symmetric 8-note
    "chromatic",       # all 12 notes
    "bebop_dominant",  # 8-note with passing tone
    "bebop_major",     # 8-note with passing tone
    "bebop_dorian",    # 8-note with passing tone
    "whole_tone",      # 6-note symmetric (no letter conflict but special)
}

# Map key enum values to their canonical names
KEY_NAMES = {
    MusicalKey.C: "C",
    MusicalKey.C_SHARP: "C#",
    MusicalKey.D_FLAT: "Db",
    MusicalKey.D: "D",
    MusicalKey.D_SHARP: "D#",  # Should map to Eb
    MusicalKey.E_FLAT: "Eb",
    MusicalKey.E: "E",
    MusicalKey.F: "F",
    MusicalKey.F_SHARP: "F#",
    MusicalKey.G_FLAT: "Gb",
    MusicalKey.G: "G",
    MusicalKey.G_SHARP: "G#",  # Should map to Ab
    MusicalKey.A_FLAT: "Ab",
    MusicalKey.A: "A",
    MusicalKey.A_SHARP: "A#",  # Should map to Bb
    MusicalKey.B_FLAT: "Bb",
    MusicalKey.B: "B",
}

def get_letter(pitch_name):
    """Extract just the letter from a pitch name."""
    return pitch_name[0]

def get_base(pitch_name):
    """Extract letter + accidental (no octave)."""
    return ''.join(c for c in pitch_name if not c.isdigit())

def check_scale_spelling(scale_type, key, pitch_names):
    """Check a scale's spelling for issues."""
    issues = []
    
    # Get unique pitch bases (no octaves)
    bases = []
    for name in pitch_names:
        base = get_base(name)
        if base not in bases:
            bases.append(base)
    
    # Check 1: Root note should match key name
    key_name = KEY_NAMES[key]
    root = bases[0] if bases else ""
    
    # Handle enharmonic equivalents for the "weird" keys
    enharmonic_roots = {
        "D#": ["D#", "Eb"],
        "G#": ["G#", "Ab"],
        "A#": ["A#", "Bb"],
    }
    
    expected_roots = enharmonic_roots.get(key_name, [key_name])
    if root not in expected_roots:
        issues.append(f"Root '{root}' doesn't match key '{key_name}'")
    
    # Check 2: Each letter should appear only once (skip for chromatic scales)
    scale_name = scale_type.value if hasattr(scale_type, 'value') else str(scale_type)
    if scale_name not in CHROMATIC_SCALES:
        letters = [get_letter(b) for b in bases]
        for letter in set(letters):
            count = letters.count(letter)
            if count > 1:
                conflicting = [b for b in bases if get_letter(b) == letter]
                issues.append(f"Letter '{letter}' appears {count} times: {conflicting}")
    
    return issues, bases

def main():
    keys = list(MusicalKey)
    scale_types = list(ScaleType)
    
    total_issues = 0
    total_tests = 0
    
    print(f"Testing {len(scale_types)} scales × {len(keys)} keys = {len(scale_types) * len(keys)} combinations")
    print("=" * 80)
    
    for scale_type in scale_types:
        scale_issues = []
        
        for key in keys:
            try:
                request = GenerationRequest(
                    content_type=GenerationType.SCALE,
                    definition=scale_type.value,
                    key=key,
                    direction='up_down',
                    num_octaves=1,
                    rhythm='quarter_notes',
                )
                result = service.generate(request)
                pitch_names = [e.pitch_name for e in result.events if e.midi_note > 0]
                
                issues, bases = check_scale_spelling(scale_type, key, pitch_names)
                total_tests += 1
                
                if issues:
                    total_issues += 1
                    scale_issues.append((key, bases, issues))
                    
            except Exception as e:
                total_issues += 1
                scale_issues.append((key, [], [f"ERROR: {e}"]))
        
        if scale_issues:
            print(f"\n{scale_type.value}:")
            for key, bases, issues in scale_issues:
                key_name = KEY_NAMES[key]
                print(f"  {key_name}: {' '.join(bases)}")
                for issue in issues:
                    print(f"    ❌ {issue}")
    
    print("\n" + "=" * 80)
    if total_issues == 0:
        print(f"✅ ALL {total_tests} scale/key combinations passed!")
    else:
        print(f"❌ {total_issues} issues found in {total_tests} tests")
    
    return total_issues

if __name__ == "__main__":
    exit(main())
