from PyQt5 import QtGui, QtWidgets, QtCore


class PageView(QtWidgets.QGraphicsView):
    zoomChanged = QtCore.pyqtSignal()
    pageChanged = QtCore.pyqtSignal()
    currentPage = None

    def __init__(self, parent):
        super().__init__(parent)
        self.zoom = 1

    def updateTransform(self):
        t = QtGui.QTransform()
        t.scale(self.zoom, self.zoom)
        self.setTransform(t)
        self.zoomChanged.emit()

    def zoomReset(self):
        self.zoom = 1
        self.updateTransform()

    def zoomIn(self):
        self.zoom *= 1.5
        self.updateTransform()

    def zoomOut(self):
        self.zoom /= 1.5
        self.updateTransform()

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            pixel_delta = event.pixelDelta()
            if pixel_delta.x() != 0 or pixel_delta.y() != 0:
                self.zoom *= 2.0 ** (pixel_delta.y() / 300.0)
            else:
                self.zoom *= 2.0 ** (event.angleDelta().y() / 300.0)
            self.updateTransform()
        else:
            super().wheelEvent(event)

    def currentPageChanged(self, page):
        self.currentPage = page
        self.setScene(page.scene if page else None)
        self.pageChanged.emit()
