from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math

# --------------------------
# GLOBAL TRANSFORM STATES
# --------------------------
camera = {
    "rot_x": 20,
    "rot_y": -30,
    "zoom": -6,
    "pan_x": 0,
    "pan_y": 0
}

obj = {
    "rot_x": 0,
    "rot_y": 0,
    "rot_z": 0,
    "tx": 0,
    "ty": 0,
    "tz": 0,
    "scale": 1.0
}

# ---------------------------------------
# TETRAHEDRON VERTICES + COLOR PER FACE
# ---------------------------------------
vertices = [
    [0.0, 1.0, 0.0],        # Top vertex
    [-1.0, -1.0, 1.0],      # Front-left
    [1.0, -1.0, 1.0],       # Front-right
    [0.0, -1.0, -1.0]       # Back
]

faces = [
    [0, 1, 2],   # Front face
    [0, 2, 3],   # Right face
    [0, 3, 1],   # Left face
    [1, 3, 2]    # Bottom face
]

colors = [
    [1, 0, 0],   # Red
    [0, 1, 0],   # Green
    [0, 0, 1],   # Blue
    [1, 1, 0]    # Yellow
]

# --------------------------
# DRAW TETRAHEDRON
# --------------------------
def draw_tetrahedron():
    glBegin(GL_TRIANGLES)
    for i, face in enumerate(faces):
        glColor3fv(colors[i])
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()

# ---------------------------------------
# RENDER LOOP
# ---------------------------------------
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # CAMERA TRANSFORMS
    glTranslatef(camera["pan_x"], camera["pan_y"], camera["zoom"])
    glRotatef(camera["rot_x"], 1, 0, 0)
    glRotatef(camera["rot_y"], 0, 1, 0)

    # OBJECT TRANSFORMS
    glTranslatef(obj["tx"], obj["ty"], obj["tz"])
    glScalef(obj["scale"], obj["scale"], obj["scale"])
    glRotatef(obj["rot_x"], 1, 0, 0)
    glRotatef(obj["rot_y"], 0, 1, 0)
    glRotatef(obj["rot_z"], 0, 0, 1)

    draw_tetrahedron()

    glutSwapBuffers()

# ---------------------------------------
# KEYBOARD INPUT
# ---------------------------------------
def keyboard(key, x, y):
    global obj, camera

    key = key.decode("utf-8")

    # SCALE OBJECT
    if key == '+': obj["scale"] += 0.1
    if key == '-': obj["scale"] -= 0.1

    # OBJECT TRANSLATION
    if key == 't': obj["ty"] += 0.1
    if key == 'f': obj["tx"] -= 0.1
    if key == 'h': obj["tx"] += 0.1
    if key == 'g': obj["ty"] -= 0.1
    if key == 'r': obj["tz"] += 0.1
    if key == 'y': obj["tz"] -= 0.1

    # OBJECT ROTATION
    if key == 'i': obj["rot_x"] += 5
    if key == 'k': obj["rot_x"] -= 5
    if key == 'j': obj["rot_y"] -= 5
    if key == 'l': obj["rot_y"] += 5
    if key == 'u': obj["rot_z"] -= 5
    if key == 'o': obj["rot_z"] += 5

    # CAMERA ZOOM
    if key == 'z': camera["zoom"] += 0.2
    if key == 'x': camera["zoom"] -= 0.2

    # CAMERA PAN
    if key == 'w': camera["pan_y"] += 0.1
    if key == 's': camera["pan_y"] -= 0.1
    if key == 'a': camera["pan_x"] -= 0.1
    if key == 'd': camera["pan_x"] += 0.1

    glutPostRedisplay()

# ---------------------------------------
# ARROW KEYS → CAMERA ROTATION
# ---------------------------------------
def special_input(key, x, y):
    if key == GLUT_KEY_UP: camera["rot_x"] += 3
    if key == GLUT_KEY_DOWN: camera["rot_x"] -= 3
    if key == GLUT_KEY_LEFT: camera["rot_y"] -= 3
    if key == GLUT_KEY_RIGHT: camera["rot_y"] += 3

    glutPostRedisplay()

# ---------------------------------------
# SETUP
# ---------------------------------------
def init():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.1, 0.1, 0.1, 1)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, 1, 0.1, 100)

    glMatrixMode(GL_MODELVIEW)

# ---------------------------------------
# MAIN
# ---------------------------------------
glutInit()
glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
glutInitWindowSize(800, 600)
glutCreateWindow(b"Tetrahedron 3D - Full Transform Controls")

init()
glutDisplayFunc(display)
glutKeyboardFunc(keyboard)
glutSpecialFunc(special_input)
glutMainLoop()
