import math
from PyQt5 import QtCore, QtWidgets, QtGui


class PdfPageItem(QtWidgets.QGraphicsItem):
    _lines = None
    _selected = None
    _selected_rects = None
    # selectedChanged = QtCore.pyqtSignal()

    selection_brush = QtGui.QColor("#4a90d9")

    def __init__(self, page):
        assert page is not None
        super().__init__()
        self.image = None
        self.cachedRect = None
        self.page = page
        tmp = self.page.renderToImage(72, 72)
        self.rect = QtCore.QRectF(0, 0, tmp.width(), tmp.height())
        self.setFlag(self.ItemUsesExtendedStyleOption, True)
        # for bbox, line in self.lines():
        #     print(bbox, [word.text() for word in line])

    def lines(self):
        if self._lines is not None:
            return self._lines
        self._lines = partition_into_lines(self.page.textList())
        return self._lines

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        d = option.levelOfDetailFromTransform(painter.worldTransform())
        d = min(d, 8)
        r = self.boundingRect()
        top = math.floor(r.top() * d)
        left = math.floor(r.left() * d)
        bottom = math.ceil(r.bottom() * d)
        right = math.ceil(r.right() * d)

        if (top, left, right, bottom) != self.cachedRect:
            self.image = self.page.renderToImage(
                72 * d, 72 * d, left, top, right - left, bottom - top
            )
            self.cachedRect = (top, left, right, bottom)
        painter.drawImage(
            QtCore.QRectF(left / d, top / d, (right - left) / d, (bottom - top) / d),
            self.image,
        )
        painter.save()
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_Multiply)
        for rect in self.get_selected_rects():
            painter.fillRect(rect, self.selection_brush)
        painter.restore()

    def find_word(self, pos):
        for i, (bbox, line) in enumerate(self.lines()):
            if not bbox.contains(pos):
                continue
            for j, word in enumerate(line):
                if word.boundingBox().contains(pos):
                    return i, j

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            word = self.find_word(pos)
            if word:
                self._set_selected((word, word))
                return
        self._set_selected(None)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._selected:
            pos = self.mapToScene(event.pos())
            word = self.find_word(pos)
            if word:
                self._set_selected((self._selected[0], word))

    def mouseReleaseEvent(self, event):
        pass

    def _set_selected(self, word_range):
        if self._selected == word_range:
            return
        self._selected = word_range
        self._selected_rects = None
        self.update()
        # self.selectedChanged.emit()

    def get_selected_rects(self):
        if self._selected_rects is not None:
            return self._selected_rects
        if not self._selected:
            self._selected_rects = ()
            return self._selected_rects
        start_line, start_word = min(self._selected)
        end_line, end_word = max(self._selected)
        self._selected_rects = []
        for i in range(start_line, end_line + 1):
            line = self.lines()[i][1]
            if i == end_line:
                line = line[: end_word + 1]
            if i == start_line:
                line = line[start_word:]
            if line:
                bboxes = [word.boundingBox() for word in line]
                self._selected_rects.append(smallest_enclosing_rectf(bboxes))
        return self._selected_rects


def smallest_enclosing_rectf(bboxes):
    top = bboxes[0].top()
    left = bboxes[0].left()
    right = bboxes[0].right()
    bottom = bboxes[0].bottom()
    for bbox in bboxes:
        top = min(top, bbox.top())
        left = min(left, bbox.left())
        right = max(right, bbox.right())
        bottom = max(bottom, bbox.bottom())
    return QtCore.QRectF(left, top, right - left, bottom - top)


def partition_into_lines(textbox):
    in_degree = {word: 0 for word in textbox}
    for word in textbox:
        if word.nextWord():
            in_degree[word.nextWord()] += 1
    lines = []
    for word in textbox:
        if in_degree[word] == 1:
            continue
        line = []
        bboxes = []
        while len(line) < len(textbox):
            line.append(word)
            bboxes.append(word.boundingBox())
            word = word.nextWord()
            if not word or in_degree[word] != 1:
                break
        bbox = smallest_enclosing_rectf(bboxes)
        lines.append((bbox, line))
    lines.sort(key=lambda line: line[0].top())
    return lines
