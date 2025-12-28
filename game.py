"""
3D Ping Pong (Table Tennis) Game
==================================
Proper table tennis rules: First to 11 points, win by 2.
Features realistic 3D graphics, physics with gravity, multiple camera angles.

Controls:
    Player 1 (Red - Back): A / D
    Player 2 (Blue - Front): Left / Right
    SPACE: Manual serve
    C: Cycle camera angles
    P: Pause/Resume
    F: Toggle FPS counter
    R: Reset match
    Esc: Quit

Requirements:
    pip install pygame PyOpenGL

Run:
    python game.py
"""

import math
import random
import sys
import pygame
from pygame.locals import (
    DOUBLEBUF,
    OPENGL,
    K_ESCAPE,
    K_a,
    K_d,
    K_LEFT,
    K_RIGHT,
    K_r,
    K_c,
    K_SPACE,
    K_p,
    K_f,
    QUIT,
    KEYDOWN,
)
from OpenGL.GL import *
from OpenGL.GLU import *

# ============================================================================
# GAME CONSTANTS
# ============================================================================

# Table dimensions (standard table tennis: 2.74m x 1.525m, height 0.76m)
TABLE_HALF_WIDTH = 5.0      # x range: -5 .. 5
TABLE_HALF_DEPTH = 8.0      # z range: -8 .. 8
TABLE_HEIGHT = 0.0          # y position of table surface
TABLE_THICKNESS = 0.3

# Net dimensions
NET_HEIGHT = 0.6            # 6 inches above table
NET_POST_RADIUS = 0.08

# Paddle dimensions
PADDLE_WIDTH = 1.2
PADDLE_HEIGHT = 1.6
PADDLE_DEPTH = 0.15
PADDLE_Z_OFFSET = 6.5       # distance from center

# Ball properties
BALL_RADIUS = 0.15
BALL_INITIAL_SPEED = 8.0
GRAVITY = -15.0             # downward acceleration

# Game rules
POINTS_TO_WIN = 11
WIN_BY = 2                  # must win by at least 2 points
DEUCE_POINT = 10            # when both players reach this, serves alternate every point

# Performance
MAX_FPS = 120

# Camera angles
CAMERA_ANGLES = {
    'default': {'pos': (0, -4, -28), 'rot': (18, 0, 0)},
    'player1': {'pos': (0, -2, -15), 'rot': (10, 0, 0)},
    'player2': {'pos': (0, -2, 15), 'rot': (-10, 0, 180)},
    'side': {'pos': (-18, -3, 0), 'rot': (15, -90, 0)},
    'top': {'pos': (0, -20, 0), 'rot': (90, 0, 0)},
}

# ============================================================================
# UTILITY CLASSES
# ============================================================================

class Particle:
    """Simple particle for impact effects"""
    def __init__(self, x, y, z, vx, vy, vz, life=0.5):
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = vx, vy, vz
        self.life = life
        self.max_life = life
        self.size = random.uniform(0.03, 0.08)
        
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.vy += GRAVITY * 0.5 * dt  # gravity on particles
        self.life -= dt
        
    def is_alive(self):
        return self.life > 0
        
    def draw(self, quadric):
        alpha = self.life / self.max_life
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glColor4f(1.0, 0.8, 0.2, alpha)
        gluSphere(quadric, self.size, 6, 6)
        glPopMatrix()


class ParticleSystem:
    """Manages particle effects"""
    def __init__(self):
        self.particles = []
        
    def emit(self, x, y, z, count=10):
        """Emit particles from a position"""
        for _ in range(count):
            vx = random.uniform(-2, 2)
            vy = random.uniform(1, 4)
            vz = random.uniform(-2, 2)
            self.particles.append(Particle(x, y, z, vx, vy, vz))
            
    def update(self, dt):
        for particle in self.particles[:]:
            particle.update(dt)
            if not particle.is_alive():
                self.particles.remove(particle)
                
    def draw(self, quadric):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        for particle in self.particles:
            particle.draw(quadric)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)


