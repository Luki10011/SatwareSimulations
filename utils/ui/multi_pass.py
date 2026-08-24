import math
from OpenGL import GL
import numpy as np
import pyqtgraph.opengl as gl
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_MODELVIEW,
    GL_PROJECTION,
    glClear,
    glClearColor,
    glDepthMask,
    glEnable,
    glLoadIdentity,
    glLoadMatrixf,
    glMatrixMode,
    glViewport,
)
from PyQt6.QtGui import QMatrix4x4, QVector3D


class MultiPassGLViewWidget(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_items = []
        self.foreground_items = []
        self.sat_position = QVector3D(0, 0, 0)

    def set_satellite_position(self, x: float, y: float, z: float):
        """Ustawia pozycję orbity używaną do orientowania tła."""
        self.sat_position = QVector3D(float(x), float(y), float(z))

    def add_background_item(self, item):
        # Powiadamiamy obiekt o przypisaniu do tego widoku (wymagane przez pyqtgraph)
        item._setView(self)
        if item not in self.background_items:
            self.background_items.append(item)
        if item in self.items:
            self.items.remove(item)

    def add_foreground_item(self, item):
        item._setView(self)
        if item not in self.foreground_items:
            self.foreground_items.append(item)
        if item in self.items:
            self.items.remove(item)

    def addItem(self, item):
        # Domyślnie trafia do foreground
        self.add_foreground_item(item)

    def removeItem(self, item):
        item._setView(None)
        if item in self.background_items:
            self.background_items.remove(item)
        if item in self.foreground_items:
            self.foreground_items.remove(item)
        if item in self.items:
            self.items.remove(item)
        self.update()

    def _apply_projection(self, near, far, viewport):
        w = max(1, int(viewport[2]))
        h = max(1, int(viewport[3]))
        fov = float(self.opts.get("fov", 60.0))

        aspect = w / h
        top = near * math.tan(0.5 * math.radians(fov))
        right = top * aspect

        proj = QMatrix4x4()
        proj.frustum(-right, right, -top, top, near, far)

        self._projectionStack = [proj]

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        mat_data = np.array(proj.copyDataTo(), dtype=np.float32)
        glLoadMatrixf(mat_data)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self, region=None, viewport=None, ev=None):
        self.makeCurrent()
        super().paintGL()

        dpr = self.devicePixelRatio()
        if viewport is None:
            viewport = (0, 0, int(self.width() * dpr), int(self.height() * dpr))

        glViewport(*viewport)

        bgcolor = self.opts.get("bgcolor", (0, 0, 0, 1))
        if isinstance(bgcolor, (tuple, list)):
            glClearColor(*bgcolor)
        else:
            glClearColor(bgcolor.redF(), bgcolor.greenF(), bgcolor.blueF(), bgcolor.alphaF())

        glDepthMask(True)
        glEnable(GL_DEPTH_TEST)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        orig_center = QVector3D(self.opts["center"])

        # ---------------------------------------------------------
        # PRZEBIEG 1: TŁO (Ziemia)
        # ---------------------------------------------------------
        self.opts["center"] = self.sat_position
        self._apply_projection(near=100.0, far=100000.0, viewport=viewport)
        self.setModelview()

        base_modelview = self.currentModelView()

        for item in self.background_items:
            if not item.visible():
                continue

            self._modelViewStack.append(
                base_modelview * item.transform()
            )

            try:
                self.drawItemTree(item)
            finally:
                self._modelViewStack.pop()

        # ---------------------------------------------------------
        # CZYSZCZENIE BUFORA GŁĘBOKOŚCI
        # ---------------------------------------------------------
        glDepthMask(True)
        glEnable(GL_DEPTH_TEST)
        glClear(GL_DEPTH_BUFFER_BIT)

        # ---------------------------------------------------------
        # PRZEBIEG 2: PIERWSZY PLAN (Satelita)
        # ---------------------------------------------------------
        self.opts["center"] = QVector3D(0, 0, 0)

        cam_dist = max(1e-5, float(self.opts.get("distance", 0.005)))
        fg_near = max(1e-5, cam_dist * 0.01)
        fg_far = max(10.0, cam_dist * 100.0)

        self._apply_projection(near=fg_near, far=fg_far, viewport=viewport)
        self.setModelview()

        base_modelview = self.currentModelView()

        for item in self.foreground_items:
            if not item.visible():
                continue

            self._modelViewStack.append(
                base_modelview * item.transform()
            )

            try:
                self.drawItemTree(item)
            finally:
                self._modelViewStack.pop()

        self.opts["center"] = orig_center