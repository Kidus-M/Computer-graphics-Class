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
    Player 1 (Bottom): WASD or Arrow Keys
    Player 2 (Top): AI Controlled
    R: Reset Game
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

# Table dimensions
TABLE_W = 5.0   # Half Width (X) - total width is 10
TABLE_L = 8.0   # Half Length (Z) - total length is 16
TABLE_H = 0.0   # Table surface height (Y)
WALL_H = 0.5    # Wall Height
WALL_THICK = 0.3

GOAL_W = 3.0    # Goal Opening Width (full width)

# Physics
FRICTION = 0.995
RESTITUTION_WALL = 0.85
RESTITUTION_PUCK = 0.95

# Dimensions
PUCK_RADIUS = 0.35
PUCK_HEIGHT = 0.12

MALLET_RADIUS = 0.5
MALLET_HEIGHT = 0.4

# Game Rules
WIN_SCORE = 7

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
        self.vy -= 20.0 * dt # Gravity for particles
        self.life -= dt
        
    def draw(self, quadric):
        if self.life <= 0: return
        glDisable(GL_LIGHTING)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glColor4f(*self.color, self.life)
        gluSphere(quadric, 0.08, 4, 4)
        glPopMatrix()
        glEnable(GL_LIGHTING)

# ============================================================================
# GAME ENTITIES
# ============================================================================

class Puck:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.x = 0.0
        self.y = TABLE_H + PUCK_HEIGHT/2 + 0.01
        self.z = 0.0
        self.vx = 0.0
        self.vz = 0.0
        # Random initial velocity
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 6)
        self.vx = math.cos(angle) * speed
        self.vz = math.sin(angle) * speed
            
    def update(self, dt):
        # Move
        self.x += self.vx * dt
        self.z += self.vz * dt
        
        # Friction
        self.vx *= FRICTION
        self.vz *= FRICTION
        
        # Wall Collisions (X - Side Walls)
        limit_x = TABLE_W - PUCK_RADIUS
        if self.x > limit_x:
            self.x = limit_x
            self.vx *= -RESTITUTION_WALL
            return 'wall'
        elif self.x < -limit_x:
            self.x = -limit_x
            self.vx *= -RESTITUTION_WALL
            return 'wall'

        # End Walls (Z) - Check if NOT in goal area
        limit_z = TABLE_L - PUCK_RADIUS
        
        # If puck is outside goal width, bounce off end wall
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
        
        # Puck body (Red)
        glColor3f(0.9, 0.1, 0.1)
        
        # Draw as cylinder laying flat
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)  # Rotate so cylinder is horizontal
        gluCylinder(quadric, PUCK_RADIUS, PUCK_RADIUS, PUCK_HEIGHT, 20, 1)
        # Bottom cap
        gluDisk(quadric, 0, PUCK_RADIUS, 20, 1)
        # Top cap
        glTranslatef(0, 0, PUCK_HEIGHT)
        gluDisk(quadric, 0, PUCK_RADIUS, 20, 1)
        glPopMatrix()
        
        glPopMatrix()

