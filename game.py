"""
3D Ping Pong (Pro Realism Edition)
==================================
Features:
- Realistic Physics (Magnus Effect for spin, Air Drag)
- 3D Modeled Rackets (Blade, Handle, Rubber)
- AI Opponent (Player 2)
- Procedural Sound Effects
- Dynamic Environment
- Full Rule Set (11 pts, Deuce)

Controls:
    Player 1 (Red - Back): A / D
    Player 2 (Blue - Front): Left / Right (or AI)
    SPACE: Serve
    I: Toggle AI for Player 2
    C: Cycle camera angles
    P: Pause/Resume
    F: Toggle FPS counter
    R: Reset match
    Esc: Quit
"""

import math
import random
import sys
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Try to import SoundGenerator
try:
    from sound_gen import SoundGenerator
except ImportError:
    SoundGenerator = None

# ============================================================================
# CONSTANTS & CONFIG
# ============================================================================

# Table dimensions (Standard Table Tennis: 2.74m x 1.525m)
# We scale slightly for gameplay feel
TABLE_HALF_WIDTH = 5.0      
TABLE_HALF_DEPTH = 8.0      
TABLE_HEIGHT = 0.0          
TABLE_THICKNESS = 0.3
NET_HEIGHT = 0.8            

# Physics Constants
# Physics Constants
GRAVITY = -18.0             # Gravity (m/s^2)
DRAG_COEFF = 0.08           # Air resistance (reduced)
MAGNUS_STRENGTH = 6.0       # Spin curve strength
RESTITUTION = 0.85          # Bounciness of table

# Paddle
PADDLE_WIDTH = 1.4
PADDLE_HEIGHT = 1.8
PADDLE_Z_OFFSET = 7.0

# Ball
BALL_RADIUS = 0.15
BALL_MASS = 0.1

# Game Rules
POINTS_TO_WIN = 11
WIN_BY = 2

# Camera
CAMERA_ANGLES = {
    'default': {'pos': (0, -6, -26), 'rot': (20, 0, 0)},
    'player1': {'pos': (0, -3, -16), 'rot': (10, 0, 0)},
    'player2': {'pos': (0, -3, 16), 'rot': (-10, 0, 180)},
    'side': {'pos': (-18, -4, 0), 'rot': (15, -90, 0)},
    'top': {'pos': (0, -22, 0), 'rot': (90, 0, 0)},
}

# ============================================================================
# HELPER CLASSES
# ============================================================================

class Particle:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(2, 6)
        self.vz = random.uniform(-3, 3)
        self.life = 0.6
        self.max_life = 0.6
        
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.vy += GRAVITY * dt
        self.life -= dt
        
    def draw(self, quadric):
        if self.life <= 0: return
        alpha = self.life / self.max_life
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glColor4f(1.0, 0.9, 0.4, alpha)
        # Simple billboard or small sphere
        gluSphere(quadric, 0.05, 4, 4)
        glPopMatrix()

class BallTrail:
    def __init__(self, length=10):
        self.positions = []
        self.length = length
        
    def add(self, x, y, z):
        self.positions.append((x, y, z))
        if len(self.positions) > self.length:
            self.positions.pop(0)
            
    def clear(self):
        self.positions = []
        
    def draw(self, quadric):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        count = len(self.positions)
        for i, (px, py, pz) in enumerate(self.positions):
            alpha = (i / count) * 0.4
            size = BALL_RADIUS * (0.4 + (i/count)*0.6)
            glPushMatrix()
            glTranslatef(px, py, pz)
            glColor4f(1, 1, 0.2, alpha)
            gluSphere(quadric, size, 6, 6)
            glPopMatrix()
        glDisable(GL_BLEND)

# ============================================================================
# GAME ENTITIES
# ============================================================================

