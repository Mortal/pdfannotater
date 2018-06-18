from PyQt5 import QtGui, QtCore, QtWidgets


class TextItem(QtWidgets.QGraphicsTextItem):
    def __init__(self, page, font=None):
        super().__init__()
        self.page = page
        # self.isHovering=False
        # self.setAcceptHoverEvents(True)
        self.setFlag(self.ItemIsMovable, True)
        self.setFlag(self.ItemIsSelectable, True)
        self.setDefaultTextColor(QtCore.Qt.red)
        document = QtGui.QTextDocument()
        document.setDocumentMargin(0)
        self.setDocument(document)
        self.setPlainText("Hello")
        if font:
            self.setFont(font)
        # self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)

    def save(self, s):
        s.writeQString(self.toHtml())
        s << self.pos()

    def load(self, s):
        html = s.readQString()
        pos = QtCore.QPointF()
        s >> pos
        self.setPos(pos)
        self.setHtml(html)

    def getName(self):
        return "Text"

    @staticmethod
    def id():
        return 3

    def selectAll(self):
        c = self.textCursor()
        c.beginEditBlock()
        c.select(QtGui.QTextCursor.Document)
        c.insertHtml("Boo")
        self.setTextCursor(c)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        c = self.textCursor()
        c.clearSelection()
        self.setTextCursor(c)
        super().focusOutEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.textInteractionFlags() == QtCore.Qt.NoTextInteraction:
            self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        super().mouseDoubleClickEvent(event)
