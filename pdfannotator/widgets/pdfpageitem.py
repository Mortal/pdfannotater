import math
import collections
from PyQt5 import QtCore, QtWidgets, QtGui


class PdfPageItem(QtWidgets.QGraphicsItem):
    _lines = None
    _selected = None
    _selected_rects = None
    _prev_v_pos = None
    _prev_strikethrough = None
    # selectedChanged = QtCore.pyqtSignal()

    selection_brush = QtGui.QColor("#4a90d9")

    def __init__(self, page, event_handler):
        assert page is not None
        super().__init__()
        self.setFlag(self.ItemIsFocusable, True)
        self._event_handler = event_handler
        self.image = None
        self.cachedRect = None
        self.page = page
        tmp = self.page.renderToImage(72, 72)
        self.rect = QtCore.QRectF(0, 0, tmp.width(), tmp.height())
        self.setFlag(self.ItemUsesExtendedStyleOption, True)
        # for bbox, line in self.lines():
        #     print(bbox, [word.text() for word in line])

    def keyPressEvent(self, event):
        if event.key() == ord("V"):
            space = self.selected_space()
            if space:
                v_pos = space.bbox.translated(0, -space.bbox.height() / 2).topLeft()
                if self._prev_v_pos:
                    adjustment = self._prev_v.pos() - self._prev_v_pos
                else:
                    adjustment = QtCore.QPointF(0, 0)
                self._prev_v_pos = v_pos
                self._prev_v = self._event_handler.insertV(v_pos + adjustment)
                self._event_handler.insertText(self.get_margin_point(space.bbox.top()))
                self._set_selected(None)
                return
        if event.key() == ord("-"):
            lines = self.get_selected_rects()
            if lines:
                if self._prev_strikethrough:
                    # Note that we create every StrikethroughItem with pos (0,0)
                    # and when it is moved, the pos changes but the bbox does not.
                    # Thus pos(), x(), y() tell us how much the user moved the item.
                    adjustment = self._prev_strikethrough.y()
                else:
                    adjustment = 0
                for line in lines:
                    self._prev_strikethrough = self._event_handler.insertStrikethrough(
                        line
                    )
                    # Copy the y-movement but not the x
                    self._prev_strikethrough.setPos(0, adjustment)
                self._event_handler.insertText(self.get_margin_point(lines[0].top()))
                self._set_selected(None)
                return
        super().keyPressEvent(event)

    def get_margin_point(self, top):
        lines = self.lines()

        widths = [line.bbox.width() for line in lines]
        median_width = sorted(widths)[len(widths) // 2]
        lines = [line for line in lines if line.bbox.width() >= median_width]

        right_margin = self.rect.right()
        lefts = []
        rights = []
        for line in lines:
            lefts.append(line.bbox.left())
            rights.append(right_margin - line.bbox.right())
        left = sorted(lefts)[int(len(lefts) * .2)]
        right = sorted(rights)[int(len(rights) * .2)]
        if left > right:
            return QtCore.QPointF(8, top)
        else:
            return QtCore.QPointF(right_margin - right + 8, top)

    def selected_space(self):
        if not self._selected or self._selected[0] != self._selected[1]:
            return
        word = self.get_selected_word()
        if word.text == "":
            return word

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
                if word.bbox.contains(pos):
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

    def get_selected_word(self):
        if self._selected:
            line, word = self._selected[0]
            return self.lines()[line].words[word]

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
            words = self.lines()[i].words
            if i == end_line:
                words = words[: end_word + 1]
            if i == start_line:
                words = words[start_word:]
            if words:
                bboxes = [word.bbox for word in words]
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


Line = collections.namedtuple("Line", "bbox words")
Word = collections.namedtuple("Word", "bbox text")


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
        last_end = None
        while len(line) < len(textbox):
            bbox = word.boundingBox()
            if last_end is not None:
                space_bbox = QtCore.QRectF(
                    last_end, bbox.top(), bbox.left() - last_end, bbox.height()
                )
                line.append(Word(space_bbox, ""))
            last_end = bbox.right()
            line.append(Word(bbox, word.text()))
            bboxes.append(bbox)
            word = word.nextWord()
            if not word or in_degree[word] != 1:
                break
        bbox = smallest_enclosing_rectf(bboxes)
        lines.append(Line(bbox, line))
    lines.sort(key=lambda line: line[0].top())
    return lines
