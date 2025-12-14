from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

# ---------------- GLOBAL STATE ----------------

# Camera position and rotation
camera_pos = [0.0, 0.0, 8.0]  # x, y, z
camera_rot = [20.0, -30.0]   # pitch (x), yaw (y)
camera_fov = 60

# Object transform
obj_pos = [0.0, 0.0, 0.0]
obj_rot = [0.0, 0.0, 0.0]
obj_scale = 1.0

# Shape: 0 = cone, 1 = cylinder
shape_type = 0


# ---------------- DRAWING ----------------

def draw_cone():
    glPushMatrix()
    glTranslatef(*obj_pos)
    glRotatef(obj_rot[0], 1, 0, 0)
    glRotatef(obj_rot[1], 0, 1, 0)
    glRotatef(obj_rot[2], 0, 0, 1)
    glScalef(obj_scale, obj_scale, obj_scale)

    slices = 40
    radius = 1.0
    height = 2.0

    glBegin(GL_TRIANGLES)
    for i in range(slices):
        angle1 = 2 * math.pi * i / slices
        angle2 = 2 * math.pi * (i + 1) / slices

        x1, y1 = radius * math.cos(angle1), radius * math.sin(angle1)
        x2, y2 = radius * math.cos(angle2), radius * math.sin(angle2)

        glColor3f(abs(math.sin(angle1)), abs(math.cos(angle1)), abs(math.sin(angle2)))

        glVertex3f(0, 0, height)
        glVertex3f(x1, y1, 0)
        glVertex3f(x2, y2, 0)
    glEnd()

    glPopMatrix()


def draw_cylinder():
    glPushMatrix()
    glTranslatef(*obj_pos)
    glRotatef(obj_rot[0], 1, 0, 0)
    glRotatef(obj_rot[1], 0, 1, 0)
    glRotatef(obj_rot[2], 0, 0, 1)
    glScalef(obj_scale, obj_scale, obj_scale)

    slices = 40
    radius = 1.0
    height = 2.0

    # Side
    glBegin(GL_QUAD_STRIP)
    for i in range(slices + 1):
        angle = 2 * math.pi * i / slices
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)

        glColor3f(abs(math.sin(angle)), abs(math.cos(angle)), abs(math.sin(angle * 2)))

        glVertex3f(x, y, 0)
        glVertex3f(x, y, height)
    glEnd()

    # Top cap
    glBegin(GL_TRIANGLE_FAN)
    glColor3f(1, 0.2, 0.2)
    glVertex3f(0, 0, height)
    for i in range(slices + 1):
        angle = 2 * math.pi * i / slices
        glVertex3f(radius * math.cos(angle), radius * math.sin(angle), height)
    glEnd()

    # Bottom cap
    glBegin(GL_TRIANGLE_FAN)
    glColor3f(0.2, 0.2, 1)
    glVertex3f(0, 0, 0)
    for i in range(slices + 1):
        angle = 2 * math.pi * i / slices
        glVertex3f(radius * math.cos(angle), radius * math.sin(angle), 0)
    glEnd()

    glPopMatrix()


# ---------------- SCENE ----------------

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Camera rotation
    glRotatef(camera_rot[0], 1, 0, 0)
    glRotatef(camera_rot[1], 0, 1, 0)

    # Camera translation
    glTranslatef(-camera_pos[0], -camera_pos[1], -camera_pos[2])

    # Draw selected shape
    if shape_type == 0:
        draw_cone()
    else:
        draw_cylinder()

    glutSwapBuffers()


def reshape(w, h):
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(camera_fov, w / h, 0.1, 100)

    glMatrixMode(GL_MODELVIEW)


# ---------------- CONTROLS ----------------

def keyboard(key, x, y):
    global shape_type, camera_pos, obj_rot, obj_pos, obj_scale, camera_fov

    key = key.decode("utf-8")

    # ---------- Shape Toggle ----------
    if key == "c":
        shape_type = 0
    if key == "y":
        shape_type = 1

    # ---------- Camera Movement ----------
    step = 0.2

    if key == "w":
        camera_pos[2] -= step
    if key == "s":
        camera_pos[2] += step
    if key == "a":
        camera_pos[0] -= step
    if key == "d":
        camera_pos[0] += step
    if key == "q":
        camera_pos[1] += step
    if key == "e":
        camera_pos[1] -= step

    # ---------- Object Movement ----------
    if key == "t":
        obj_pos[1] += step
    if key == "g":
        obj_pos[1] -= step
    if key == "f":
        obj_pos[0] -= step
    if key == "h":
        obj_pos[0] += step
    if key == "v":
        obj_pos[2] += step
    if key == "b":
        obj_pos[2] -= step

    # ---------- Object Rotation ----------
    rot_speed = 5
    if key == "i":
        obj_rot[0] += rot_speed
    if key == "k":
        obj_rot[0] -= rot_speed
    if key == "j":
        obj_rot[1] += rot_speed
    if key == "l":
        obj_rot[1] -= rot_speed
    if key == "u":
        obj_rot[2] += rot_speed
    if key == "o":
        obj_rot[2] -= rot_speed

    # ---------- Object Scale ----------
    if key == ",":
        obj_scale -= 0.05
    if key == ".":
        obj_scale += 0.05

    # ---------- Reset ----------
    if key == "r":
        obj_pos[:] = [0, 0, 0]
        obj_rot[:] = [0, 0, 0]
        obj_scale = 1.0

    glutPostRedisplay()


def special_keys(key, x, y):
    global camera_rot

    # Arrow keys rotate camera
    rot_speed = 3

    if key == GLUT_KEY_UP:
        camera_rot[0] += rot_speed
    if key == GLUT_KEY_DOWN:
        camera_rot[0] -= rot_speed
    if key == GLUT_KEY_LEFT:
        camera_rot[1] += rot_speed
    if key == GLUT_KEY_RIGHT:
        camera_rot[1] -= rot_speed

    glutPostRedisplay()


def init():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.1, 0.1, 0.1, 1)


# ---------------- MAIN ----------------

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(900, 600)
    glutCreateWindow(b"Camera Orbit (gluLookAt) - Multi-color Cone")

    init()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special_keys)

    glutMainLoop()


if __name__ == "__main__":
    main()
