from PyQt5 import QtGui, QtCore, QtWidgets


class StrikethroughItem(QtWidgets.QGraphicsLineItem):
    def __init__(self, page, line_bbox=None):
        super().__init__()
        self.set_line_bbox(line_bbox)
        self.page = page
        self.setFlag(self.ItemIsMovable, True)
        self.setFlag(self.ItemIsSelectable, True)
        self.setPen(QtGui.QPen(QtGui.QBrush(QtCore.Qt.red), 1))

    def boundingRect(self):
        return self.line_bbox

    def contains(self, point):
        return self.line_bbox.contains(point)

    def shape(self):
        painter_path = QtGui.QPainterPath()
        painter_path.addRect(self.line_bbox)
        return painter_path

    def save(self, stream, version):
        stream << self.line_bbox

    def load(self, stream, version):
        line_bbox = QtCore.QRectF()
        stream >> line_bbox
        self.set_line_bbox(line_bbox)

    def set_line_bbox(self, line_bbox):
        self.line_bbox = line_bbox
        if line_bbox is not None:
            y = line_bbox.top() + line_bbox.height() / 2
            self.setLine(line_bbox.left(), y, line_bbox.right(), y)

    def getName(self):
        return "Strikethrough"

    @staticmethod
    def id():
        return 4
