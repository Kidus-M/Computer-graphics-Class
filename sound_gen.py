import math
import struct
import random
import pygame

class SoundGenerator:
    """Generates procedural sounds without external assets"""
    def __init__(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception as e:
            print(f"Sound init failed: {e}")
            self.enabled = False
            return

        self.sounds = {}
        self.generate_sounds()

    def generate_wave(self, duration, freq_start, freq_end, decay=True, volume=0.5):
        # Generate raw audio data
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = bytearray()
        
        for i in range(n_samples):
            t = float(i) / sample_rate
            # Frequency sweep
            f = freq_start + (freq_end - freq_start) * (t / duration)
            # Sine wave
            val = math.sin(2 * math.pi * f * t)
            
            # Envelope (decay)
            if decay:
                env = 1.0 - (t / duration)
                env = env ** 2  # quadratic decay
                val *= env
            
            val *= volume * 32767
            
            # Angle for stereo (center)
            frame = struct.pack('<hh', int(val), int(val))
            buf.extend(frame)
            
        return pygame.mixer.Sound(buffer=buf)

    def generate_sounds(self):
        if not self.enabled: return
        
        # Paddle hit (higher pitch, sharp)
        self.sounds['paddle_hit'] = self.generate_wave(0.1, 440, 200, volume=0.6)
        
        # Table bounce (lower pitch, duller)
        self.sounds['table_hit'] = self.generate_wave(0.08, 200, 100, volume=0.4)
        
        # Score / Win (simple chord-like chirp)
        self.sounds['score'] = self.generate_wave(0.3, 880, 440, volume=0.5)

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
