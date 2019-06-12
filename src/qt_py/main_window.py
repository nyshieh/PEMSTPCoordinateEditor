import sys
import os
from decimal import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtWidgets import QFileDialog

from log import Logger
logger = Logger(__name__)


# Load Qt ui file into a class
qtCreatorFile = os.path.join(os.path.dirname(os.path.realpath(__file__)),  "../qt_ui/main_window.ui")
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

files = []

class ExceptionHandler(QtCore.QObject):

    errorSignal = QtCore.pyqtSignal()
    silentSignal = QtCore.pyqtSignal()

    def __init__(self):
        super(ExceptionHandler, self).__init__()

    def handler(self, exctype, value, traceback):
        self.errorSignal.emit()
        sys._excepthook(exctype, value, traceback)

exceptionHandler = ExceptionHandler()
sys._excepthook = sys.excepthook
sys.excepthook = exceptionHandler.handler

class Stream(QtCore.QObject):
    newText = QtCore.pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self,EASTdisplacement,NORTHdisplacement):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.EASTdisplacement = None
        self.NORTHdisplacement = None
        self.setupUi(self)

        self.menubar.setNativeMenuBar(False)
        self.setAcceptDrops(True)

        # Connect signals to slots
        self.action_open_file.triggered.connect(self.on_file_open)
        self.pshProcess.clicked.connect(self.process_files)
        self.chkOverwrite.stateChanged.connect(self.flipstate)
        self.pshClear.clicked.connect(self.clearall)
        self.file_browser = None

        self.move(500, 300)

    def clearall(self):
        files.clear()
        self.txtPEM.setText(None)

    def flipstate(self):
        QWidget.setEnabled(self.lineEdit,not QWidget.isEnabled(self.lineEdit))

    def on_file_open(self):
        # Will eventually hold logic for choosing between different file types
        # TODO Add logger class
        logger.info("Entering file dialog")

        dlg = QFileDialog()
        dlg.setNameFilter("PEM (*.pem)");

        files.extend(dlg.getOpenFileNames()[0])

        if len(files) == 0:
            logger.info("No Files Selected")
            return
        else:
            self.open_files()

    def dropEvent(self, e):
        logger.info("File dropped into main window")
        urls = [url.toLocalFile() for url in e.mimeData().urls()]
        files.extend(urls)
        self.open_files(files)

    def open_files(self):
        s = '\n'.join(files)
        self.txtPEM.setText(s)

    def process_files(self):
        if len(files)==0:
            return
        READONLY = not self.chkOverwrite.isChecked()
        suffix = self.lineEdit.displayText()
        try:
            self.EASTdisplacement = float(self.lineEasting.displayText())
            self.NORTHdisplacement = float(self.lineNorthing.displayText())
        except ValueError:
            QMessageBox.warning(self, 'No Input', 'Enter Numeric Displacements', QMessageBox.Ok, QMessageBox.Ok)
            return

        if self.chkOverwrite.isChecked():
            msg = 'Confirm overwrite of existing files? ORIGINALS WILL BE LOST'
        else:
            msg = 'Start processing?'

        if READONLY and suffix == "":
            QMessageBox.information(self, 'No Suffix', 'Enter Suffix', QMessageBox.Ok, QMessageBox.Ok)
            return

        buttonReply = QMessageBox.warning(self, 'Confirm', msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            for i in files:
                self.processFileGPS(i,READONLY,suffix)
            suffix = ""

    # Flattens a list of lists
    def flatten(self, l):
        flat_list = [item for sublist in l for item in sublist]
        return flat_list

    # Strips tab and comma delineators
    def stripDelin(self, s):
        temp = s.replace('\t', ' ').replace(',', ' ')
        return temp

    # convertLine(line_as_list as List,METER_FLAG as Boolean)
    #   Replace coordinate line in a Crone PEM/STP file by incrementing by some displacement declared globally.
    #   Precision can be edited by changing the argument of the .quantize methods.
    #   Requires: List is at least of length 4
    def convertLine(self, line_as_list, METER_FLAG):
        linelist = line_as_list
        if METER_FLAG:
            # Meters
            linelist[1] = str(Decimal((Decimal(linelist[1]) + Decimal(self.EASTdisplacement))).quantize(Decimal('0.1')))
            linelist[2] = str(Decimal((Decimal(linelist[2]) + Decimal(self.NORTHdisplacement))).quantize(Decimal('0.1')))
        else:
            # Feet
            linelist[1] = str(
                Decimal((Decimal(linelist[1]) + Decimal(self.EASTdisplacement * 3.28084))).quantize(Decimal('0.1')))
            linelist[2] = str(
                Decimal((Decimal(linelist[2]) + Decimal(self.NORTHdisplacement* 3.28084))).quantize(Decimal('0.1')))
        return linelist

    # processFileGPS(Filepath as String, READONLY_FLAG as Boolean)
    #   Replace a Crone .PEM or .STP file GPS UTM coordinates with an offset specified in the global
    #   declarations of (EASTdisplacementm as Float) and (NORTHdisplacementm as Float)
    #   Note: Will overwrite the file at FilePath unless READONLY_FLAG is True, in which a copy <File>NAD83.(PEM/STP)
    #   will be written to
    def processFileGPS(self, FilePath, READONLY_FLAG, suffix):

        with open(FilePath) as f:
            lines = f.readlines()
        i = 0
        numEdits = 0
        while i < len(lines):
            edited_flag = False
            line = lines[i]
            line = line.strip('\n')
            if line != '' and line[0] == '<':
                flag = line[1]
                if flag == 'T' and line[1:4] != 'TXS' or flag == 'L' or flag == 'P':
                    # Remove delineators
                    templine = self.stripDelin(line)
                    linelist = templine.split(' ')
                    # Remove extra nullspace
                    while '' in linelist: linelist.remove('')
                    if len(linelist) < 5:
                        linelist = list(map(lambda x: x.split(","), linelist))
                        linelist = self.flatten(linelist)
                    # Try converting line
                    if len(linelist) > 1:
                        try:
                            float(linelist[1]) and float(linelist[2])
                            if linelist[4] == '1':
                                linelist = self.convertLine(linelist, False)
                            else:
                                linelist = self.convertLine(linelist, True)
                            numEdits += 1
                            edited_flag = True
                        except ValueError:
                            pass
                        linelist.append('\n')
                        lines[i] = " ".join(linelist)
            if not edited_flag: line = line + '\n'
            i += 1
        self.txtConsoleOut.append(FilePath + suffix + ": " + str(numEdits) + " line edits")

        NEW_PATH = FilePath
        if READONLY_FLAG:
            NEW_PATH = FilePath[0:len(FilePath) - 4] + suffix + FilePath[len(FilePath) - 4:len(FilePath)]
        with open(NEW_PATH, 'w') as f:
            f.writelines(lines)

if __name__ == "__main__":
    # Code to test MainWindow if running main_window.py
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())