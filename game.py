"""
Ping pong 3D 
Match is "first to 5" wins. Score displayed on-screen.
Controls:
    Player 1 (back): A / D
    Player 2 (front): Left / Right
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
    QUIT,
    KEYDOWN,
)
from OpenGL.GL import *
from OpenGL.GLU import *
# === Game constants ===
# Field size (wide and deep)
TABLE_HALF_WIDTH = 5.0    # x range: -5 .. 5
TABLE_HALF_DEPTH = 8.0    # z range: -8 .. 8
# Paddle size: width (x), height (y), depth (z)
PADDLE_WIDTH = 1.2        # horizontal size
PADDLE_HEIGHT_P1 = 1.6    # Player 1 tall paddle
PADDLE_HEIGHT_P2 = 0.9    # Player 2 shorter (blue) paddle
PADDLE_DEPTH = 0.3        # thickness
PADDLE_Z_OFFSET = 6.0     # distance from center for paddles (front/back)
BALL_RADIUS = 0.16
BALL_SPEED = 6.0          # primary speed along z
MAX_FPS = 120
FIRST_TO = 5              # first to 5 wins
# === Entities ===
class Paddle:
    def __init__(self, z, height):
        self.z = z
        self.x = 0.0
        self.width = PADDLE_WIDTH
        self.height = height
        self.depth = PADDLE_DEPTH
        self.speed = 7.0
    def move_horizontal(self, dx, dt):
        # dx is -1..1 (direction), dt in seconds
        self.x += dx * self.speed * dt
        limit = TABLE_HALF_WIDTH - self.width / 2 - 0.05
        if self.x > limit:
            self.x = limit
        if self.x < -limit:
            self.x = -limit
    def draw(self):
        glPushMatrix()
        # paddle is centered at (x, height/2, z) so its base sits on the table
        glTranslatef(self.x, self.height / 2.0, self.z)
        glScalef(self.width, self.height, self.depth)
        draw_unit_cube()
        glPopMatrix()
class Ball:
    def __init__(self):
        self.reset()
    def reset(self, toward_player1=None):
        # toward_player1: True -> serve towards player1 (back/negative z)
        #                 False -> serve towards player2 (front/positive z)
        self.x = 0.0
        self.z = 0.0
        angle_deg = random.uniform(-20, 20)
        angle = math.radians(angle_deg)
        if toward_player1 is None:
            dir = random.choice([-1, 1])
        else:
            dir = -1 if toward_player1 else 1
        # primary velocity along z, small vx from angle
        self.vz = dir * BALL_SPEED * math.cos(angle)
        self.vx = BALL_SPEED * math.sin(angle)
    def update(self, dt):
        self.x += self.vx * dt
        self.z += self.vz * dt
    def draw(self, quadric):
        glPushMatrix()
        glTranslatef(self.x, BALL_RADIUS, self.z)  # draw ball above table
        glColor3f(1.0, 0.9, 0.2)
        gluSphere(quadric, BALL_RADIUS, 22, 22)
        glPopMatrix()
# === Drawing helpers ===
def draw_unit_cube():
    # centered cube (-0.5 .. 0.5)
    glBegin(GL_QUADS)
    # Front (positive z)
    glNormal3f(0, 0, 1)
    glVertex3f(-0.5, -0.5, 0.5)
    glVertex3f(0.5, -0.5, 0.5)
    glVertex3f(0.5, 0.5, 0.5)
    glVertex3f(-0.5, 0.5, 0.5)
    # Back (negative z)
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
# === Game class ===
class Game:
    def __init__(self, width=1400, height=900, title="Ping Pong"):
        pygame.init()
        pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption(title)
        self.width = width
        self.height = height
        self.title = title
        # OpenGL init
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (0.5, 1.0, 0.8, 0.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.18, 0.18, 0.18, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.85, 0.85, 0.85, 1.0))
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glClearColor(0.04, 0.07, 0.10, 1.0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (width / height), 0.1, 160.0)
        glMatrixMode(GL_MODELVIEW)
        # Game objects: paddles located at front (+z) and back (-z)
        self.player1 = Paddle(-PADDLE_Z_OFFSET, PADDLE_HEIGHT_P1)  # back (Player 1) - taller
        self.player2 = Paddle(PADDLE_Z_OFFSET, PADDLE_HEIGHT_P2)   # front (Player 2) - shorter (blue)
        self.ball = Ball()
        self.quadric = gluNewQuadric()
        self.score_p1 = 0
        self.score_p2 = 0
        self.clock = pygame.time.Clock()
        self.running = True
        # gameplay flags
        self.game_over = False
        self.winner = None
        # font for overlay
        pygame.font.init()
        self.font_large = pygame.font.SysFont(None, 92)
        self.font_medium = pygame.font.SysFont(None, 48)
        self.font_small = pygame.font.SysFont(None, 28)
        # initial caption
        pygame.display.set_caption(f"{self.title} — Score {self.score_p1} : {self.score_p2}")
    def reset_ball(self, toward_player1=None):
        # won't serve if match is over
        if self.game_over:
            return
        self.ball.reset(toward_player1)
    def reset_match(self):
        self.score_p1 = 0
        self.score_p2 = 0
        self.game_over = False
        self.winner = None
        pygame.display.set_caption(f"{self.title} — Score {self.score_p1} : {self.score_p2}")
        self.ball.reset()
    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        # Player 1: A / D
        if keys[K_a]:
            self.player1.move_horizontal(-1, dt)
        if keys[K_d]:
            self.player1.move_horizontal(1, dt)
        # Player 2: Left / Right arrows
        if keys[K_LEFT]:
            self.player2.move_horizontal(-1, dt)
        if keys[K_RIGHT]:
            self.player2.move_horizontal(1, dt)
    def check_win(self):
        if self.score_p1 >= FIRST_TO:
            self.game_over = True
            self.winner = "Player 1"
            self.ball.vx = self.ball.vz = 0.0
            pygame.display.set_caption(f"{self.title} — {self.winner} wins {self.score_p1} : {self.score_p2}  (Press R to restart)")
        elif self.score_p2 >= FIRST_TO:
            self.game_over = True
            self.winner = "Player 2"
            self.ball.vx = self.ball.vz = 0.0
            pygame.display.set_caption(f"{self.title} — {self.winner} wins {self.score_p1} : {self.score_p2}  (Press R to restart)")
    def check_collisions(self):
        # Ball x bounds (bounce off left/right table edges)
        limit_x = TABLE_HALF_WIDTH - BALL_RADIUS
        if self.ball.x > limit_x:
            self.ball.x = limit_x
            self.ball.vx *= -1
        if self.ball.x < -limit_x:
            self.ball.x = -limit_x
            self.ball.vx *= -1
        # Player 1 collision (player1 at negative z)
        p1_front_z = self.player1.z + self.player1.depth / 2  # front-most z for player1 (less negative)
        if self.ball.vz < 0 and (self.ball.z - BALL_RADIUS) <= p1_front_z:
            # check horizontal overlap (x)
            if abs(self.ball.x - self.player1.x) <= (self.player1.width / 2 + BALL_RADIUS):
                # collision: reflect vz and slightly speed up
                self.ball.z = p1_front_z + BALL_RADIUS + 1e-4
                self.ball.vz = -self.ball.vz * 1.08
                # add vx based on hit horizontal offset
                offset = (self.ball.x - self.player1.x) / (self.player1.width / 2)
                self.ball.vx += offset * 2.2
        # Player 2 collision (player2 at positive z)
        p2_back_z = self.player2.z - self.player2.depth / 2  # back-most z for player2 (less positive)
        if self.ball.vz > 0 and (self.ball.z + BALL_RADIUS) >= p2_back_z:
            if abs(self.ball.x - self.player2.x) <= (self.player2.width / 2 + BALL_RADIUS):
                self.ball.z = p2_back_z - BALL_RADIUS - 1e-4
                self.ball.vz = -self.ball.vz * 1.08
                offset = (self.ball.x - self.player2.x) / (self.player2.width / 2)
                self.ball.vx += offset * 2.2
        # Scoring: ball past paddles along z axis (only if not game over)
        if not self.game_over:
            if self.ball.z < -TABLE_HALF_DEPTH - 0.8:
                # Player 2 scores
                self.score_p2 += 1
                pygame.display.set_caption(f"{self.title} — Score {self.score_p1} : {self.score_p2}")
                self.check_win()
                if not self.game_over:
                    # serve toward the player who was scored on next (toward player1 = False)
                    self.ball.reset(toward_player1=False)
            if self.ball.z > TABLE_HALF_DEPTH + 0.8:
                # Player 1 scores
                self.score_p1 += 1
                pygame.display.set_caption(f"{self.title} — Score {self.score_p1} : {self.score_p2}")
                self.check_win()
                if not self.game_over:
                    self.ball.reset(toward_player1=True)
        # Limit ball speed
        speed = math.hypot(self.ball.vx, self.ball.vz)
        max_speed = 16.0
        if speed > max_speed:
            scale = max_speed / speed
            self.ball.vx *= scale
            self.ball.vz *= scale
    def draw_table(self):
        # Table top
        glColor3f(0.04, 0.40, 0.04)
        glBegin(GL_QUADS)
        glNormal3f(0, 1, 0)
        glVertex3f(-TABLE_HALF_WIDTH, 0.0, -TABLE_HALF_DEPTH)
        glVertex3f(TABLE_HALF_WIDTH, 0.0, -TABLE_HALF_DEPTH)
        glVertex3f(TABLE_HALF_WIDTH, 0.0, TABLE_HALF_DEPTH)
        glVertex3f(-TABLE_HALF_WIDTH, 0.0, TABLE_HALF_DEPTH)
        glEnd()
        # Net (simple line at z=0)
        glColor3f(0.92, 0.92, 0.92)
        glBegin(GL_LINES)
        glVertex3f(-TABLE_HALF_WIDTH, 0.02, 0.0)
        glVertex3f(TABLE_HALF_WIDTH, 0.02, 0.0)
        glEnd()
        # Boundary lines (left/right)
        glColor3f(0.9, 0.9, 0.9)
        glBegin(GL_LINES)
        glVertex3f(-TABLE_HALF_WIDTH, 0.02, -TABLE_HALF_DEPTH)
        glVertex3f(-TABLE_HALF_WIDTH, 0.02, TABLE_HALF_DEPTH)
        glVertex3f(TABLE_HALF_WIDTH, 0.02, -TABLE_HALF_DEPTH)
        glVertex3f(TABLE_HALF_WIDTH, 0.02, TABLE_HALF_DEPTH)
        glEnd()
    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        # Camera transform: move camera back and down (to show taller paddles)
        glTranslatef(0.0, -4.0, -30.0)
        glRotatef(18, 1, 0, 0)
        # Table
        self.draw_table()
        # Paddles (player1 back is red, player2 front is blue)
        glColor3f(0.86, 0.12, 0.12)
        self.player1.draw()
        glColor3f(0.14, 0.18, 0.86)
        self.player2.draw()
        # Ball
        self.ball.draw(self.quadric)
        # Draw 2D overlay
        self.draw_overlay()
        # Swap buffers
        pygame.display.flip()
    def draw_text_texture(self, surf, x, y):
        """Render a pygame surface to the screen at pixel coords (x,y) using an OpenGL texture."""
        text_width, text_height = surf.get_size()
        if text_width == 0 or text_height == 0:
            return
        tex_data = pygame.image.tostring(surf, "RGBA", True)
        glPushAttrib(GL_ENABLE_BIT | GL_TRANSFORM_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, tex_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # Setup orthographic projection to blit in pixel coordinates
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        # Draw textured quad (flipped texture coordinates to correct orientation)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x, y)
        glTexCoord2f(1, 1); glVertex2f(x + text_width, y)
        glTexCoord2f(1, 0); glVertex2f(x + text_width, y + text_height)
        glTexCoord2f(0, 0); glVertex2f(x, y + text_height)
        glEnd()
        # Restore matrices and cleanup
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glDeleteTextures([tex_id])
        glPopAttrib()
    def draw_overlay(self):
        # Score top-center
        score_text = f"{self.score_p1}  :  {self.score_p2}"
        surf = self.font_large.render(score_text, True, (0, 255, 0))
        sw, sh = surf.get_size()
        self.draw_text_texture(surf, int(self.width / 2 - sw / 2), 18)
        # Instructions small
        instr = "Player 1: A/D  |  Player 2: Left/Right  |  R: Reset match"
        instr_s = self.font_small.render(instr, True, (0, 255, 0))
        iw, ih = instr_s.get_size()
        self.draw_text_texture(instr_s, int(self.width / 2 - iw / 2), self.height - ih - 14)
        # If game over, draw winner message
        if self.game_over and self.winner:
            win_surf = self.font_medium.render(f"{self.winner} Wins!", True, (0, 255, 0))
            ws, hs = win_surf.get_size()
            self.draw_text_texture(win_surf, int(self.width / 2 - ws / 2), int(self.height / 2 - hs / 2))
            sub = self.font_small.render("Press R to restart the match", True, (255, 255, 255))
            subw, subh = sub.get_size()
            self.draw_text_texture(sub, int(self.width / 2 - subw / 2), int(self.height / 2 + hs / 2 + 10))
    def run(self):
        while self.running:
            dt = self.clock.tick(MAX_FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.running = False
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.running = False
                    if event.key == K_r:
                        # Reset entire match
                        self.reset_match()
            if not self.game_over:
                self.handle_input(dt)
                # Physics update
                self.ball.update(dt)
                self.check_collisions()
            # Render (always render so overlay still shows when game_over)
            self.render()
        pygame.quit()
# === Entry point ===
def main():
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