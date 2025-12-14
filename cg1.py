from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import sys

# --- Global State Variables ---
state = {
    "x": 0.0,
    "y": 0.0,
    "z": -5.0,  # Camera distance
    "angle_x": 0.0,
    "angle_y": 0.0,
    "scale": 1.0
}


def draw_hexagon_prism():
    radius = 1.0
    height = 0.5

    # Top and bottom faces
    top_vertices = []
    bottom_vertices = []

    for i in range(6):
        angle = math.radians(i * 60)
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        top_vertices.append((x, y, height / 2))
        bottom_vertices.append((x, y, -height / 2))

    # Draw top face
    glColor3f(0, 1, 0)
    glBegin(GL_POLYGON)
    for v in top_vertices:
        glVertex3f(*v)
    glEnd()

    # Draw bottom face
    glColor3f(0, 0.6, 0)
    glBegin(GL_POLYGON)
    for v in bottom_vertices:
        glVertex3f(*v)
    glEnd()

    # Draw side faces
    glColor3f(0, 0.8, 0)
    glBegin(GL_QUADS)
    for i in range(6):
        v1 = top_vertices[i]
        v2 = top_vertices[(i + 1) % 6]
        v3 = bottom_vertices[(i + 1) % 6]
        v4 = bottom_vertices[i]

        glVertex3f(*v1)
        glVertex3f(*v2)
        glVertex3f(*v3)
        glVertex3f(*v4)
    glEnd()


# --------------------------------------------------------
# Display Function
# --------------------------------------------------------
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Camera / Transform
    glTranslatef(state["x"], state["y"], state["z"])
    glScalef(state["scale"], state["scale"], state["scale"])
    glRotatef(state["angle_x"], 1, 0, 0)
    glRotatef(state["angle_y"], 0, 1, 0)

    draw_hexagon_prism()
    glutSwapBuffers()


# --------------------------------------------------------
# Keyboard Controls
# --------------------------------------------------------
def keyboard(key, x, y):
    if key == b'w':
        state["scale"] += 0.1
    elif key == b's':
        state["scale"] = max(0.1, state["scale"] - 0.1)

    elif key == b'a':
        state["angle_y"] -= 5
    elif key == b'd':
        state["angle_y"] += 5

    elif key == b'q':
        state["angle_x"] -= 5
    elif key == b'e':
        state["angle_x"] += 5

    elif key == b'r':
        state["x"] = 0
        state["y"] = 0
        state["z"] = -5
        state["scale"] = 1
        state["angle_x"] = 0
        state["angle_y"] = 0

    elif key == b'\x1b':
        sys.exit()

    glutPostRedisplay()


# Arrow keys move the object
def special_keys(key, x, y):
    if key == GLUT_KEY_UP:
        state["y"] += 0.1
    elif key == GLUT_KEY_DOWN:
        state["y"] -= 0.1
    elif key == GLUT_KEY_LEFT:
        state["x"] -= 0.1
    elif key == GLUT_KEY_RIGHT:
        state["x"] += 0.1

    glutPostRedisplay()


# --------------------------------------------------------
# Window Setup
# --------------------------------------------------------
def init():
    glClearColor(0.1, 0.1, 0.1, 1)
    glEnable(GL_DEPTH_TEST)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, 1, 0.1, 100)

    glMatrixMode(GL_MODELVIEW)


# --------------------------------------------------------
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(600, 600)
    glutCreateWindow(b"3D Hexagon Prism")

    init()
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)

    print("Controls:")
    print("Rotate X: Q / E")
    print("Rotate Y: A / D")
    print("Scale     W / S")
    print("Move      Arrow Keys")
    print("Reset     R")
    print("Exit      ESC")

    glutMainLoop()


if __name__ == "__main__":
    main()