class AIPlayer:
    """Simple AI Opponent"""
    def __init__(self, paddle):
        self.paddle = paddle
        self.reaction_timer = 0.0
        self.target_x = 0.0
        self.skill_level = 0.8 # 0.0 to 1.0 (Speed/Accuracy)
        
    def update(self, dt, ball):
        # Only react if ball is coming towards us (vz > 0 for Player 2)
        if ball.vz > 0:
            # Predict x impact
            time_to_impact = abs((self.paddle.z - ball.z) / (ball.vz if abs(ball.vz) > 0.1 else 0.1))
            
            if time_to_impact < 1.5: # React when closer
                self.target_x = ball.x + ball.vx * time_to_impact
                # Add some error based on skill
                error = (1.0 - self.skill_level) * random.uniform(-1.0, 1.0)
                if time_to_impact > 0.5: # Refine target as it gets closer
                    self.target_x += error
            else:
                self.target_x = 0.0 # Return to center
        else:
            self.target_x = 0.0 # Return to center
            
        # Move paddle
        diff = self.target_x - self.paddle.x
        force = 10.0 if abs(diff) > 1.0 else 5.0
        
        move_dir = 0
        if diff > 0.2: move_dir = 1
        elif diff < -0.2: move_dir = -1
        
        self.paddle.move_horizontal(move_dir, dt)

class Paddle:
    def __init__(self, z, color_rubber):
        self.z = z
        self.x = 0.0
        self.y = 1.0
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT # Actually Diameter of the blade
        self.depth = 0.2
        self.speed = 10.0
        self.color_rubber = color_rubber
        self.tilt = 0.0
        
    def move_horizontal(self, direction, dt):
        self.x += direction * self.speed * dt
        limit = TABLE_HALF_WIDTH + 1.0
        self.x = max(-limit, min(limit, self.x))
        # Tilt effect
        target_tilt = -direction * 15.0
        self.tilt += (target_tilt - self.tilt) * 10.0 * dt

    def draw(self, quadric):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.tilt, 0, 0, 1)
        glRotatef(90, 0, 1, 0) # Rotate to face forward
        
        # 1. Handle (Wood Cylinder)
        glColor3f(0.6, 0.4, 0.2)
        glPushMatrix()
        glTranslatef(0, -0.8, 0)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quadric, 0.12, 0.15, 0.8, 12, 1)
        # Cap
        gluDisk(quadric, 0, 0.12, 12, 1)
        glPopMatrix()
        
        # 2. Blade (Wood Disk/Sandwich)
        # We need a transformation to place the blade head
        glPushMatrix()
        glTranslatef(0, 0.5, 0) 
        glScalef(0.2, 1.0, 1.0) # Thickness, Height, Width scaling
        
        # Wood core
        glColor3f(0.7, 0.6, 0.4)
        draw_box_centered(0.1, 1.3, 1.25)
        
        # 3. Rubber Faces
        # Face 1
        glColor3f(*self.color_rubber)
        glPushMatrix()
        glTranslatef(0.06, 0, 0)
        draw_box_centered(0.02, 1.25, 1.2)
        glPopMatrix()
        
        # Face 2 (Black)
        glColor3f(0.1, 0.1, 0.1)
        glPushMatrix()
        glTranslatef(-0.06, 0, 0)
        draw_box_centered(0.02, 1.25, 1.2)
        glPopMatrix()
        
        glPopMatrix()
        glPopMatrix()

