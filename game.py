"""
3D Air Hockey
=============
Features:
- Planar Physics (Drift, Friction)
- 3D Mallets and Puck
- AI Opponent
- Wall Bouncing & Goal Detection
- Particle Effects for Goals/Hits

Controls:
    Player 1 (Bottom): Mouse to move (or WASD)
    Player 2 (Top): AI
    R: Reset
    Esc: Quit
"""

import math
import random
import sys
import os
import ctypes
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Try importing sound
try:
    from sound_gen import SoundGenerator
except ImportError:
    SoundGenerator = None

# ============================================================================
# CONSTANTS
# ============================================================================

# Table: 8ft Air Hockey Table approx 2.4m x 1.2m
# We scale up for visibility
TABLE_W = 6.0   # Width (X)
TABLE_L = 10.0  # Length (Z)
TABLE_H = 0.0   # Height (Y)
WALL_H = 0.3    # Wall Height

GOAL_W = 2.5    # Goal Opening Width

# Physics
FRICTION = 0.99
RESTITUTION_WALL = 0.8
RESTITUTION_PUCK = 0.9

# Dimensions
PUCK_RADIUS = 0.4
PUCK_HEIGHT = 0.15

MALLET_RADIUS = 0.6
MALLET_HEIGHT = 0.5

# Game Rules
WIN_SCORE = 7

# Camera
CAM_OFFSET = (0, -15, -12)
CAM_ROT = (50, 0, 0) # High angle

# ============================================================================
# HELPER CLASSES
# ============================================================================

class Particle:
    def __init__(self, x, y, z, color):
        self.x, self.y, self.z = x, y, z
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(2, 8)
        self.vz = random.uniform(-5, 5)
        self.life = 1.0
        self.color = color
        
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.vy -= 20.0 * dt # Gravity
        self.life -= dt
        
    def draw(self, quadric):
        if self.life <= 0: return
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glColor4f(*self.color, self.life)
        gluSphere(quadric, 0.08, 4, 4)
        glPopMatrix()

# ============================================================================
# GAME ENTITIES
# ============================================================================

class Puck:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.x = 0.0
        self.y = TABLE_H + PUCK_HEIGHT/2
        self.z = 0.0
        self.vx = 0.0
        self.vz = 0.0
        # Serve random
        if random.random() > 0.5:
            self.vz = random.uniform(5, 8)
            self.vx = random.uniform(-4, 4)
        else:
            self.vz = random.uniform(-8, -5)
            self.vx = random.uniform(-4, 4)
            
    def update(self, dt):
        # Move
        self.x += self.vx * dt
        self.z += self.vz * dt
        
        # Friction
        self.vx *= FRICTION
        self.vz *= FRICTION
        
        # Wall Collisions (X)
        limit_x = TABLE_W - PUCK_RADIUS
        if self.x > limit_x:
            self.x = limit_x
            self.vx *= -RESTITUTION_WALL
            return 'wall'
        elif self.x < -limit_x:
            self.x = -limit_x
            self.vx *= -RESTITUTION_WALL
            return 'wall'

        # End Walls (Z) - Check if NOT in goal
        limit_z = TABLE_L - PUCK_RADIUS
        
        # Goal Check happens in Game loop usually, but wall bounce here
        # Simple Wall bounce if outside Goal Width
        if abs(self.x) > GOAL_W/2:
            if self.z > limit_z:
                self.z = limit_z
                self.vz *= -RESTITUTION_WALL
                return 'wall'
            elif self.z < -limit_z:
                self.z = -limit_z
                self.vz *= -RESTITUTION_WALL
                return 'wall'
                
        return None

    def draw(self, quadric):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(90, 1, 0, 0)
        
        # Body
        glColor3f(0.8, 0.2, 0.2) # Red Puck
        gluCylinder(quadric, PUCK_RADIUS, PUCK_RADIUS, PUCK_HEIGHT, 16, 1)
        
        # Top/Bottom Caps
        gluDisk(quadric, 0, PUCK_RADIUS, 16, 1)
        glPushMatrix()
        glTranslatef(0, 0, PUCK_HEIGHT)
        gluDisk(quadric, 0, PUCK_RADIUS, 16, 1)
        glPopMatrix()
        
        glPopMatrix()