class BallTrail:
    """Ball trail effect for better visibility"""
    def __init__(self, max_length=8):
        self.positions = []
        self.max_length = max_length
        
    def add_position(self, x, y, z):
        self.positions.append((x, y, z))
        if len(self.positions) > self.max_length:
            self.positions.pop(0)
            
    def draw(self, quadric):
        if len(self.positions) < 2:
            return
            
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        
        count = len(self.positions)
        for i, (x, y, z) in enumerate(self.positions):
            alpha = (i + 1) / count * 0.6
            size = BALL_RADIUS * (0.5 + (i + 1) / count * 0.5)
            glPushMatrix()
            glTranslatef(x, y, z)
            glColor4f(1.0, 1.0, 0.5, alpha)
            gluSphere(quadric, size, 8, 8)
            glPopMatrix()
            
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        
    def clear(self):
        """Clear all trail positions"""
        self.positions = []

# ============================================================================
# GAME ENTITIES
# ============================================================================

class Paddle:
    """Paddle with enhanced 3D appearance and rotation"""
    def __init__(self, z, color):
        self.z = z
        self.x = 0.0
        self.y = PADDLE_HEIGHT / 2
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.depth = PADDLE_DEPTH
        self.speed = 9.0
        self.color = color
        self.tilt = 0.0  # rotation based on movement
        self.target_tilt = 0.0
        
    def move_horizontal(self, dx, dt):
        """Move paddle horizontally"""
        self.x += dx * self.speed * dt
        limit = TABLE_HALF_WIDTH - self.width / 2 - 0.2
        self.x = max(-limit, min(limit, self.x))
        
        # Set tilt based on movement direction
        self.target_tilt = dx * 8.0
        
    def update(self, dt):
        """Update paddle state (smooth tilt animation)"""
        # Smooth tilt interpolation
        self.tilt += (self.target_tilt - self.tilt) * 10.0 * dt
        
    def draw(self):
        """Draw paddle with 3D appearance"""
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.tilt, 0, 0, 1)  # tilt effect
        
        # Paddle body (wood handle)
        glColor3f(*self.color)
        glPushMatrix()
        glScalef(self.width, self.height, self.depth)
        draw_unit_cube()
        glPopMatrix()
        
        # Rubber surface (pure black for contrast)
        glColor3f(0.0, 0.0, 0.0)
        offset = self.depth / 2 + 0.02
        glPushMatrix()
        glTranslatef(0, 0, offset if self.z > 0 else -offset)
        glScalef(self.width - 0.1, self.height - 0.1, 0.03)
        draw_unit_cube()
        glPopMatrix()
        
        glPopMatrix()