class Mallet:
    def __init__(self, is_player, z_start, color):
        self.is_player = is_player
        self.x = 0
        self.y = TABLE_H + MALLET_HEIGHT/2
        self.z = z_start
        self.color = color
        
        # Physics
        self.vx = 0
        self.vz = 0
        self.last_x = 0
        self.last_z = z_start
        self.speed = 15.0
        
        # Bounds (each player stays on their half)
        if z_start > 0: # Top player (Positive Z) - AI
            self.min_z, self.max_z = 0.5, TABLE_L - MALLET_RADIUS - 0.5
        else: # Bottom player (Negative Z) - Human
            self.min_z, self.max_z = -TABLE_L + MALLET_RADIUS + 0.5, -0.5

    def update(self, dt, target_pos=None):
        self.last_x, self.last_z = self.x, self.z
        
        if self.is_player:
            # Keyboard Control
            keys = pygame.key.get_pressed()
            dx = 0
            dz = 0
            if keys[K_a] or keys[K_LEFT]: dx += 1
            if keys[K_d] or keys[K_RIGHT]: dx -= 1
            if keys[K_w] or keys[K_UP]: dz += 1    # W moves forward (positive Z from player view)
            if keys[K_s] or keys[K_DOWN]: dz -= 1  # S moves backward
            
            # Normalize diagonal movement
            if dx != 0 or dz != 0:
                mag = math.sqrt(dx*dx + dz*dz)
                dx /= mag
                dz /= mag
                
            self.x += dx * self.speed * dt
            self.z += dz * self.speed * dt
            
        else:
            # AI Logic - Improved to avoid getting stuck
            if target_pos:
                tx, tz = target_pos
                
                # If puck is near side walls, AI should position to push it away from wall
                puck_near_left_wall = tx < -TABLE_W + 1.5
                puck_near_right_wall = tx > TABLE_W - 1.5
                
                # Aim slightly behind the puck (toward AI's goal) to push it forward
                target_z_offset = -0.8  # Stay behind puck to hit it forward
                
                # If puck is stuck near edge, push it toward center
                if puck_near_left_wall:
                    # Position to the left of puck to push it right
                    tx = tx - 0.5
                elif puck_near_right_wall:
                    # Position to the right of puck to push it left
                    tx = tx + 0.5
                
                diff_x = tx - self.x
                diff_z = (tz + target_z_offset) - self.z
                
                # Faster AI movement when chasing, slower when defending
                ai_speed = 8.0 if tz > 2 else 5.0
                self.x += diff_x * ai_speed * dt
                self.z += diff_z * ai_speed * dt
        
        # Clamp to bounds
        limit_x = TABLE_W - MALLET_RADIUS - 0.2
        self.x = max(-limit_x, min(limit_x, self.x))
        self.z = max(self.min_z, min(self.max_z, self.z))
        
        # Calculate Velocity (for collision impulse)
        if dt > 0:
            self.vx = (self.x - self.last_x) / dt
            self.vz = (self.z - self.last_z) / dt

    def draw(self, quadric):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        glColor3f(*self.color)
        
        # Base cylinder
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, MALLET_RADIUS, MALLET_RADIUS, MALLET_HEIGHT * 0.6, 20, 1)
        gluDisk(quadric, 0, MALLET_RADIUS, 20, 1)
        glTranslatef(0, 0, MALLET_HEIGHT * 0.6)
        gluDisk(quadric, 0, MALLET_RADIUS, 20, 1)
        glPopMatrix()
        
        # Handle (smaller cylinder on top)
        glPushMatrix()
        glTranslatef(0, MALLET_HEIGHT * 0.6, 0)
        glRotatef(-90, 1, 0, 0)
        glColor3f(0.3, 0.3, 0.3)  # Dark handle
        gluCylinder(quadric, 0.15, 0.15, MALLET_HEIGHT * 0.5, 12, 1)
        glTranslatef(0, 0, MALLET_HEIGHT * 0.5)
        gluDisk(quadric, 0, 0.15, 12, 1)
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
        self.font = pygame.font.SysFont('Arial', 48, bold=True)
        self.font_small = pygame.font.SysFont('Arial', 24)
        
    def init_gl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Main light (overhead)
        glLightfv(GL_LIGHT0, GL_POSITION, (0, 15, 0, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1, 1, 1, 1))
        
        # Fill light
        glLightfv(GL_LIGHT1, GL_POSITION, (5, 5, -10, 1))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.3, 0.3, 0.4, 1))
        
        glClearColor(0.1, 0.1, 0.15, 1.0)
        
        self.resize(self.width, self.height)
        
    def resize(self, w, h):
        self.width, self.height = w, h
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 200)
        glMatrixMode(GL_MODELVIEW)
        
    def start_game(self):
        self.p1 = Mallet(True, -5.0, (0.2, 0.4, 0.9))   # Blue (Human at bottom)
        self.p2 = Mallet(False, 5.0, (0.9, 0.3, 0.2))   # Red (AI at top)
        self.puck = Puck()
        self.scores = [0, 0]  # [Player1, Player2]
        self.particles = []
        self.winner = None
        
    def check_collision(self, m, p):
        # Circle-Circle Collision in XZ plane
        dx = p.x - m.x
        dz = p.z - m.z
        dist_sq = dx*dx + dz*dz
        min_dist = PUCK_RADIUS + MALLET_RADIUS
        
        if dist_sq < min_dist * min_dist and dist_sq > 0:
            dist = math.sqrt(dist_sq)
            
            # Normalize direction
            nx = dx / dist
            nz = dz / dist
            
            # Push puck out of mallet
            overlap = min_dist - dist
            p.x += nx * overlap
            p.z += nz * overlap
            
            # Relative velocity
            rvx = p.vx - m.vx
            rvz = p.vz - m.vz
            
            # Velocity along collision normal
            vel_along_normal = rvx * nx + rvz * nz
            
            # Only resolve if approaching
            if vel_along_normal < 0:
                # Impulse
                j = -(1 + RESTITUTION_PUCK) * vel_along_normal
                
                p.vx += j * nx
                p.vz += j * nz
                
                # Add mallet velocity influence
                p.vx += m.vx * 0.6
                p.vz += m.vz * 0.6
                
                # Cap speed
                speed = math.sqrt(p.vx*p.vx + p.vz*p.vz)
                max_speed = 25.0
                if speed > max_speed:
                    p.vx = (p.vx / speed) * max_speed
                    p.vz = (p.vz / speed) * max_speed
                
                # Sound
                if self.sound: 
                    self.sound.play('mallet_hit')
                
                # Particles
                self.spawn_particles(p.x, p.y + 0.2, p.z, 8, (1, 1, 0.3))
            
    def spawn_particles(self, x, y, z, n, col):
        for _ in range(n):
            self.particles.append(Particle(x, y, z, col))
            
    def update(self):
        dt = self.clock.tick(60) / 1000.0
        if dt > 0.1: dt = 0.1  # Cap delta time
        
        if self.winner: 
            return
        
        # AI targeting logic
        if self.puck.z > 0:  # Puck in AI's half
            ai_target = (self.puck.x, self.puck.z)
        else:  # Puck in player's half, AI defends
            ai_target = (0, 5)
        
        self.p1.update(dt)
        self.p2.update(dt, ai_target)
        
        res = self.puck.update(dt)
        if res == 'wall' and self.sound: 
            self.sound.play('wall_hit')
        
        # Mallet-Puck Collisions
        self.check_collision(self.p1, self.puck)
        self.check_collision(self.p2, self.puck)
        
        # Goal Checks
        if self.puck.z > TABLE_L + PUCK_RADIUS:
            self.goal(0)  # Player 1 scores (puck went past AI)
        elif self.puck.z < -TABLE_L - PUCK_RADIUS:
            self.goal(1)  # Player 2 (AI) scores
            
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles: 
            p.update(dt)
        
    def goal(self, scorer_idx):
        self.scores[scorer_idx] += 1
        if self.sound: 
            self.sound.play('goal')
        
        # Goal celebration particles
        goal_z = TABLE_L if scorer_idx == 0 else -TABLE_L
        self.spawn_particles(0, 1, goal_z, 30, (0, 1, 0.5))
        
        if self.scores[scorer_idx] >= WIN_SCORE:
            winner_name = "YOU" if scorer_idx == 0 else "AI"
            self.winner = f"{winner_name} WIN!"
        else:
            self.puck.reset()
            
    def draw_table(self):
        # Table surface (green/blue felt)
        glColor3f(0.1, 0.4, 0.3)
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-TABLE_W, TABLE_H, -TABLE_L)
        glVertex3f(TABLE_W, TABLE_H, -TABLE_L)
        glVertex3f(TABLE_W, TABLE_H, TABLE_L)
        glVertex3f(-TABLE_W, TABLE_H, TABLE_L)
        glEnd()
        
        # Side rails (brown/dark)
        glColor3f(0.4, 0.25, 0.1)
        
        # Left wall
        self.draw_box(-TABLE_W - WALL_THICK/2, TABLE_H + WALL_H/2, 0, 
                      WALL_THICK, WALL_H, TABLE_L * 2)
        # Right wall
        self.draw_box(TABLE_W + WALL_THICK/2, TABLE_H + WALL_H/2, 0, 
                      WALL_THICK, WALL_H, TABLE_L * 2)
        
        # Top wall (with goal opening)
        wall_side_w = (TABLE_W - GOAL_W/2)
        # Left part of top wall
        self.draw_box(-TABLE_W + wall_side_w/2, TABLE_H + WALL_H/2, TABLE_L + WALL_THICK/2,
                      wall_side_w, WALL_H, WALL_THICK)
        # Right part of top wall
        self.draw_box(TABLE_W - wall_side_w/2, TABLE_H + WALL_H/2, TABLE_L + WALL_THICK/2,
                      wall_side_w, WALL_H, WALL_THICK)
        
        # Bottom wall (with goal opening)
        self.draw_box(-TABLE_W + wall_side_w/2, TABLE_H + WALL_H/2, -TABLE_L - WALL_THICK/2,
                      wall_side_w, WALL_H, WALL_THICK)
        self.draw_box(TABLE_W - wall_side_w/2, TABLE_H + WALL_H/2, -TABLE_L - WALL_THICK/2,
                      wall_side_w, WALL_H, WALL_THICK)
        
        # Goal areas (darker)
        glColor3f(0.05, 0.05, 0.05)
        # Top goal
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-GOAL_W/2, TABLE_H - 0.01, TABLE_L)
        glVertex3f(GOAL_W/2, TABLE_H - 0.01, TABLE_L)
        glVertex3f(GOAL_W/2, TABLE_H - 0.01, TABLE_L + 1)
        glVertex3f(-GOAL_W/2, TABLE_H - 0.01, TABLE_L + 1)
        glEnd()
        # Bottom goal
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-GOAL_W/2, TABLE_H - 0.01, -TABLE_L)
        glVertex3f(GOAL_W/2, TABLE_H - 0.01, -TABLE_L)
        glVertex3f(GOAL_W/2, TABLE_H - 0.01, -TABLE_L - 1)
        glVertex3f(-GOAL_W/2, TABLE_H - 0.01, -TABLE_L - 1)
        glEnd()
        
        # Center line
        glDisable(GL_LIGHTING)
        glColor3f(1, 1, 1)
        glLineWidth(3)
        glBegin(GL_LINES)
        glVertex3f(-TABLE_W, TABLE_H + 0.01, 0)
        glVertex3f(TABLE_W, TABLE_H + 0.01, 0)
        glEnd()
        
        # Center circle
        glPushMatrix()
        glTranslatef(0, TABLE_H + 0.01, 0)
        glRotatef(90, 1, 0, 0)
        self.draw_circle_outline(1.5)
        glPopMatrix()
        
        # Goal lines
        glColor3f(1, 0, 0)
        glBegin(GL_LINES)
        # Top goal line
        glVertex3f(-GOAL_W/2, TABLE_H + 0.01, TABLE_L)
        glVertex3f(GOAL_W/2, TABLE_H + 0.01, TABLE_L)
        # Bottom goal line
        glVertex3f(-GOAL_W/2, TABLE_H + 0.01, -TABLE_L)
        glVertex3f(GOAL_W/2, TABLE_H + 0.01, -TABLE_L)
        glEnd()
        
        glEnable(GL_LIGHTING)
        
    def draw_box(self, cx, cy, cz, w, h, d):
        """Draw a box centered at (cx, cy, cz) with dimensions w, h, d"""
        x1, x2 = cx - w/2, cx + w/2
        y1, y2 = cy - h/2, cy + h/2
        z1, z2 = cz - d/2, cz + d/2
        
        glBegin(GL_QUADS)
        # Top
        glNormal3f(0, 1, 0)
        glVertex3f(x1, y2, z1); glVertex3f(x2, y2, z1)
        glVertex3f(x2, y2, z2); glVertex3f(x1, y2, z2)
        # Bottom
        glNormal3f(0, -1, 0)
        glVertex3f(x1, y1, z2); glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1); glVertex3f(x1, y1, z1)
        # Front
        glNormal3f(0, 0, 1)
        glVertex3f(x1, y1, z2); glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2); glVertex3f(x1, y2, z2)
        # Back
        glNormal3f(0, 0, -1)
        glVertex3f(x2, y1, z1); glVertex3f(x1, y1, z1)
        glVertex3f(x1, y2, z1); glVertex3f(x2, y2, z1)
        # Right
        glNormal3f(1, 0, 0)
        glVertex3f(x2, y1, z2); glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1); glVertex3f(x2, y2, z2)
        # Left
        glNormal3f(-1, 0, 0)
        glVertex3f(x1, y1, z1); glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2); glVertex3f(x1, y2, z1)
        glEnd()
        
    def draw_circle_outline(self, r):
        glBegin(GL_LINE_LOOP)
        for i in range(36):
            th = 2 * math.pi * i / 36
            glVertex2f(r * math.cos(th), r * math.sin(th))
        glEnd()

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Camera: Behind player 1, looking at the table
        # Using gluLookAt for proper camera setup
        eye_x, eye_y, eye_z = 0, 12, -18  # Camera position (behind player)
        look_x, look_y, look_z = 0, 0, 0   # Look at center of table
        up_x, up_y, up_z = 0, 1, 0         # Up vector
        
        gluLookAt(eye_x, eye_y, eye_z,
                  look_x, look_y, look_z,
                  up_x, up_y, up_z)
        
        # Draw scene
        self.draw_table()
        self.p1.draw(self.quadric)
        self.p2.draw(self.quadric)
        self.puck.draw(self.quadric)
        
        # Draw particles
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for p in self.particles: 
            p.draw(self.quadric)
        glDisable(GL_BLEND)
        
        # Draw UI overlay
        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self):
        # Switch to 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        
        # Score display
        score_text = f"{self.scores[0]}  -  {self.scores[1]}"
        surf = self.font.render(score_text, True, (255, 255, 255))
        data = pygame.image.tostring(surf, 'RGBA', True)
        w, h = surf.get_size()
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glRasterPos2i(self.width//2 - w//2, 60)
        glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)
        
        # Labels
        p1_label = self.font_small.render("YOU", True, (100, 150, 255))
        data1 = pygame.image.tostring(p1_label, 'RGBA', True)
        w1, h1 = p1_label.get_size()
        glRasterPos2i(self.width//2 - 80, 60)
        glDrawPixels(w1, h1, GL_RGBA, GL_UNSIGNED_BYTE, data1)
        
        p2_label = self.font_small.render("AI", True, (255, 100, 100))
        data2 = pygame.image.tostring(p2_label, 'RGBA', True)
        w2, h2 = p2_label.get_size()
        glRasterPos2i(self.width//2 + 60, 60)
        glDrawPixels(w2, h2, GL_RGBA, GL_UNSIGNED_BYTE, data2)
        
        # Controls hint
        hint = self.font_small.render("WASD: Move | R: Reset | ESC: Quit", True, (150, 150, 150))
        hint_data = pygame.image.tostring(hint, 'RGBA', True)
        wh, hh = hint.get_size()
        glRasterPos2i(self.width//2 - wh//2, self.height - 20)
        glDrawPixels(wh, hh, GL_RGBA, GL_UNSIGNED_BYTE, hint_data)
        
        # Winner text
        if self.winner:
            win_surf = self.font.render(self.winner, True, (50, 255, 100))
            win_data = pygame.image.tostring(win_surf, 'RGBA', True)
            ww, whi = win_surf.get_size()
            glRasterPos2i(self.width//2 - ww//2, self.height//2)
            glDrawPixels(ww, whi, GL_RGBA, GL_UNSIGNED_BYTE, win_data)
            
            restart_surf = self.font_small.render("Press R to restart", True, (200, 200, 200))
            restart_data = pygame.image.tostring(restart_surf, 'RGBA', True)
            rw, rh = restart_surf.get_size()
            glRasterPos2i(self.width//2 - rw//2, self.height//2 + 50)
            glDrawPixels(rw, rh, GL_RGBA, GL_UNSIGNED_BYTE, restart_data)

        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def run(self):
        while self.running:
            # Process events first
            for e in pygame.event.get():
                if e.type == QUIT: 
                    self.running = False
                elif e.type == KEYDOWN:
                    if e.key == K_ESCAPE: 
                        self.running = False
                    elif e.key == K_r: 
                        self.start_game()
                elif e.type == VIDEORESIZE: 
                    self.resize(e.w, e.h)
            
            self.update()
            self.render()

if __name__ == "__main__":
    g = Game()
    g.run()