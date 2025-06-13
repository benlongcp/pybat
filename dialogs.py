from PyQt6 import QtWidgets


class NamePrompt(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter your name")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.input = QtWidgets.QLineEdit()
        self.layout.addWidget(self.input)
        self.button = QtWidgets.QPushButton("Join Lobby")
        self.layout.addWidget(self.button)
        self.button.clicked.connect(self.accept)

    def get_name(self):
        return self.input.text().strip()