class Ball:
    """Ball with realistic physics including gravity and spin"""
    def __init__(self):
        self.trail = BallTrail()
        self.reset()
        
    def reset(self, server=1):
        """Reset ball position and velocity
        server: 1 or 2 indicating who serves (receives ball moving toward them)
        """
        self.x = 0.0
        self.y = NET_HEIGHT + 1.0
        self.z = 0.0
        
        # Initial velocity
        angle_deg = random.uniform(-15, 15)
        angle = math.radians(angle_deg)
        
        # Serve toward the server (they receive it)
        direction = 1 if server == 1 else -1
        speed = BALL_INITIAL_SPEED
        
        self.vx = speed * math.sin(angle)
        self.vy = random.uniform(1.0, 2.5)  # initial upward velocity
        self.vz = direction * speed * math.cos(angle)
        
        # Spin properties
        self.spin_x = 0.0
        self.spin_z = 0.0
        
        # Bounce counter
        self.table_bounces = 0
        
        self.trail.clear()
        
    def update(self, dt):
        """Update ball position with physics"""
        # Apply gravity
        self.vy += GRAVITY * dt
        
        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        
        # Apply spin effect (affects horizontal velocity slightly)
        self.vx += self.spin_x * dt * 0.5
        self.vz += self.spin_z * dt * 0.5
        
        # Add to trail
        self.trail.add_position(self.x, self.y, self.z)
        
    def bounce_table(self):
        """Bounce ball off table surface"""
        if self.y < TABLE_HEIGHT + BALL_RADIUS and self.vy < 0:
            # Check if ball is within table bounds
            if (abs(self.x) < TABLE_HALF_WIDTH and 
                abs(self.z) < TABLE_HALF_DEPTH):
                self.y = TABLE_HEIGHT + BALL_RADIUS
                self.vy = -self.vy * 0.75  # some energy loss
                self.table_bounces += 1
                return True
        return False
        
    def bounce_paddle(self, paddle, particles):
        """Check and handle paddle collision"""
        # Determine which face of paddle to check
        if paddle.z > 0:  # player 2 (front)
            paddle_face_z = paddle.z - paddle.depth / 2
            moving_toward = self.vz > 0
        else:  # player 1 (back)
            paddle_face_z = paddle.z + paddle.depth / 2
            moving_toward = self.vz < 0
            
        # Check if ball is at paddle position and moving toward it
        if not moving_toward:
            return False
            
        ball_edge = self.z + BALL_RADIUS if paddle.z > 0 else self.z - BALL_RADIUS
        
        # Check collision
        if ((paddle.z > 0 and ball_edge >= paddle_face_z) or 
            (paddle.z < 0 and ball_edge <= paddle_face_z)):
            
            # Check horizontal and vertical overlap
            if (abs(self.x - paddle.x) <= paddle.width / 2 + BALL_RADIUS and
                abs(self.y - paddle.y) <= paddle.height / 2 + BALL_RADIUS):
                
                # Collision! Reset ball position
                if paddle.z > 0:
                    self.z = paddle_face_z - BALL_RADIUS - 0.01
                else:
                    self.z = paddle_face_z + BALL_RADIUS + 0.01
                    
                # Reflect and speed up
                self.vz = -self.vz * 1.05
                
                # Add spin based on where ball hits paddle
                offset_x = (self.x - paddle.x) / (paddle.width / 2)
                offset_y = (self.y - paddle.y) / (paddle.height / 2)
                
                # Horizontal offset affects horizontal velocity and spin
                self.vx += offset_x * 3.5
                self.spin_x = offset_x * 2.0
                
                # Vertical offset affects vertical velocity slightly
                self.vy += offset_y * 1.5
                
                # Reset table bounces on paddle hit
                self.table_bounces = 0
                
                # Emit particles
                particles.emit(self.x, self.y, self.z, 8)
                
                return True
        return False
        
    def check_out_of_bounds(self):
        """Check if ball is out of bounds horizontally"""
        limit_x = TABLE_HALF_WIDTH + 2.0
        if abs(self.x) > limit_x:
            return True
        if self.y < -5.0:  # fell way below table
            return True
        return False
        
    def draw(self, quadric):
        """Draw ball"""
        # Draw trail first
        self.trail.draw(quadric)
        
        # Draw ball with glow
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        
        # Outer glow (bright yellow for visibility)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1.0, 1.0, 0.0, 0.5)
        gluSphere(quadric, BALL_RADIUS * 1.6, 16, 16)
        glDisable(GL_BLEND)
        
        # Main ball (bright white)
        glColor3f(1.0, 1.0, 1.0)
        gluSphere(quadric, BALL_RADIUS, 20, 20)
        
        glPopMatrix()

# ============================================================================
# DRAWING UTILITIES
# ============================================================================