class Mallet:
    def __init__(self, is_player, z_start, color):
        self.is_player = is_player
        self.x = 0
        self.y = TABLE_H 
        self.z = z_start
        self.color = color
        
        # Physics
        self.vx = 0
        self.vz = 0
        self.last_x = 0
        self.last_z = z_start
        self.speed = 20.0
        
        # Bounds (Half table)
        if z_start > 0: # Top player (Positive Z)
            self.min_z, self.max_z = 0.5, TABLE_L - MALLET_RADIUS
        else: # Bottom player (Negative Z)
            self.min_z, self.max_z = -TABLE_L + MALLET_RADIUS, -0.5

    def update(self, dt, target_pos=None):
        self.last_x, self.last_z = self.x, self.z
        
        if self.is_player:
            # Mouse Control or Keyboard
            keys = pygame.key.get_pressed()
            dx = 0
            dz = 0
            if keys[K_a] or keys[K_LEFT]: dx -= 1
            if keys[K_d] or keys[K_RIGHT]: dx += 1
            if keys[K_w] or keys[K_UP]: dz -= 1
            if keys[K_s] or keys[K_DOWN]: dz += 1
            
            # Normalize
            if dx!=0 or dz!=0:
                mag = math.sqrt(dx*dx + dz*dz)
                dx /= mag
                dz /= mag
                
            self.x += dx * self.speed * dt
            self.z += dz * self.speed * dt
            
        else:
            # AI Logic
            if target_pos:
                tx, tz = target_pos
                
                # AI Speed limit
                diff_x = tx - self.x
                diff_z = tz - self.z
                
                # Move towards target
                self.x += diff_x * 8.0 * dt
                self.z += diff_z * 8.0 * dt
                
                # Defense home position if puck is far
                # (Simple AI implementation)
        
        # Clamp bounds
        limit_x = TABLE_W - MALLET_RADIUS
        self.x = max(-limit_x, min(limit_x, self.x))
        self.z = max(self.min_z, min(self.max_z, self.z))
        
        # Calculate Velocity (for collision impulse)
        self.vx = (self.x - self.last_x) / dt
        self.vz = (self.z - self.last_z) / dt

    def draw(self, quadric):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        glColor3f(*self.color)
        
        # Base
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, MALLET_RADIUS, MALLET_RADIUS, 0.4, 16, 1)
        glTranslatef(0, 0, 0.4)
        gluDisk(quadric, 0, MALLET_RADIUS, 16, 1)
        glPopMatrix()
        
        # Handle
        glPushMatrix()
        glTranslatef(0, 0.4, 0)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, 0.2, 0.2, 0.4, 8, 1)
        glTranslatef(0, 0, 0.4)
        gluDisk(quadric, 0, 0.2, 8, 1)
        glPopMatrix()
        
        glPopMatrix()

# ============================================================================
# MAIN GAME
# ============================================================================

