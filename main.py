from OpenGL.GL import *
from OpenGL.GLUT import *
import math

# --- Global State Variables ---
# We store the state of the hexagon here so we can modify it with keys
state = {
    "x": 0.0,
    "y": 0.0,
    "angle": 0.0,
    "scale": 1.0
}


def draw_hexagon():
    glBegin(GL_POLYGON)
    radius = 0.2
    for i in range(6):
        angle_deg = 60 * i
        angle_rad = math.radians(angle_deg)
        x = radius * math.cos(angle_rad)
        y = radius * math.sin(angle_rad)
        glVertex2f(x, y)
    glEnd()


def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glLoadIdentity()

    # --- APPLY TRANSFORMATIONS BASED ON USER INPUT ---
    # 1. Translate (Move)
    glTranslatef(state["x"], state["y"], 0.0)

    # 2. Rotate
    glRotatef(state["angle"], 0.0, 0.0, 1.0)

    # 3. Scale
    glScalef(state["scale"], state["scale"], 1.0)

    # Draw logic
    glColor3f(0.0, 1.0, 0.0)  # Green color
    draw_hexagon()

    glutSwapBuffers()


def keyboard(key, x, y):
    global state

    # Scaling (W = Grow, S = Shrink)
    if key == b'w':
        state["scale"] += 0.1
    elif key == b's':
        state["scale"] = max(0.1, state["scale"] - 0.1)  # Prevent scale from going negative

    # Rotation (A = Left, D = Right)
    elif key == b'a':
        state["angle"] += 5.0
    elif key == b'd':
        state["angle"] -= 5.0

    # Reset (R key)
    elif key == b'r':
        state["x"] = 0.0
        state["y"] = 0.0
        state["angle"] = 0.0
        state["scale"] = 1.0

    # Escape key to exit (ASCII 27)
    elif key == b'\x1b':
        sys.exit()

    # Tell GLUT to redraw the screen now that variables changed
    glutPostRedisplay()


# --- INPUT HANDLER: Special Keys ---
# Handles Arrow keys, Function keys, Home/End, etc.
def special_keys(key, x, y):
    global state
    step = 0.05

    # Translation (Arrow Keys)
    if key == GLUT_KEY_UP:
        state["y"] += step
    elif key == GLUT_KEY_DOWN:
        state["y"] -= step
    elif key == GLUT_KEY_LEFT:
        state["x"] -= step
    elif key == GLUT_KEY_RIGHT:
        state["x"] += step

    glutPostRedisplay()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA)
    glutInitWindowSize(600, 600)
    glutCreateWindow(b"Control the Hexagon")

    glClearColor(0.1, 0.1, 0.1, 1.0)  # Dark Grey Background

    # Register the Display Function
    glutDisplayFunc(display)

    # Register the Keyboard Functions
    glutKeyboardFunc(keyboard)  # For W, A, S, D, R
    glutSpecialFunc(special_keys)  # For Arrow Keys

    print("Controls:")
    print("[Arrow Keys] Move Position")
    print("[A] / [D]    Rotate Left/Right")
    print("[W] / [S]    Scale Up/Down")
    print("[R]          Reset")

    glutMainLoop()


if __name__ == "__main__":
    main()
