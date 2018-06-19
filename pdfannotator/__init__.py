import popplerqt5
from PyQt5 import QtGui, QtCore, QtWidgets, uic, QtPrintSupport
import os
import subprocess
from .widgets.textitem import TextItem
from .widgets.pdfpageitem import PdfPageItem
from .widgets.item import ItemBase, ImageItem, RectItem
from .widgets.strikethrough import StrikethroughItem


class ObjectTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, project):
        QtCore.QAbstractItemModel.__init__(self)
        self.project = project

    def columnCount(self, parent):
        return 1

    def rowCount(self, parent):
        p = self.project
        if parent.isValid():
            p = parent.internalPointer()
        if isinstance(p, Project):
            return len(p.pages)
        elif isinstance(p, Page):
            return len(p.objects)
        else:
            return 0

    def data(self, index, role):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        i = index.internalPointer()
        if isinstance(i, Page):
            return "Page %i" % (i.number + 1)
        elif isinstance(i, ItemBase):
            return i.getName()
        return None

    def parent(self, index):
        if not index.isValid():
            return None
        p = index.internalPointer()
        if isinstance(p, Page):
            return self.createIndex(0, 0, p.project)
        elif isinstance(p, ItemBase):
            return self.createIndex(0, 0, p.page)
        return QtCore.QModelIndex()

    def index(self, row, column, parent):
        p = self.project
        if parent.isValid():
            p = parent.internalPointer()
        if row < 0:
            return None
        if isinstance(p, Project):
            if row >= len(p.pages):
                return None
            return self.createIndex(row, column, p.pages[row])
        elif isinstance(p, Page):
            if row >= len(p.objects):
                return None
            return self.createIndex(row, column, p.objects[row])
        else:
            return None


class Page(QtCore.QObject):
    def __init__(self, project, i):
        QtCore.QObject.__init__(self)
        self.number = i
        self.objects = []

        self.scene = QtWidgets.QGraphicsScene()
        self.scene.setBackgroundBrush(QtCore.Qt.gray)
        self.pageItem = PdfPageItem(project.document.page(i), self)
        self.scene.addItem(self.pageItem)

        self.project = project

    def insertV(self, v_point):
        v_text = self._addText(v_point, "topleft", focus=False)
        v_text.setPlainText("v")
        return v_text

    def insertText(self, topleft):
        return self._addText(topleft, "topleft", focus=True)

    def insertStrikethrough(self, line_bbox):
        item = StrikethroughItem(self, line_bbox)
        self.scene.addItem(item)
        self.objects.append(item)
        return item

    def addTextUnderCursor(self, application):
        pos = application.pageView.mapToScene(
            application.pageView.mapFromGlobal(QtGui.QCursor.pos())
        )
        anchor = "baseline"
        self._addText(pos, "baseline", focus=True)

    def _addText(self, pos, anchor, focus):
        text = TextItem(self, self.myFont)
        if anchor == "baseline":
            font_metrics = QtGui.QFontMetrics(text.font())
            topleft = QtCore.QPointF(
                pos.x(), pos.y() - font_metrics.ascent() - font_metrics.leading() - 1
            )
        elif anchor == "topleft":
            topleft = pos
        else:
            raise ValueError(anchor)
        text.setPos(topleft)
        self.scene.addItem(text)
        self.objects.append(text)
        if focus:
            text.setSelected(True)
            text.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
            selection = text.textCursor()
            selection.select(QtGui.QTextCursor.Document)
            text.setTextCursor(selection)
            text.setFocus()
        return text

    def save(self, stream):
        stream.writeUInt32(len(self.objects))
        for obj in self.objects:
            stream.writeUInt32(obj.id())
            obj.save(stream)

    def load(self, stream):
        count = stream.readUInt32()
        for i in range(count):
            d = stream.readUInt32()
            for t in [ImageItem, RectItem, TextItem, StrikethroughItem]:
                if t.id() != d:
                    continue
                item = t(self)
                item.load(stream)
                self.scene.addItem(item)
                self.objects.append(item)

    def deleteSelection(self):
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
            self.objects.remove(item)

    def itemSelected(self, item):
        self.parent.itemSelected.emit(item)

    def changeFont(self, font):
        self.myFont = font
        for item in self.scene.selectedItems():
            if isinstance(item, TextItem):
                item.setFont(font)


