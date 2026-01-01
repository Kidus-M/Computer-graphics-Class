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
        
        # Mallet Hit (Sharp plastic 'tock')
        self.sounds['mallet_hit'] = self.generate_wave(0.05, 800, 100, volume=0.8)
        
        # Wall Hit (High click)
        self.sounds['wall_hit'] = self.generate_wave(0.03, 1200, 800, volume=0.4)
        
        # Goal Horn (Buzz)
        self.sounds['goal'] = self.generate_wave(1.5, 150, 100, decay=False, volume=0.7)
        
        # Score point (Short beep)
        self.sounds['score'] = self.generate_wave(0.2, 600, 900, volume=0.5)

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
