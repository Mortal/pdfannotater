from PyQt5 import QtGui, QtCore, QtWidgets


class GeometryCommand(QtWidgets.QUndoCommand):
    def __init__(self, item, f, t, text):
        super().__init__(text)
        self.item = item
        self.f = f
        self.t = t

    def undo(self):
        self.item.changeRect(self.f)

    def redo(self):
        self.item.changeRect(self.t)


class ItemBase(QtWidgets.QGraphicsItem):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.startRect = None
        self.isHovering = False
        self.setAcceptHoverEvents(True)
        self.resizeTop = False
        self.resizeBottom = False
        self.resizeLeft = False
        self.resizeRight = False
        self.moveStart = None
        self.setFlag(self.ItemIsMovable, True)
        self.setFlag(self.ItemIsSelectable, True)
        self.properties = ["width", "height", "top", "left"]

    def boundingRect(self):
        r = QtCore.QRectF(self.innerRect)
        r.setLeft(r.left() - 2)
        r.setTop(r.top() - 2)
        r.setRight(r.right() + 2)
        r.setBottom(r.bottom() + 2)
        return r

    def changeRect(self, r):
        self.prepareGeometryChange()
        self.innerRect = r

    def paint(self, painter, option, widget):
        if self.isHovering or self.isSelected():
            if self.isSelected():
                pen = QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.SolidLine)
            else:
                pen = QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.DotLine)

            # painter.setCompositionMode(QtGui.QPainter.RasterOp_SourceXorDestination)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            r = QtCore.QRectF(self.innerRect)
            r.setLeft(r.left() - 1)
            r.setTop(r.top() - 1)
            r.setRight(r.right() + 1)
            r.setBottom(r.bottom() + 1)
            painter.drawRect(self.boundingRect())

    def onLeft(self, pos):
        return pos.x() <= self.innerRect.left() + 3

    def onRight(self, pos):
        return pos.x() >= self.innerRect.right() - 3

    def onTop(self, pos):
        return pos.y() <= self.innerRect.top() + 3

    def onBottom(self, pos):
        return pos.y() >= self.innerRect.bottom() - 3

    def mousePressEvent(self, event):
        p = event.pos()
        self.resizeTop = self.resizeBottom = False
        self.resizeLeft = self.resizeRight = False
        self.moveStart = None
        self.startRect = QtCore.QRectF(self.innerRect)
        self.myEvent = False
        if event.button() == QtCore.Qt.LeftButton:
            # self.page.select(self)
            if event.modifiers() != QtCore.Qt.ControlModifier:
                self.resizeTop = self.onTop(p)
                self.resizeBottom = self.onBottom(p)
                self.resizeLeft = self.onLeft(p)
                self.resizeRight = self.onRight(p)

            if (
                not self.resizeTop
                and not self.resizeBottom
                and not self.resizeLeft
                and not self.resizeRight
            ):
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    self.moveStart = (self.innerRect.topLeft(), p)
                    self.myEvent = True
                else:
                    super().mousePressEvent(event)
            else:
                self.myEvent = True
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.myEvent:
            p = event.pos()
            self.prepareGeometryChange()
            if self.resizeTop:
                self.innerRect.setTop(p.y())
            if self.resizeBottom:
                self.innerRect.setBottom(p.y())
            if self.resizeLeft:
                self.innerRect.setLeft(p.x())
            if self.resizeRight:
                self.innerRect.setRight(p.x())
            self.commandName = "Resize item"
            if self.moveStart:
                self.innerRect.moveTo(
                    self.moveStart[0].x() + p.x() - self.moveStart[1].x(),
                    self.moveStart[0].y() + p.y() - self.moveStart[1].y(),
                )
                self.commandName = "Move item"
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.myEvent:
            if self.innerRect != self.startRect:
                GeometryCommand(
                    self,
                    self.startRect,
                    QtCore.QRectF(self.innerRect),
                    self.commandName,
                )
        else:
            super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        self.isHovering = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.isHovering = False
        self.update()

    def hoverMoveEvent(self, event):
        p = event.pos()
        if self.onLeft(p) and self.onTop(p):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.onRight(p) and self.onBottom(p):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.onRight(p) and self.onTop(p):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        elif self.onLeft(p) and self.onBottom(p):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        elif self.onLeft(p) or self.onRight(p):
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif self.onTop(p) or self.onBottom(p):
            self.setCursor(QtCore.Qt.SizeVerCursor)
        else:
            self.setCursor(QtCore.Qt.OpenHandCursor)


class ImageItem(ItemBase):
    def __init__(self, page):
        ItemBase.__init__(self, page)
        self.image = QtGui.QImage("/home/jakobt/tux2.png")
        self.innerRect = QtCore.QRectF(
            100, 100, self.image.width(), self.image.height()
        )

    def paint(self, painter, option, widget):
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.drawImage(
            self.innerRect,
            self.image,
            QtCore.QRectF(0, 0, self.image.width(), self.image.height()),
        )
        ItemBase.paint(self, painter, option, widget)

    def getName(self):
        return "Image"

    def save(self, s, version):
        s << self.image
        s << self.innerRect

    @staticmethod
    def id():
        return 1


class RectItem(ItemBase):
    def __init__(self, page):
        ItemBase.__init__(self, page)
        self.innerRect = QtCore.QRectF(0, 0, 100, 100)
        self.pen = QtGui.QPen(QtCore.Qt.black, 2)
        self.brush = QtCore.Qt.blue

    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRect(self.innerRect)
        ItemBase.paint(self, painter, option, widget)

    def getName(self):
        return "Rect"

    def save(self, stream):
        stream << self.innerRect

    @staticmethod
    def id():
        return 2