def draw_unit_cube():
    """Draw a unit cube centered at origin"""
    glBegin(GL_QUADS)
    
    # Front
    glNormal3f(0, 0, 1)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    
    # Back
    glNormal3f(0, 0, -1)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, -0.5, -0.5)
    
    # Left
    glNormal3f(-1, 0, 0)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, -0.5)
    
    # Right
    glNormal3f(1, 0, 0)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, 0.5, -0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    
    # Top
    glNormal3f(0, 1, 0)
    glVertex3f(-0.5, 0.5, -0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(0.5, 0.5, -0.5)
    
    # Bottom
    glNormal3f(0, -1, 0)
    glVertex3f(-0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, -0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(-0.5, -0.5, 0.5)
    
    glEnd()


def draw_cylinder(quadric, radius, height, slices=20):
    """Draw a cylinder along Y axis"""
    gluCylinder(quadric, radius, radius, height, slices, 1)


def draw_table(quadric):
    """Draw realistic 3D table tennis table"""
    
    # Table surface (bright blue - high contrast)
    glColor3f(0.15, 0.45, 0.75)
    glPushMatrix()
    glTranslatef(0, TABLE_HEIGHT, 0)
    glScalef(TABLE_HALF_WIDTH * 2, TABLE_THICKNESS, TABLE_HALF_DEPTH * 2)
    draw_unit_cube()
    glPopMatrix()
    
    # Center line (white)
    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(3.0)
    glBegin(GL_LINES)
    glVertex3f(-TABLE_HALF_WIDTH, TABLE_HEIGHT + TABLE_THICKNESS/2 + 0.01, 0)
    glVertex3f(TABLE_HALF_WIDTH, TABLE_HEIGHT + TABLE_THICKNESS/2 + 0.01, 0)
    glEnd()
    
    # Side lines (bright white)
    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(2.0)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-TABLE_HALF_WIDTH, TABLE_HEIGHT + TABLE_THICKNESS/2 + 0.01, -TABLE_HALF_DEPTH)
    glVertex3f(TABLE_HALF_WIDTH, TABLE_HEIGHT + TABLE_THICKNESS/2 + 0.01, -TABLE_HALF_DEPTH)
    glVertex3f(TABLE_HALF_WIDTH, TABLE_HEIGHT + TABLE_THICKNESS/2 + 0.01, TABLE_HALF_DEPTH)
    glVertex3f(-TABLE_HALF_WIDTH, TABLE_HEIGHT + TABLE_THICKNESS/2 + 0.01, TABLE_HALF_DEPTH)
    glEnd()
    glLineWidth(1.0)
    
    # Table legs (4 legs at corners)
    leg_height = 3.0
    leg_radius = 0.15
    leg_offset_x = TABLE_HALF_WIDTH - 0.5
    leg_offset_z = TABLE_HALF_DEPTH - 0.5
    
    glColor3f(0.15, 0.15, 0.2)
    for x_sign in [-1, 1]:
        for z_sign in [-1, 1]:
            glPushMatrix()
            glTranslatef(x_sign * leg_offset_x, TABLE_HEIGHT - TABLE_THICKNESS/2 - leg_height, z_sign * leg_offset_z)
            glRotatef(-90, 1, 0, 0)
            draw_cylinder(quadric, leg_radius, leg_height, 12)
            glPopMatrix()
    
    # Net posts
    net_post_height = NET_HEIGHT + TABLE_THICKNESS / 2
    glColor3f(0.15, 0.15, 0.15)
    for x_sign in [-1, 1]:
        glPushMatrix()
        glTranslatef(x_sign * (TABLE_HALF_WIDTH + 0.3), TABLE_HEIGHT + TABLE_THICKNESS/2, 0)
        glRotatef(-90, 1, 0, 0)
        draw_cylinder(quadric, NET_POST_RADIUS, net_post_height, 12)
        glPopMatrix()
    
    # Net (mesh effect with lines - bright white)
    glColor3f(1.0, 1.0, 1.0)
    glLineWidth(2.0)
    
    # Vertical lines
    num_vertical = 20
    for i in range(num_vertical + 1):
        x = -TABLE_HALF_WIDTH + (i / num_vertical) * TABLE_HALF_WIDTH * 2
        glBegin(GL_LINES)
        glVertex3f(x, TABLE_HEIGHT + TABLE_THICKNESS/2, 0)
        glVertex3f(x, TABLE_HEIGHT + TABLE_THICKNESS/2 + NET_HEIGHT, 0)
        glEnd()
    
    # Horizontal lines
    num_horizontal = 5
    for i in range(num_horizontal + 1):
        y = TABLE_HEIGHT + TABLE_THICKNESS/2 + (i / num_horizontal) * NET_HEIGHT
        glBegin(GL_LINES)
        glVertex3f(-TABLE_HALF_WIDTH, y, 0)
        glVertex3f(TABLE_HALF_WIDTH, y, 0)
        glEnd()
    
    glLineWidth(1.0)


def draw_environment():
    """Draw floor and background"""
    # Floor (darker for better contrast)
    glColor3f(0.08, 0.09, 0.11)
    floor_y = TABLE_HEIGHT - 4.0
    floor_size = 30.0
    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-floor_size, floor_y, -floor_size)
    glVertex3f(floor_size, floor_y, -floor_size)
    glVertex3f(floor_size, floor_y, floor_size)
    glVertex3f(-floor_size, floor_y, floor_size)
    glEnd()
    
    # Floor grid (subtle)
    glColor3f(0.12, 0.13, 0.15)
    glLineWidth(1.0)
    glBegin(GL_LINES)
    grid_spacing = 2.0
    for i in range(-15, 16):
        # Lines along X
        glVertex3f(-floor_size, floor_y + 0.01, i * grid_spacing)
        glVertex3f(floor_size, floor_y + 0.01, i * grid_spacing)
        # Lines along Z
        glVertex3f(i * grid_spacing, floor_y + 0.01, -floor_size)
        glVertex3f(i * grid_spacing, floor_y + 0.01, floor_size)
    glEnd()

