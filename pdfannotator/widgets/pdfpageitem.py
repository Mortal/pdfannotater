import math
from PyQt5 import QtCore, QtWidgets


class PdfPageItem(QtWidgets.QGraphicsItem):
    def __init__(self, page):
        super().__init__()
        self.image = None
        self.cachedRect = None
        self.page = page
        tmp = page.renderToImage(75, 75)
        self.rect = QtCore.QRectF(0, 0, tmp.width(), tmp.height())
        self.setFlag(self.ItemUsesExtendedStyleOption, True)

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
                75 * d, 75 * d, left, top, right - left, bottom - top
            )
            self.cachedRect = (top, left, right, bottom)
        painter.drawImage(
            QtCore.QRectF(left / d, top / d, (right - left) / d, (bottom - top) / d),
            self.image,
        )