class Ball:
    def __init__(self):
        self.trail = BallTrail()
        self.reset()
        
    def reset(self, server=1):
        self.x = 0.0
        self.y = NET_HEIGHT + 0.5
        self.z = -5.0 if server == 1 else 5.0
        
        
        # Launch params
        speed = 22.0 # Increased serve speed
        forward = 1 if server == 1 else -1
        
        self.vx = random.uniform(-1, 1) # Reduced lateral randomness
        self.vy = random.uniform(4, 6)  # Higher toss for arc
        self.vz = forward * speed * 0.6 # Stronger forward push
        
        self.spin_x = 0.0 # Top/Back spin  (Magus force in Y/Z)
        self.spin_y = 0.0 # Side spin      (Magnus force in X/Z)
        self.in_play = True
        self.last_hit_by = 0 # 0=None, 1=P1, 2=P2
        self.bounces_side1 = 0
        self.bounces_side2 = 0
        self.trail.clear()

    def update(self, dt):
        if not self.in_play: return

        # 1. Gravity
        self.vy += GRAVITY * dt

        # 2. Air Drag (F_drag = -C * v * |v|)
        v_sq = self.vx**2 + self.vy**2 + self.vz**2
        v_mag = math.sqrt(v_sq)
        if v_mag > 0:
            drag_f = DRAG_COEFF * v_mag
            self.vx -= drag_f * self.vx * dt
            self.vy -= drag_f * self.vy * dt
            self.vz -= drag_f * self.vz * dt

        # 3. Magnus Effect (Lift due to spin)
        # Force ~ V x Spin
        # Simple approximation:
        # Topspin (spin_x > 0) -> Dip down (force -Y)
        magnus_y = -self.spin_x * self.vz * MAGNUS_STRENGTH * dt
        # Side spin -> Curve X
        magnus_x = self.spin_y * self.vz * MAGNUS_STRENGTH * dt
        
        self.vy += magnus_y
        self.vx += magnus_x
        
        # Move
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        
        self.trail.add(self.x, self.y, self.z)

    def draw(self, quadric):
        self.trail.draw(quadric)
        
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Glow
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 1.0, 0.8, 0.4)
        gluSphere(quadric, BALL_RADIUS*1.4, 12, 12)
        glDisable(GL_BLEND)
        
        # Ball
        glColor3f(1.0, 1.0, 1.0)
        make_material((1,1,1), (1,1,1), 60)
        gluSphere(quadric, BALL_RADIUS, 16, 16)
        
        glPopMatrix()

# ============================================================================
# RENDERING UTILS
# ============================================================================

def make_material(diffuse, specular, shininess):
    glMaterialfv(GL_FRONT, GL_DIFFUSE, (*diffuse, 1.0))
    glMaterialfv(GL_FRONT, GL_SPECULAR, (*specular, 1.0))
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)

def draw_box_centered(w, h, d):
    glPushMatrix()
    glScalef(w, h, d)
    glutSolidCube(1.0) if 'glutSolidCube' in globals() else draw_cube_arrays()
    glPopMatrix()

def draw_cube_arrays():
    # Simple fallback if GLUT is annoying
    glBegin(GL_QUADS)
    # Front
    glNormal3f(0,0,1)
    glVertex3f(-0.5, -0.5, 0.5); glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5); glVertex3f(-0.5, 0.5, 0.5)
    # Back
    glNormal3f(0,0,-1)
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5); glVertex3f(0.5, -0.5, -0.5)
    # Right
    glNormal3f(1,0,0)
    glVertex3f(0.5, -0.5, -0.5); glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, -0.5, 0.5)
    # Left
    glNormal3f(-1,0,0)
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5); glVertex3f(-0.5, 0.5, -0.5)
    # Top
    glNormal3f(0,1,0)
    glVertex3f(-0.5, 0.5, -0.5); glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, 0.5, -0.5)
    # Bottom
    glNormal3f(0,-1,0)
    glVertex3f(-0.5, -0.5, -0.5); glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5); glVertex3f(-0.5, -0.5, 0.5)
    glEnd()

def draw_stadium():
    # Large dark room
    glColor3f(0.1, 0.1, 0.12)
    glDisable(GL_LIGHTING) # Ambient room feel
    
    room_w = 40
    room_h = 20
    room_d = 50
    
    glBegin(GL_QUADS)
    # Floor
    glColor3f(0.05, 0.05, 0.08)
    glVertex3f(-room_w, -5, -room_d); glVertex3f(room_w, -5, -room_d)
    glVertex3f(room_w, -5, room_d); glVertex3f(-room_w, -5, room_d)
    # Ceiling
    glColor3f(0.02, 0.02, 0.03)
    glVertex3f(-room_w, room_h, -room_d); glVertex3f(-room_w, room_h, room_d)
    glVertex3f(room_w, room_h, room_d); glVertex3f(room_w, room_h, -room_d)
    # Walls (Striped for depth perception)
    for i in range(-5, 6):
        c = 0.06 if i % 2 == 0 else 0.08
        glColor3f(c, c, c+0.02)
        z1 = i * 10
        z2 = (i+1) * 10
        # Right Wall
        glVertex3f(room_w, -5, z1); glVertex3f(room_w, room_h, z1)
        glVertex3f(room_w, room_h, z2); glVertex3f(room_w, -5, z2)
        # Left Wall
        glVertex3f(-room_w, -5, z1); glVertex3f(-room_w, -5, z2)
        glVertex3f(-room_w, room_h, z2); glVertex3f(-room_w, room_h, z1)
        
    glEnd()
    glEnable(GL_LIGHTING)

