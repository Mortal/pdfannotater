import os
import sys

from PyQt4 import QtGui
from pdfannotator import MainWindow


def main():
    global a
    app = QtGui.QApplication(sys.argv)

    a = MainWindow()
    a.show()
    if len(app.arguments()) > 1:
        pep = os.path.splitext(str(app.arguments()[1]))[0] + ".pep"
        if os.path.exists(pep):
            a.doLoad(pep)
        else:
            a.doNewProject(app.arguments()[1])
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
