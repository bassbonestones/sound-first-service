#!/usr/bin/env python3
from music21 import note, stream, tempo, meter
import subprocess, os

# Test different trombone variants
variants = [
    ('SOLO_sustain', 'soundfonts/Virtual-Playing-Orchestra3/Brass/trombone-SOLO-sustain.sfz'),
    ('Bass_SOLO_sustain', 'soundfonts/Virtual-Playing-Orchestra3/Brass/bass-trombone-SOLO-sustain.sfz'),
]

for name, sfz_path in variants:
    print(f'Testing {name}...')
    
    # Create MIDI
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure()
    m.insert(0, tempo.MetronomeMark(number=60))
    m.insert(0, meter.TimeSignature('4/4'))
    n = note.Note('Bb3')
    n.quarterLength = 3.0
    n.volume.velocity = 100
    m.append(n)
    rest = note.Rest()
    rest.quarterLength = 1.0
    m.append(rest)
    p.append(m)
    s.append(p)
    midi_path = s.write('midi')
    
    wav_path = f'/tmp/test_{name}.wav'
    
    result = subprocess.run([
        'sfizz_render',
        '--sfz', sfz_path,
        '--midi', str(midi_path),
        '--wav', wav_path,
        '-s', '44100'
    ], capture_output=True, text=True)
    
    if result.returncode == 0 and os.path.exists(wav_path):
        print(f'  Created {wav_path} ({os.path.getsize(wav_path)} bytes)')
    else:
        print(f'  Failed: {result.stderr}')
    os.unlink(midi_path)

print("\nDone! Listen with:")
print("afplay /tmp/test_SOLO_sustain.wav")
print("afplay /tmp/test_Bass_SOLO_sustain.wav")