class Project(QtCore.QObject):
    itemSelected = QtCore.pyqtSignal([QtWidgets.QGraphicsItem])

    def __init__(self):
        super().__init__()
        self.undoStack = QtWidgets.QUndoStack()
        self.document = None
        self.pages = []
        self.treeModel = ObjectTreeModel(self)
        self.path = None

    def load_pdf(self, pdfData):
        self.undoStack.clear()
        self.pdfData = pdfData
        self.document = popplerqt5.Poppler.Document.loadFromData(pdfData)
        self.document.setRenderHint(popplerqt5.Poppler.Document.Antialiasing, True)
        self.document.setRenderHint(popplerqt5.Poppler.Document.TextAntialiasing, True)
        self.pages = [Page(self, i) for i in range(self.document.numPages())]

    def create(self, path):
        if not os.path.exists(path):
            raise IOError("%s does not exist" % (path,))
        pdf = QtCore.QFile(path)
        pdf.open(QtCore.QIODevice.ReadOnly)
        pdfData = pdf.readAll()
        self.load_pdf(pdfData)
        self.path = os.path.splitext(str(path))[0] + ".pep"

    def save(self):
        f = QtCore.QFile(self.path)
        f.open(QtCore.QIODevice.WriteOnly)
        stream = QtCore.QDataStream(f)
        stream.writeUInt32(0x2a04c304)
        stream.writeUInt32(0)
        stream.writeQString(self.path)
        stream.writeBytes(self.pdfData)
        stream.writeUInt32(len(self.pages))
        for page in self.pages:
            page.save(stream)

    def saveas(self, path):
        self.path = str(path)
        self.save()

    def load(self, path):
        f = QtCore.QFile(path)
        f.open(QtCore.QIODevice.ReadOnly)
        stream = QtCore.QDataStream(f)
        if stream.readUInt32() != 0x2a04c304:
            return None
        version = stream.readUInt32()
        if version > 0:
            return None
        self.path = stream.readQString()
        pdfData = stream.readBytes()
        self.load_pdf(pdfData)
        pages = stream.readUInt32()
        for i in range(pages - len(self.pages)):
            self.addPage()
        for page in self.pages:
            page.load(stream)
        self.changeFont(self.font)

    def addPage():
        pass

    def export(self, path):
        printer = QtPrintSupport.QPrinter()
        printer.setColorMode(QtPrintSupport.QPrinter.Color)
        printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
        printer.setOutputFileName(path + "~1")
        printer.setPageMargins(0, 0, 0, 0, QtPrintSupport.QPrinter.Point)
        page = self.document.page(0)
        printer.setPaperSize(page.pageSizeF(), QtPrintSupport.QPrinter.Point)

        painter = QtGui.QPainter()
        if not painter.begin(printer):
            return

        first = True
        for page in self.pages:
            if first:
                first = False
            else:
                printer.newPage()
            page.pageItem.hide()
            bg = page.scene.backgroundBrush()
            page.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
            page.scene.render(painter, QtCore.QRectF(), page.pageItem.boundingRect())
            page.scene.setBackgroundBrush(bg)
            page.pageItem.show()
        painter.end()
        del painter
        del printer
        f = QtCore.QFile(path + "~2")
        f.open(QtCore.QIODevice.WriteOnly)
        f.write(self.pdfData)
        f.close()
        subprocess.call(
            ["pdftk", path + "~1", "multibackground", path + "~2", "output", path]
        )
        os.remove(path + "~1")
        os.remove(path + "~2")

    def changeFont(self, font):
        self.font = font
        for page in self.pages:
            page.changeFont(font)


