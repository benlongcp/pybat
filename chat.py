# =========================================
#              IMPORTS
# =========================================
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QPushButton,
    QSizePolicy,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt
import json
import asyncio
import functools


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

    # --- Exit Room Button ---
    self.exit_room_btn = QPushButton("Exit Room / Return to Lobby")
    self.exit_room_btn.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
    )
    self.exit_room_btn.setStyleSheet(
        "background-color: #c62828; color: white; font-weight: bold; border-radius: 6px; padding: 8px 0; margin-top: 16px;"
    )

    def handle_exit_room():
        # Send leave_room message to server and close game window
        if hasattr(self, "websocket") and self.websocket:
            import asyncio, json

            asyncio.create_task(self.websocket.send(json.dumps({"type": "leave_room"})))
        # If in a parent_lobby context, show lobby
        if hasattr(self, "parent_lobby") and self.parent_lobby:
            self.close()
            self.parent_lobby.show_lobby()

    self.exit_room_btn.clicked.connect(handle_exit_room)
    # Add the button at the very bottom of the chat layout
    self.chat_layout.addStretch(1)
    self.chat_layout.addWidget(
        self.exit_room_btn, alignment=Qt.AlignmentFlag.AlignBottom
    )

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


# =========================================
#         LOBBY INVITE BUTTON HANDLER
# =========================================
def connect_lobby_invite(self, user_list_widget):
    def on_user_selected():
        selected = user_list_widget.selectedItems()
        if not selected:
            self.invite_button.setEnabled(False)
            return
        selected_user = (
            selected[0].text().replace(" (you)", "").replace(" (in room)", "")
        )
        # Check if selected user is self or in room
        if selected_user == self.username:
            self.invite_button.setEnabled(False)
            return
        if "(in room)" in selected[0].text():
            self.invite_button.setEnabled(False)
            return
        # Check if current user is in room
        for i in range(user_list_widget.count()):
            item = user_list_widget.item(i)
            if item.text().startswith(self.username) and "(in room)" in item.text():
                self.invite_button.setEnabled(False)
                return
        self.invite_button.setEnabled(True)

        # Use a closure to always get the current selected user at click time
        def send_invite():
            selected = user_list_widget.selectedItems()
            if not selected:
                print("[DEBUG] No user selected at click time.")
                return
            user = selected[0].text().replace(" (you)", "").replace(" (in room)", "")
            print(f"[DEBUG] Sending invite to: {user}")
            import asyncio, json

            asyncio.create_task(
                self.ws.send(json.dumps({"type": "invite", "to": user}))
            )

        try:
            self.invite_button.clicked.disconnect()
        except TypeError:
            pass
        self.invite_button.clicked.connect(send_invite)

    user_list_widget.itemSelectionChanged.connect(on_user_selected)


# =========================================
#         GAME/LOBBY INTEGRATION HELPERS
# =========================================
def start_game_session(self, websocket, username, opponent_name):
    """
    Helper to transition from lobby/room UI to the game session UI.
    Should be called when a room is joined with two users (either via invite or open room).
    """
    from client import GameClient

    self.game_window = GameClient(
        self.loop, websocket, username, opponent_name, parent_lobby=self
    )
    self.game_window.round = (
        -2
    )  # Offset starting round by -2 (will be incremented to 1 on first update)
    self.game_window._last_round_for_chat = -2
    self.game_window.show()
    self.hide()
    # Do NOT start a new receive_messages coroutine here!
    # The main handle_ws_messages coroutine will continue to dispatch messages.


# =========================================
#         LOBBY INVITE/ROOM HANDLERS
# =========================================
def handle_lobby_message(self, data):
    """
    Call this from your lobby/room message handler to process lobby events.
    Handles: room_joined, invite_received, invite_result, create_room, join_room, leave_room.
    """
    msg_type = data.get("type")
    if msg_type == "room_joined":
        usernames = data.get("usernames", [])
        if len(usernames) == 2:
            # Start game session with the other user
            opponent = [u for u in usernames if u != self.username][0]
            self.start_game_session(self.ws, self.username, opponent)
        else:
            # Waiting for another player to join the room
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                None, "Room Created", "Waiting for another player to join..."
            )
    elif msg_type == "invite_received":
        from_user = data.get("from")
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            None,
            "Invitation",
            f"You have been invited by {from_user}! Accept?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            asyncio.create_task(
                self.ws.send(
                    json.dumps(
                        {
                            "type": "invite_response",
                            "from": from_user,
                            "accepted": True,
                        }
                    )
                )
            )
        else:
            asyncio.create_task(
                self.ws.send(
                    json.dumps(
                        {
                            "type": "invite_response",
                            "from": from_user,
                            "accepted": False,
                        }
                    )
                )
            )
    elif msg_type == "invite_result":
        from_user = data.get("from")
        accepted = data.get("accepted")
        from PyQt6.QtWidgets import QMessageBox

        if accepted:
            QMessageBox.information(
                None, "Invite Accepted", f"{from_user} accepted your invitation!"
            )
            asyncio.create_task(self.ws.send(json.dumps({"type": "enter_room"})))
        else:
            QMessageBox.information(
                None, "Invite Declined", f"{from_user} declined your invitation."
            )
    elif msg_type == "room_left":
        # Return to lobby UI if user leaves the room/game
        if hasattr(self, "game_window") and self.game_window:
            # Add chat notification if the other client disconnected
            if hasattr(self.game_window, "append_chat_message"):
                # Ensure the chat window is visible before closing
                self.game_window.chat_display.append(
                    '<b><span style="color:#ffcc00;">System:</span></b> <span style="color:#fff;">Your opponent has left or disconnected.</span>'
                )
                self.game_window.chat_display.moveCursor(
                    self.game_window.chat_display.textCursor().End
                )
            self.game_window.close()
            self.game_window = None
        self.show()
    # You can add more handlers for create_room, join_room, etc. as needed...