# ============================================================================
# GAME MANAGER
# ============================================================================

class Game:
    """Main game manager"""
    
    def __init__(self, width=1400, height=900):
        pygame.init()
        # Add RESIZABLE flag for window controls (minimize, maximize, close)
        pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL | pygame.RESIZABLE)
        pygame.display.set_caption("3D Ping Pong")
        
        self.width = width
        self.height = height
        
        # OpenGL setup
        self.init_opengl()
        
        # Camera
        self.camera_mode = 'default'
        self.camera_names = list(CAMERA_ANGLES.keys())
        
        # Game objects
        self.player1 = Paddle(-PADDLE_Z_OFFSET, (1.0, 0.0, 0.0))  # Pure Red
        self.player2 = Paddle(PADDLE_Z_OFFSET, (0.0, 0.5, 1.0))   # Cyan Blue
        self.ball = Ball()
        self.particles = ParticleSystem()
        self.quadric = gluNewQuadric()
        
        # Game state
        self.score_p1 = 0
        self.score_p2 = 0
        self.total_points = 0
        self.current_server = 1  # who is serving
        self.game_over = False
        self.winner = None
        self.paused = False
        self.show_fps = False
        self.waiting_for_serve = True  # New: waiting for manual serve
        
        # Timing
        self.clock = pygame.time.Clock()
        self.running = True
        
        # UI
        pygame.font.init()
        self.font_large = pygame.font.SysFont('Arial', 80, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 42)
        self.font_small = pygame.font.SysFont('Arial', 24)
        
        # Don't auto-serve, wait for spacebar
        # self.serve_ball()
        
    def init_opengl(self):
        """Initialize OpenGL settings"""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        
        # Main light (brighter for better visibility)
        glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 15.0, 0.0, 0.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.4, 0.4, 0.4, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))
        
        # Secondary light (fill light)
        glLightfv(GL_LIGHT1, GL_POSITION, (0.0, 8.0, 10.0, 0.0))
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.2, 0.2, 0.2, 1.0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.6, 0.6, 0.6, 1.0))
        
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Material properties for specular highlights
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.8, 0.8, 0.8, 1.0))
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)
        
        glClearColor(0.02, 0.03, 0.05, 1.0)  # Very dark background for contrast
        
        # Projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width / self.height, 0.1, 200.0)
        glMatrixMode(GL_MODELVIEW)
        
    def handle_resize(self, width, height):
        """Handle window resize event"""
        self.width = width
        self.height = height
        
        # Update viewport
        glViewport(0, 0, width, height)
        
        # Update projection matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height, 0.1, 200.0)
        glMatrixMode(GL_MODELVIEW)
        
    def serve_ball(self):
        """Start a new serve"""
        if not self.game_over and not self.waiting_for_serve:
            self.ball.reset(server=self.current_server)
            self.waiting_for_serve = True
            
    def determine_server(self):
        """Determine who should serve based on total points"""
        # In deuce (both >= 10), alternate every point
        if self.score_p1 >= DEUCE_POINT and self.score_p2 >= DEUCE_POINT:
            return 1 if self.total_points % 2 == 0 else 2
        # Otherwise, alternate every 2 points
        return 1 if (self.total_points // 2) % 2 == 0 else 2
        
    def award_point(self, player):
        """Award a point to a player"""
        if player == 1:
            self.score_p1 += 1
        else:
            self.score_p2 += 1
            
        self.total_points += 1
        
        # Check for win
        self.check_win()
        
        if not self.game_over:
            # Determine next server
            self.current_server = self.determine_server()
            self.waiting_for_serve = True
            self.ball.reset(server=self.current_server)
            
    def check_win(self):
        """Check if someone has won"""
        # Must reach POINTS_TO_WIN and lead by WIN_BY
        if self.score_p1 >= POINTS_TO_WIN and self.score_p1 - self.score_p2 >= WIN_BY:
            self.game_over = True
            self.winner = "Player 1 (Red)"
        elif self.score_p2 >= POINTS_TO_WIN and self.score_p2 - self.score_p1 >= WIN_BY:
            self.game_over = True
            self.winner = "Player 2 (Blue)"
            
    def reset_match(self):
        """Reset the entire match"""
        self.score_p1 = 0
        self.score_p2 = 0
        self.total_points = 0
        self.current_server = 1
        self.game_over = False
        self.winner = None
        self.paused = False
        self.waiting_for_serve = True
        self.ball.reset(server=self.current_server)
        
    def toggle_pause(self):
        """Toggle pause state"""
        if not self.game_over:
            self.paused = not self.paused
            
    def cycle_camera(self):
        """Cycle through camera angles"""
        current_idx = self.camera_names.index(self.camera_mode)
        next_idx = (current_idx + 1) % len(self.camera_names)
        self.camera_mode = self.camera_names[next_idx]
        
    def handle_input(self, dt):
        """Handle continuous input (key presses)"""
        if self.paused or self.game_over:
            return
        
        # Allow paddle movement even when waiting for serve
        keys = pygame.key.get_pressed()
        
        # Player 1 (A/D)
        if keys[K_a]:
            self.player1.move_horizontal(-1, dt)
        elif keys[K_d]:
            self.player1.move_horizontal(1, dt)
        else:
            self.player1.target_tilt = 0.0
            
        # Player 2 (Left/Right)
        if keys[K_LEFT]:
            self.player2.move_horizontal(-1, dt)
        elif keys[K_RIGHT]:
            self.player2.move_horizontal(1, dt)
        else:
            self.player2.target_tilt = 0.0
            
    def update(self, dt):
        """Update game state"""
        if self.paused or self.game_over or self.waiting_for_serve:
            return
            
        # Update paddles
        self.player1.update(dt)
        self.player2.update(dt)
        
        # Update ball
        self.ball.update(dt)
        
        # Check table bounce
        if self.ball.bounce_table():
            self.particles.emit(self.ball.x, self.ball.y, self.ball.z, 6)
            
        # Check paddle collisions
        if self.ball.bounce_paddle(self.player1, self.particles):
            pass  # particles emitted in bounce_paddle
        if self.ball.bounce_paddle(self.player2, self.particles):
            pass
            
        # Check if ball went out
        if self.ball.z > TABLE_HALF_DEPTH + 1.5:
            # Player 1 scores (ball passed player 2)
            self.award_point(1)
        elif self.ball.z < -TABLE_HALF_DEPTH - 1.5:
            # Player 2 scores (ball passed player 1)
            self.award_point(2)
        elif self.ball.check_out_of_bounds():
            # Ball went out sideways or down - award to last hitter
            # (simplified: award to opponent of direction ball was traveling)
            if self.ball.vz > 0:
                self.award_point(1)  # was going toward p2, p1 scores
            else:
                self.award_point(2)
                
        # Limit ball speed
        speed = math.sqrt(self.ball.vx**2 + self.ball.vz**2)
        max_speed = 20.0
        if speed > max_speed:
            scale = max_speed / speed
            self.ball.vx *= scale
            self.ball.vz *= scale
            
        # Update particles
        self.particles.update(dt)
        
    def apply_camera(self):
        """Apply current camera transformation"""
        cam = CAMERA_ANGLES[self.camera_mode]
        glLoadIdentity()
        glTranslatef(*cam['pos'])
        glRotatef(cam['rot'][0], 1, 0, 0)
        glRotatef(cam['rot'][1], 0, 1, 0)
        glRotatef(cam['rot'][2], 0, 0, 1)
        
    def render(self):
        """Render the game"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        self.apply_camera()
        
        # Draw environment
        draw_environment()
        
        # Draw table
        draw_table(self.quadric)
        
        # Draw paddles
        self.player1.draw()
        self.player2.draw()
        
        # Draw ball
        self.ball.draw(self.quadric)
        
        # Draw particles
        self.particles.draw(self.quadric)
        
        # Draw UI overlay
        self.draw_ui()
        
        pygame.display.flip()
        
    def draw_text_2d(self, text, x, y, font, color=(255, 255, 255)):
        """Draw 2D text overlay"""
        surf = font.render(text, True, color)
        w, h = surf.get_size()
        
        tex_data = pygame.image.tostring(surf, "RGBA", True)
        
        glPushAttrib(GL_ENABLE_BIT | GL_TRANSFORM_BIT)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x, y)
        glTexCoord2f(1, 1); glVertex2f(x + w, y)
        glTexCoord2f(1, 0); glVertex2f(x + w, y + h)
        glTexCoord2f(0, 0); glVertex2f(x, y + h)
        glEnd()
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        glDeleteTextures([tex_id])
        glPopAttrib()
        
    def draw_ui(self):
        """Draw UI overlays"""
        # Score
        score_text = f"{self.score_p1}  -  {self.score_p2}"
        surf = self.font_large.render(score_text, True, (100, 255, 100))
        w, h = surf.get_size()
        self.draw_text_2d(score_text, self.width // 2 - w // 2, 20, self.font_large, (100, 255, 100))
        
        # Server indicator
        server_text = f"Server: Player {self.current_server}"
        self.draw_text_2d(server_text, 20, 20, self.font_small, (200, 200, 200))
        
        # Camera mode
        cam_text = f"Camera: {self.camera_mode.title()}"
        self.draw_text_2d(cam_text, self.width - 250, 20, self.font_small, (200, 200, 200))
        
        # FPS
        if self.show_fps:
            fps_text = f"FPS: {int(self.clock.get_fps())}"
            self.draw_text_2d(fps_text, self.width - 120, 50, self.font_small, (200, 200, 100))
        
        # Controls
        controls = "P1: A/D | P2: ←/→ | SPACE: Serve | C: Camera | P: Pause | R: Reset"
        self.draw_text_2d(controls, 20, self.height - 35, self.font_small, (150, 150, 150))
        
        # Serve waiting indicator
        if self.waiting_for_serve and not self.game_over and not self.paused:
            serve_text = "Press SPACE to Serve"
            self.draw_text_2d(serve_text, self.width // 2 - 150, self.height // 2, 
                            self.font_medium, (255, 255, 0))
        
        # Pause overlay
        if self.paused:
            pause_text = "PAUSED"
            surf = self.font_large.render(pause_text, True, (255, 255, 0))
            w, h = surf.get_size()
            self.draw_text_2d(pause_text, self.width // 2 - w // 2, self.height // 2 - h // 2, 
                            self.font_large, (255, 255, 0))
            sub_text = "Press P to resume"
            self.draw_text_2d(sub_text, self.width // 2 - 100, self.height // 2 + 50, 
                            self.font_small, (200, 200, 200))
        
        # Game over
        if self.game_over:
            win_text = f"{self.winner} Wins!"
            surf = self.font_large.render(win_text, True, (100, 255, 100))
            w, h = surf.get_size()
            self.draw_text_2d(win_text, self.width // 2 - w // 2, self.height // 2 - h // 2, 
                            self.font_large, (100, 255, 100))
            
            final_score = f"Final Score: {self.score_p1} - {self.score_p2}"
            self.draw_text_2d(final_score, self.width // 2 - 150, self.height // 2 + 60, 
                            self.font_medium, (200, 200, 200))
            
            restart_text = "Press R to play again"
            self.draw_text_2d(restart_text, self.width // 2 - 120, self.height // 2 + 120, 
                            self.font_small, (150, 150, 150))
        
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(MAX_FPS) / 1000.0
            
            # Events
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                    
                if event.type == pygame.VIDEORESIZE:
                    # Handle window resize
                    self.handle_resize(event.w, event.h)
                    
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.running = False
                    elif event.key == K_r:
                        self.reset_match()
                    elif event.key == K_c:
                        self.cycle_camera()
                    elif event.key == K_p:
                        self.toggle_pause()
                    elif event.key == K_f:
                        self.show_fps = not self.show_fps
                    elif event.key == K_SPACE:
                        # Serve button
                        if self.waiting_for_serve and not self.game_over and not self.paused:
                            self.waiting_for_serve = False
                        
            # Input
            self.handle_input(dt)
            
            # Update
            self.update(dt)
            
            # Render
            self.render()
            
        pygame.quit()

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Entry point"""
    game = Game()
    try:
        game.run()
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    main()