class MainWindow(QtWidgets.QMainWindow):
    currentPageChanged = QtCore.pyqtSignal(Page)

    def setCurrentPage(self, page):
        if page == self.currentPage:
            return
        self.currentPage = page
        self.currentPageChanged.emit(page)
        self.treeView.clearSelection()
        if page:
            self.treeView.selectionModel().setCurrentIndex(
                self.project.treeModel.createIndex(0, 0, page),
                QtCore.QItemSelectionModel.ClearAndSelect,
            )

    def currentObjectChanged(self, current, previous):
        p = current.internalPointer()
        if isinstance(p, Page):
            self.setCurrentPage(p)
        elif isinstance(p, ItemBase):
            self.setCurrentPage(p.page)

    def __init__(self):
        QtCore.QObject.__init__(self)
        uic.loadUi(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "main.ui"), self
        )

        self.textToolBar.addWidget(self.fontCombo)

        self.textToolBar.addWidget(self.fontSizeCombo)
        self.fontSizeCombo.setValidator(QtGui.QIntValidator(2, 64, self))

        self.project = Project()
        self.project.itemSelected.connect(self.itemSelected)

        self.currentPage = None

        # self.actionAddImage.triggered.connect(self.addImage)

        # Action group ensures that when one action is selected, the others are unselected
        toolGroup = QtWidgets.QActionGroup(self)
        toolGroup.addAction(self.actionSizeTool)
        toolGroup.addAction(self.actionRectangleTool)
        toolGroup.addAction(self.actionLineTool)
        toolGroup.addAction(self.actionTextTool)
        self.actionSizeTool.setChecked(True)

        self.treeView.setModel(self.project.treeModel)
        self.treeView.selectionModel().currentChanged.connect(self.currentObjectChanged)

        self.handleFontChange()

    def doNewProject(self, path):
        self.setCurrentPage(None)
        self.project.create(path)
        if self.project.pages:
            self.setCurrentPage(self.project.pages[0])
        self.handleFontChange()

    def newProject(self):
        path = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open PDF file", "", "PDF document (*.pdf);;All files (*)"
        )
        if path:
            self.doNewProject(path)

    def export(self):
        a, e = os.path.splitext(str(self.project.path))
        path = a + "_ann.pdf"
        # path = QtWidgets.QFileDialog.getSaveFileName(
        #     self, "Export pdf", "", "Pdf Documents (*.pdf);;All files (*)")
        if path:
            self.project.export(path)

    def saveas(self):
        path = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Project",
            self.project.path if self.project.path else "",
            "Pro Documents (*.pro);;All files (*)",
        )
        if path:
            self.project.saveas(path)

    def doLoad(self, path):
        self.setCurrentPage(None)
        self.project.load(path)
        if self.project.pages:
            self.setCurrentPage(self.project.pages[0])

    def load(self):
        path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Project",
            self.project.path if self.project.path else "",
            "Pro Documents (*.pro);;All files (*)",
        )
        if path:
            self.doLoad(path)

    def save(self):
        if not self.project.path:
            self.saveas()
        else:
            self.project.save()

    def addImage(self):
        path = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Add image",
            "",
            "Image Formats (*.bmp *.jgp *.jpeg *.mng *.png *.pbm *.ppm "
            "*.tiff);;All files(*)",
        )
        if path:
            pass

    def addTextUnderCursor(self):
        self.currentPage.addTextUnderCursor(self)

    def deleteSelection(self):
        self.currentPage.deleteSelection()

    def exportSaveAndQuit(self):
        self.save()
        self.export()
        self.close()

    def handleFontChange(self, *_):
        font = self.fontCombo.currentFont()
        font.setPointSize(int(self.fontSizeCombo.currentText()))
        font.setWeight(
            QtGui.QFont.Bold if self.actionBold.isChecked() else QtGui.QFont.Normal
        )
        font.setItalic(self.actionItalic.isChecked())
        font.setUnderline(self.actionUnderline.isChecked())
        self.project.changeFont(font)

    def itemSelected(self, item):
        font = item.font()
        # color = item.defaultTextColor()
        self.fontCombo.setCurrentFont(font)
        self.fontSizeCombo.setEditText(str(font.pointSize()))
        self.boldAction.setChecked(font.weight() == QtGui.QFont.Bold)
        self.italicAction.setChecked(font.italic())
        self.underlineAction.setChecked(font.underline())