class Game:
    def __init__(self, w=1280, h=720):
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        pygame.init()
        pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL | RESIZABLE)
        pygame.display.set_caption("3D Air Hockey")
        self.width, self.height = w, h
        
        self.init_gl()
        
        # Sound
        self.sound = None
        if SoundGenerator:
            self.sound = SoundGenerator()
            
        self.quadric = gluNewQuadric()
        
        self.start_game()
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Font for scores
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 40, bold=True)
        
    def init_gl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
        
        glLightfv(GL_LIGHT0, GL_POSITION, (5, 10, 5, 0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))
        
        self.resize(self.width, self.height)
        
    def resize(self, w, h):
        self.width, self.height = w, h
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 100)
        glMatrixMode(GL_MODELVIEW)
        
    def start_game(self):
        self.p1 = Mallet(True, -6.0, (0.2, 0.2, 0.9)) # Blue (User)
        self.p2 = Mallet(False, 6.0, (0.9, 0.2, 0.2)) # Red (AI)
        self.puck = Puck()
        self.scores = [0, 0]
        self.particles = []
        self.winner = None
        
    def check_collision(self, m, p):
        # Circle-Circle Collision
        dx = p.x - m.x
        dz = p.z - m.z
        dist = math.sqrt(dx*dx + dz*dz)
        min_dist = PUCK_RADIUS + MALLET_RADIUS
        
        if dist < min_dist:
            # Overlap!
            
            # 1. Resolve Position (Push Puck out)
            overlap = min_dist - dist
            nx = dx / dist # Normal
            nz = dz / dist
            
            p.x += nx * overlap
            p.z += nz * overlap
            
            # 2. Resolve Velocity (Elastic)
            # Relative velocity
            rvx = p.vx - m.vx
            rvz = p.vz - m.vz
            
            # Velocity along normal
            vel_along_normal = rvx * nx + rvz * nz
            
            # If moving apart, don't bounce
            if(vel_along_normal > 0): return
            
            j = -(1 + RESTITUTION_PUCK) * vel_along_normal
            # Assume equal mass for simplicity or infinite mass mallet
            # Impulse scalar
            
            p.vx += j * nx
            p.vz += j * nz
            
            # Add some mallet velocity transfer
            p.vx += m.vx * 0.5
            p.vz += m.vz * 0.5
            
            # Sound
            if self.sound: self.sound.play('mallet_hit')
            
            # Particles
            self.spawn_particles(p.x, p.y, p.z, 5, (1, 1, 0))
            
    def spawn_particles(self, x, y, z, n, col):
        for _ in range(n):
            self.particles.append(Particle(x, y, z, col))
            
    def update(self):
        dt = self.clock.tick(60) / 1000.0
        
        if self.winner: return
        
        # AI Target
        # AI targets puck if in his half (z > 0), else targets home (0, 6)
        ai_target = (self.puck.x, self.puck.z)
        if self.puck.z < 0: ai_target = (0, 5) # Defend center
        
        self.p1.update(dt)
        self.p2.update(dt, ai_target)
        
        res = self.puck.update(dt)
        if res == 'wall' and self.sound: self.sound.play('wall_hit')
        
        # Collisions
        self.check_collision(self.p1, self.puck)
        self.check_collision(self.p2, self.puck)
        
        # Goal Checks
        if self.puck.z > TABLE_L:
            self.goal(0) # P2 side (Top), P1 scores
        elif self.puck.z < -TABLE_L:
            self.goal(1) # P1 side (Bottom), P2 scores
            
        # Particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles: p.update(dt)
        
    def goal(self, scorer_idx):
        self.scores[scorer_idx] += 1
        if self.sound: self.sound.play('goal') 
        self.spawn_particles(self.puck.x, 2, self.puck.z, 20, (0, 1, 0))
        
        if self.scores[scorer_idx] >= WIN_SCORE:
            self.winner = f"PLAYER {scorer_idx+1} WINS!"
        else:
            self.puck.reset()
            
    def draw_world(self):
        # Table Floor
        glColor3f(0.9, 0.9, 0.95) # Ice White
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-TABLE_W, 0, -TABLE_L)
        glVertex3f(TABLE_W, 0, -TABLE_L)
        glVertex3f(TABLE_W, 0, TABLE_L)
        glVertex3f(-TABLE_W, 0, TABLE_L)
        glEnd()
        
        # Walls (Red)
        glColor3f(0.8, 0.1, 0.1)
        h = WALL_H
        w = 0.2
        # Left Wall
        glPushMatrix(); glTranslatef(-TABLE_W-w/2, h/2, 0); glScalef(w, h, TABLE_L*2); self.box(); glPopMatrix()
        # Right Wall
        glPushMatrix(); glTranslatef(TABLE_W+w/2, h/2, 0); glScalef(w, h, TABLE_L*2); self.box(); glPopMatrix()
        # Top Wall (Split for Goal)
        # Left part
        glPushMatrix(); glTranslatef(-TABLE_W/2 - GOAL_W/2, h/2, -TABLE_L-w/2); glScalef(TABLE_W - GOAL_W/2, h, w); self.box(); glPopMatrix()
        # Right part
        glPushMatrix(); glTranslatef(TABLE_W/2 + GOAL_W/2, h/2, -TABLE_L-w/2); glScalef(TABLE_W - GOAL_W/2, h, w); self.box(); glPopMatrix()
        
        # Bottom Wall (Split)
        glPushMatrix(); glTranslatef(-TABLE_W/2 - GOAL_W/2, h/2, TABLE_L+w/2); glScalef(TABLE_W - GOAL_W/2, h, w); self.box(); glPopMatrix()
        glPushMatrix(); glTranslatef(TABLE_W/2 + GOAL_W/2, h/2, TABLE_L+w/2); glScalef(TABLE_W - GOAL_W/2, h, w); self.box(); glPopMatrix()
        
        # Markings (Lines)
        glDisable(GL_LIGHTING)
        glColor3f(1, 0, 0) # Center Line
        glLineWidth(3)
        glBegin(GL_LINES)
        glVertex3f(-TABLE_W, 0.05, 0); glVertex3f(TABLE_W, 0.05, 0)
        glEnd()
        
        # Circle
        glPushMatrix()
        glTranslatef(0, 0.05, 0)
        glRotatef(90, 1, 0, 0)
        self.draw_circle(2.0)
        glPopMatrix()
        glEnable(GL_LIGHTING)

    def draw_circle(self, r):
        glBegin(GL_LINE_LOOP)
        for i in range(32):
            th = 2 * math.pi * i / 32
            glVertex2f(r*math.cos(th), r*math.sin(th))
        glEnd()

    def box(self):
        glutSolidCube(1.0) if 'glutSolidCube' in globals() else self.draw_cube_arrays()

    def draw_cube_arrays(self):
        glBegin(GL_QUADS)
        # Top
        glNormal3f(0,1,0); glVertex3f(-0.5, 0.5, 0.5); glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, 0.5, -0.5); glVertex3f(-0.5, 0.5, -0.5)
        # Front
        glNormal3f(0,0,1); glVertex3f(-0.5, -0.5, 0.5); glVertex3f(0.5, -0.5, 0.5); glVertex3f(0.5, 0.5, 0.5); glVertex3f(-0.5, 0.5, 0.5)
        # ... (Abbreviated, relying on glut mostly)
        glEnd()

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Camera
        glTranslatef(*CAM_OFFSET)
        glRotatef(CAM_ROT[0], 1, 0, 0)
        
        self.draw_world()
        self.p1.draw(self.quadric)
        self.p2.draw(self.quadric)
        self.puck.draw(self.quadric)
        
        for p in self.particles: p.draw(self.quadric)
        
        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self):
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
        
        # Scores
        s = f"{self.scores[0]} : {self.scores[1]}"
        surf = self.font.render(s, True, (0, 0, 0))
        data = pygame.image.tostring(surf, 'RGBA', True)
        w, h = surf.get_size()
        
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glRasterPos2i(self.width//2 - w//2, 50)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)
        
        if self.winner:
            ws = self.font.render(self.winner, True, (50, 200, 50))
            data = pygame.image.tostring(ws, 'RGBA', True)
            w2, h2 = ws.get_size()
            glRasterPos2i(self.width//2 - w2//2, self.height//2)
            glDrawPixels(w2, h2, GL_RGBA, GL_UNSIGNED_BYTE, data)

        glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

    def run(self):
        while self.running:
            self.update()
            self.render()
            for e in pygame.event.get():
                if e.type == QUIT: self.running = False
                elif e.type == KEYDOWN and e.key == K_ESCAPE: self.running = False
                elif e.type == KEYDOWN and e.key == K_r: self.start_game()
                elif e.type == VIDEORESIZE: self.resize(e.w, e.h)

if __name__ == "__main__":
    g = Game()
    g.run()