def draw_table_mesh(quadric):
    # Table Top (Blue)
    glColor3f(0.0, 0.3, 0.8) # Pro Blue
    make_material((0, 0.3, 0.8), (0.5, 0.5, 0.5), 30)
    draw_box_centered(TABLE_HALF_WIDTH*2, TABLE_THICKNESS, TABLE_HALF_DEPTH*2)
    
    # Lines (White)
    glDisable(GL_LIGHTING)
    glColor3f(1, 1, 1)
    glLineWidth(2)
    y = TABLE_THICKNESS/2 + 0.02
    
    glBegin(GL_LINES)
    # Center
    glVertex3f(0, y, -TABLE_HALF_DEPTH); glVertex3f(0, y, TABLE_HALF_DEPTH)
    # Edges
    glVertex3f(-TABLE_HALF_WIDTH, y, -TABLE_HALF_DEPTH); glVertex3f(-TABLE_HALF_WIDTH, y, TABLE_HALF_DEPTH)
    glVertex3f(TABLE_HALF_WIDTH, y, -TABLE_HALF_DEPTH); glVertex3f(TABLE_HALF_WIDTH, y, TABLE_HALF_DEPTH)
    glVertex3f(-TABLE_HALF_WIDTH, y, -TABLE_HALF_DEPTH); glVertex3f(TABLE_HALF_WIDTH, y, -TABLE_HALF_DEPTH)
    glVertex3f(-TABLE_HALF_WIDTH, y, TABLE_HALF_DEPTH); glVertex3f(TABLE_HALF_WIDTH, y, TABLE_HALF_DEPTH)
    glEnd()
    glEnable(GL_LIGHTING)
    
    # Net
    glDisable(GL_CULL_FACE)
    glColor4f(0.9, 0.9, 0.9, 0.8) # Transparentish
    glBegin(GL_QUADS)
    glVertex3f(-TABLE_HALF_WIDTH-0.2, y, 0)
    glVertex3f(TABLE_HALF_WIDTH+0.2, y, 0)
    glVertex3f(TABLE_HALF_WIDTH+0.2, y+NET_HEIGHT, 0)
    glVertex3f(-TABLE_HALF_WIDTH-0.2, y+NET_HEIGHT, 0)
    glEnd()
    glEnable(GL_CULL_FACE)
    
    # Legs (Black metal)
    glColor3f(0.1, 0.1, 0.1)
    for x in [-4, 4]:
        for z in [-6, 6]:
            glPushMatrix()
            glTranslatef(x, -2.5, z)
            glScalef(0.4, 5.0, 0.4)
            draw_box_centered(1,1,1)
            glPopMatrix()

# ============================================================================
# MAIN GAME CLASS
# ============================================================================

