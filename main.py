from gui.gui import Ui_MainWindow
from PyQt6.QtWidgets import QApplication, QMainWindow

class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

app = QApplication([])
window = Window()

window.show()
app.exec()