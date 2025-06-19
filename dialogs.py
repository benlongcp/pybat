# dialogs.py - Dialogs for user prompts and notifications
# TODO: Add comments to all dialog classes and functions, including any stubs or placeholders.

from PyQt6 import QtWidgets


class NamePrompt(QtWidgets.QDialog):
    """
    Dialog to prompt the user for their name.
    """

    def __init__(self):
        """
        Initializes the dialog, setting the window title and
        adding the name input field and join lobby button.
        """
        super().__init__()
        self.setWindowTitle("Enter your name")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.input = QtWidgets.QLineEdit()
        self.layout.addWidget(self.input)
        self.button = QtWidgets.QPushButton("Join Lobby")
        self.layout.addWidget(self.button)
        self.button.clicked.connect(self.accept)

    def get_name(self):
        """
        Returns the text from the input field, stripped of
        leading and trailing whitespace.
        """
        return self.input.text().strip()