class Game:
    def __init__(self, w=1400, h=900):
        pygame.init()
        pygame.display.set_mode((w, h), DOUBLEBUF | OPENGL | RESIZABLE)
        pygame.display.set_caption("3D Ping Pong Pro")
        self.width, self.height = w, h
        
        self.init_gl()
        
        # Audio
        self.sound_gen = None
        if SoundGenerator:
            self.sound_gen = SoundGenerator()
            
        # Assets
        self.quadric = gluNewQuadric()
        
        # State
        self.reset_match()
        
        # Camera
        self.cam_mode = 'default'
        self.cam_keys = list(CAMERA_ANGLES.keys())
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.ai_enabled = False
        
        # Font
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 40, bold=True)
        self.font_sm = pygame.font.SysFont('Arial', 24)

    def init_gl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_NORMALIZE)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
        
        # Lights
        glLightfv(GL_LIGHT0, GL_POSITION, (10, 20, 10, 0)) # Sun-like
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.9, 0.9, 0.9, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1, 1, 1, 1))
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (0.3, 0.3, 0.3, 1))
        
        self.resize(self.width, self.height)

    def resize(self, w, h):
        self.width, self.height = w, h
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 200)
        glMatrixMode(GL_MODELVIEW)

    def reset_match(self):
        self.score = [0, 0]
        self.server = 1
        self.waiting_serve = True
        self.game_over = False
        self.winner_text = ""
        
        self.ball = Ball()
        self.p1 = Paddle(-PADDLE_Z_OFFSET, (0.8, 0.1, 0.1)) # Red
        self.p2 = Paddle(PADDLE_Z_OFFSET, (0.1, 0.1, 0.1))  # Black
        self.ai = AIPlayer(self.p2)
        self.particles = []

    def handle_collisions(self):
        b = self.ball
        
        # Table Bounce
        if b.y < BALL_RADIUS and b.vy < 0:
            if abs(b.x) < TABLE_HALF_WIDTH and abs(b.z) < TABLE_HALF_DEPTH:
                # Physics Reset
                b.y = BALL_RADIUS
                b.vy = -b.vy * RESTITUTION
                b.vx *= 0.95
                b.vz *= 0.95
                
                # Sound (Only if bouncing hard enough to avoid spam)
                if self.sound_gen and abs(b.vy) > 0.5: 
                    self.sound_gen.play('table_hit')
                
                self.spawn_particles(b.x, b.y, b.z, 3)

                # Game Rule: Count Bounces
                if b.z < 0:
                    b.bounces_side1 += 1
                    b.bounces_side2 = 0 # Reset other side
                else:
                    b.bounces_side2 += 1
                    b.bounces_side1 = 0
                
                # Check for Point (Double Bounce)
                if b.bounces_side1 >= 2:
                    self.score_point(2) # P1 let it bounce twice, P2 wins point
                elif b.bounces_side2 >= 2:
                    self.score_point(1)

        # Paddle Collision
        for i, p in enumerate([self.p1, self.p2]):
            player_id = i + 1
            # Check Z proximity
            dist_z = abs(b.z - p.z)
            if dist_z < (BALL_RADIUS + 0.3): 
                # Check Face overlap
                if abs(b.x - p.x) < (PADDLE_WIDTH/2 + BALL_RADIUS) and \
                   abs(b.y - p.y) < (PADDLE_HEIGHT/2 + BALL_RADIUS):
                    
                    # Ensure moving towards paddle
                    move_towards = (b.vz < 0 and player_id==1) or (b.vz > 0 and player_id==2)
                    
                    if move_towards:
                        # HIT!
                        # POWER BOOST: Add base velocity + multiplier
                        # This fixes "weak paddle" feel
                        boost = 5.0 
                        b.vz = -b.vz * 1.2 - (boost if b.vz < 0 else -boost)
                        
                        # Add upward lift for arc
                        b.vy = abs(b.vy) * 0.8 + 2.0 

                        # Add Spin/Curve
                        hit_offset = (b.x - p.x)
                        b.vx += hit_offset * 6.0
                        b.spin_x = random.uniform(-2, 2)
                        b.spin_y = hit_offset * 2.5
                        
                        # Reset bounces
                        b.bounces_side1 = 0
                        b.bounces_side2 = 0
                        b.last_hit_by = player_id
                        
                        # Sound
                        if self.sound_gen: self.sound_gen.play('paddle_hit')
                        self.spawn_particles(b.x, b.y, b.z, 12)
                        
                        # Cap speed to prevent physics glitching
                        max_speed = 35.0
                        if abs(b.vz) > max_speed: b.vz = max_speed if b.vz > 0 else -max_speed

        # Scoring
        if b.z > 15: self.score_point(1) # P2 missed, P1 scores
        elif b.z < -15: self.score_point(2) 

        # Out of bounds (Hit floor)
        if b.y < -5:
            if b.z > 0: self.score_point(1)
            else: self.score_point(2)

    def score_point(self, winner_idx):
        if self.game_over: return
        
        # Winner idx is 1 or 2
        self.score[winner_idx-1] += 1
        
        if self.sound_gen: self.sound_gen.play('score')
        
        # Game Over Check
        s1, s2 = self.score
        if (s1 >= POINTS_TO_WIN and s1 >= s2 + WIN_BY) or \
           (s2 >= POINTS_TO_WIN and s2 >= s1 + WIN_BY):
            self.game_over = True
            self.winner_text = f"PLAYER {winner_idx} WINS!"
        else:
            self.waiting_serve = True
            self.ball.reset(server=1 if ((sum(self.score)//2)%2==0) else 2) 

    def spawn_particles(self, x, y, z, n):
        for _ in range(n):
            self.particles.append(Particle(x, y, z))

    def update(self, dt):
        # Update particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles: p.update(dt)
        
        if self.waiting_serve:
            # Sync ball to server paddle
            server_z = -5 if self.server == 1 else 5
            self.ball.x = 0
            self.ball.y = 2
            self.ball.z = server_z
            return
            
        if self.game_over: return
        
        self.ball.update(dt)
        self.handle_collisions()
        
        if self.ai_enabled:
            self.ai.update(dt, self.ball)

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Camera
        cam = CAMERA_ANGLES[self.cam_mode]
        glTranslatef(*cam['pos'])
        glRotatef(cam['rot'][0], 1, 0, 0)
        glRotatef(cam['rot'][1], 0, 1, 0)
        glRotatef(cam['rot'][2], 0, 0, 1)
        
        # Draw World
        draw_stadium()
        draw_table_mesh(self.quadric)
        
        self.p1.draw(self.quadric)
        self.p2.draw(self.quadric)
        self.ball.draw(self.quadric)
        
        for p in self.particles: p.draw(self.quadric)
        
        # 2D UI
        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self):
        # 2D Projection
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_LIGHTING); glDisable(GL_DEPTH_TEST)
        
        # Text helper
        def draw_text(txt, x, y, col=(255,255,255), center=False, font=self.font):
            surf = font.render(txt, True, col)
            data = pygame.image.tostring(surf, 'RGBA', True)
            w, h = surf.get_size()
            if center: x -= w//2
            
            glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glRasterPos2i(int(x), int(y+h))
            glDrawPixels(w, h, GL_RGBA, GL_UNSIGNED_BYTE, data)

        # HUD
        draw_text(f"{self.score[0]} - {self.score[1]}", self.width//2, 20, center=True)
        draw_text(f"P2: {'AI' if self.ai_enabled else 'HUMAN'}", self.width-150, 20, font=self.font_sm, col=(200,200,100))
        
        if self.waiting_serve:
             draw_text("PRESS SPACE TO SERVE", self.width//2, self.height//2 + 50, col=(255,255,0), center=True)
             
        if self.game_over:
             draw_text(self.winner_text, self.width//2, self.height//2 - 50, col=(50,255,50), center=True)
             draw_text("PRESS R TO RESET", self.width//2, self.height//2 + 10, font=self.font_sm, center=True)

        glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING)
        glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

    def run(self):
        while self.running:
            dt = self.clock.tick(120) / 1000.0
            
            for event in pygame.event.get():
                if event.type == QUIT: self.running = False
                elif event.type == VIDEORESIZE: self.resize(event.w, event.h)
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE: self.running = False
                    elif event.key == K_r: self.reset_match()
                    elif event.key == K_SPACE: 
                        if self.waiting_serve: 
                            self.waiting_serve = False
                            # Launch ball
                            self.ball.reset(server=1 if ((sum(self.score)//2)%2==0) else 2)
                    elif event.key == K_c:
                         idx = self.cam_keys.index(self.cam_mode)
                         self.cam_mode = self.cam_keys[(idx+1)%len(self.cam_keys)]
                    elif event.key == K_i: self.ai_enabled = not self.ai_enabled
            
            # Input
            keys = pygame.key.get_pressed()
            if keys[K_a]: self.p1.move_horizontal(-1, dt)
            if keys[K_d]: self.p1.move_horizontal(1, dt)
            
            if not self.ai_enabled:
                if keys[K_LEFT]: self.p2.move_horizontal(-1, dt)
                if keys[K_RIGHT]: self.p2.move_horizontal(1, dt)

            self.update(dt)
            self.render()
            
        pygame.quit()

if __name__ == "__main__":
    Game().run()