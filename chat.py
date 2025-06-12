# =========================================
#              IMPORTS
# =========================================
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTextEdit, QPushButton, QSizePolicy
from PyQt6.QtCore import Qt


# =========================================
#         CHAT UI CREATION
# =========================================
def create_chat_ui(self):
    # --- Chat toggle button ---
    self.message_toggle_btn = QPushButton("Show Chat")
    self.message_toggle_btn.setCheckable(True)
    self.message_toggle_btn.setChecked(True)
    self.message_toggle_btn.setText("Hide Chat")

    # --- Chat container and layout ---
    self.chat_container = QWidget()
    self.chat_container.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    self.chat_layout = QVBoxLayout(self.chat_container)
    self.chat_layout.setContentsMargins(10, 10, 10, 10)
    self.chat_layout.setSpacing(24)
    self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

    # --- Chat display (read-only log) ---
    self.chat_display = QTextEdit()
    self.chat_display.setReadOnly(True)
    self.chat_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    self.chat_display.setStyleSheet("margin-bottom: 12px; margin-top: 12px;")
    self.chat_display.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    self.chat_layout.addWidget(self.chat_display, stretch=10)

    # --- Message input box ---
    self.message_input = QTextEdit()
    self.message_input.setPlaceholderText("Type your message here...")
    self.message_input.setFixedHeight(60)
    self.message_input.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    self.chat_layout.addWidget(self.message_input, stretch=0)

    # --- Enter key submits message ---
    def handle_message_input_key(event):
        # If Enter is pressed without Shift/Ctrl, send message
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers()
            & (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier)
        ):
            self.send_message()
            event.accept()
        else:
            QTextEdit.keyPressEvent(self.message_input, event)

    self.message_input.keyPressEvent = handle_message_input_key

    # --- Send button ---
    self.send_btn = QPushButton("Send")
    self.send_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    send_row = QVBoxLayout()
    send_row.setContentsMargins(0, 0, 0, 0)
    send_row.setSpacing(0)
    send_row.addWidget(self.send_btn)
    self.chat_layout.addLayout(send_row, stretch=0)

    # --- Hide Game toggle button (bottom left) ---
    self.hide_game_btn = QPushButton("<")
    self.hide_game_btn.setFixedSize(24, 24)
    self.hide_game_btn.setStyleSheet(
        """
        QPushButton {
            background: transparent;
            border: none;
            color: transparent;
            font-size: 14px;
            padding: 2px 6px;
            margin-top: 8px;
        }
        QPushButton:hover {
            background: #222;
            border: 2px solid #ffcc00;
            border-radius: 6px;
            color: #ffcc00;
        }
        """
    )
    self.hide_game_btn.setCheckable(True)
    self.hide_game_btn.setChecked(True)
    from PyQt6.QtWidgets import QHBoxLayout

    hide_game_row = QHBoxLayout()
    hide_game_row.setContentsMargins(0, 0, 0, 0)
    hide_game_row.setSpacing(0)
    hide_game_row.addWidget(self.hide_game_btn, alignment=Qt.AlignmentFlag.AlignLeft)
    hide_game_row.addStretch(1)
    self.chat_layout.addLayout(hide_game_row, stretch=0)

    self.chat_container.setVisible(True)
    self.chat_container.setMinimumWidth(200)
    self.chat_container.setMaximumWidth(600)
    self.chat_container.setMinimumHeight(200)
    if hasattr(self, "chat_frame"):
        self.chat_frame.setVisible(True)


# =========================================
#         CHAT SIGNAL CONNECTIONS
# =========================================
def connect_chat_signals(self):
    def toggle_chat(checked):
        main_window = self.window()
        splitter = None
        parent = self.parent()
        while parent is not None:
            if parent.metaObject().className() == "QSplitter":
                splitter = parent
                break
            parent = parent.parent()
        if checked:
            self.message_toggle_btn.setText("Hide Chat")
            if getattr(self, "_window_size_before_chat", None) is None:
                self._window_size_before_chat = main_window.size()
                new_width = (
                    self._window_size_before_chat.width() + self.chat_container.width()
                )
                main_window.resize(new_width, main_window.height())
                main_window.setMinimumWidth(new_width)
            if hasattr(self, "chat_frame"):
                self.chat_frame.setVisible(True)
            self.chat_container.setVisible(True)
            if splitter and splitter.count() == 1:
                splitter.addWidget(self.chat_frame)
                splitter.setSizes(
                    [main_window.width() * 2 // 3, main_window.width() // 3]
                )
        else:
            self.message_toggle_btn.setText("Show Chat")
            if getattr(self, "_window_size_before_chat", None) is not None:
                main_window.resize(self._window_size_before_chat)
                main_window.setMinimumWidth(self._window_size_before_chat.width())
                self._window_size_before_chat = None
            if hasattr(self, "chat_frame"):
                self.chat_frame.setVisible(False)
            self.chat_container.setVisible(False)
            if splitter and splitter.count() == 2:
                splitter.widget(1).setParent(None)
        main_window.adjustSize()

    self.message_toggle_btn.toggled.connect(toggle_chat)
    if hasattr(self, "send_message") and callable(getattr(self, "send_message", None)):
        try:
            self.send_btn.clicked.disconnect()
        except TypeError:
            pass
        self.send_btn.clicked.connect(self.send_message)
    else:
        print(
            "Warning: send_message method not found on self, chat send will not work."
        )
