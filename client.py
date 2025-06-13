# =========================================
#              IMPORTS
# =========================================
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QFrame,
    QVBoxLayout,
    QSplitter,
    QSplitterHandle,
    QInputDialog,
    QMessageBox,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor
import json
import sys
import asyncio
import websockets

# Import game UI helpers
from ui import create_main_ui, apply_dark_theme
from chat import create_chat_ui, connect_chat_signals
from network import connect_to_server


# =========================================
#         CUSTOM SPLITTER CLASSES
# =========================================
class DoubleLineSplitterHandle(QSplitterHandle):
    # Custom splitter handle with double vertical line
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)

    def paintEvent(self, event):
        # Paints two vertical lines for the splitter handle
        super().paintEvent(event)
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        painter.setPen(QColor(0, 0, 0))  # Black line
        painter.drawLine(1, 0, 1, h)
        painter.setPen(QColor(68, 68, 68))  # Dark grey line
        painter.drawLine(3, 0, 3, h)
        painter.end()


class DoubleLineSplitter(QSplitter):
    # Custom splitter using DoubleLineSplitterHandle
    def createHandle(self):
        return DoubleLineSplitterHandle(self.orientation(), self)


# =========================================
#           MAIN GAME CLIENT
# =========================================
class GameClient(QWidget):
    def __init__(self, loop, websocket, username, opponent_name, parent_lobby=None):
        super().__init__()
        self.setObjectName("GameClient")
        self.setStyleSheet(self.styleSheet() + "\n#GameClient { border: none; }")
        self.setWindowTitle(f"Game - {username} vs {opponent_name}")
        self.action = None
        self.loaded = False
        self.hp = 3
        self.opponent_hp = 3
        self.round = 0
        self.opponent_name = opponent_name
        self.username = username
        self.websocket = websocket
        self.loop = loop
        self.last_actions = None
        self.parent_lobby = parent_lobby
        self.init_ui()
        apply_dark_theme(self)
        self._last_round_for_chat = 0
        self.setMinimumSize(700, 500)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

    # -----------------------------------------
    # Prompt user for a username
    # -----------------------------------------
    def prompt_for_username(self):
        name, ok = QInputDialog.getText(self, "Enter Username", "Choose a username:")
        if ok and name.strip():
            return name.strip()
        # If not provided, use default client# (set after server assigns)
        return None

    # -----------------------------------------
    # Build the main UI layout
    # -----------------------------------------
    def init_ui(self):
        layout = create_main_ui(self)  # Main game area layout
        create_chat_ui(self)  # Chat area layout
        connect_chat_signals(self)  # Connect chat signals

        # --- Game area frame ---
        self.game_frame = QFrame()
        self.game_frame.setObjectName("GameArea")
        game_layout = QVBoxLayout(self.game_frame)
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(0)
        game_layout.addLayout(layout)

        # --- Chat area frame ---
        self.chat_frame = QFrame()
        self.chat_frame.setObjectName("ChatArea")
        chat_layout = QVBoxLayout(self.chat_frame)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        chat_layout.addWidget(self.chat_container)

        # --- Splitter for game/chat ---
        splitter = DoubleLineSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.addWidget(self.game_frame)
        splitter.addWidget(self.chat_frame)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(splitter)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        splitter.setSizes([400, 300])

        self.setFixedWidth(700)  # Initial window width

        self.splitter = splitter
        self.game_frame_ref = self.game_frame
        self.chat_frame_ref = self.chat_frame

        layout.addWidget(self.message_toggle_btn)

        # --- Button connections ---
        self.attack_btn.clicked.connect(lambda: self.select_action("attack"))
        self.block_btn.clicked.connect(lambda: self.select_action("block"))
        self.load_btn.clicked.connect(lambda: self.select_action("load"))
        self.submit_btn.clicked.connect(self.submit_action)
        self.reset_btn.clicked.connect(self.reset_game)

        # --- Chat alert logic ---
        def clear_chat_alert(checked):
            if checked:
                self.message_toggle_btn.setText("Hide Chat")
            else:
                self.message_toggle_btn.setText("Show Chat")

        self.message_toggle_btn.toggled.connect(clear_chat_alert)

        # --- Game/chat toggle logic ---
        def toggle_game_area(checked):
            main_window = self.window()
            if checked:
                if self.splitter.count() == 2:
                    self.splitter.widget(0).setParent(None)
                self.hide_game_btn.setText("<")
                self.game_frame_ref.setVisible(False)
                if self.chat_frame_ref.isVisible():
                    main_window.setFixedWidth(300)
                else:
                    main_window.setFixedWidth(0)
            else:
                if self.splitter.count() == 1:
                    self.splitter.insertWidget(0, self.game_frame_ref)
                    self.splitter.setSizes([400, 300])
                self.hide_game_btn.setText(">")
                self.game_frame_ref.setVisible(True)
                if self.chat_frame_ref.isVisible():
                    main_window.setFixedWidth(700)
                else:
                    main_window.setFixedWidth(400)
            if not checked:
                main_window._prev_full_width = main_window.width()

        def toggle_chat_area(checked):
            main_window = self.window()
            self.chat_frame_ref.setVisible(checked)
            if checked:
                self.message_toggle_btn.setText("Hide Chat")
                if self.splitter.count() == 2:
                    main_window.setFixedWidth(700)
                else:
                    main_window.setFixedWidth(300)
            else:
                self.message_toggle_btn.setText("Show Chat")
                if self.splitter.count() == 2:
                    main_window.setFixedWidth(400)
                else:
                    main_window.setFixedWidth(0)

        self.hide_game_btn.setChecked(True)
        self.hide_game_btn.toggled.connect(toggle_game_area)
        self.message_toggle_btn.setChecked(True)
        self.message_toggle_btn.toggled.connect(toggle_chat_area)
        if self.splitter.count() == 2:
            self.splitter.widget(0).setParent(None)
        self.hide_game_btn.setText("<")
        self.chat_frame_ref.setVisible(True)
        self.game_frame_ref.setVisible(False)

        def enforce_initial_width():
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.resize(300, self.height())
            self.setFixedWidth(300)

        QTimer.singleShot(0, enforce_initial_width)

        # --- Redundant toggle logic for window width (ensures correct sizing) ---
        def toggle_game_area(checked):
            main_window = self.window()
            if checked:
                if self.splitter.count() == 2:
                    self.splitter.widget(0).setParent(None)
                self.hide_game_btn.setText("<")
                self.game_frame_ref.setVisible(False)
                if self.chat_frame_ref.isVisible():
                    main_window.setFixedWidth(300)
                else:
                    main_window.setFixedWidth(0)
            else:
                if self.splitter.count() == 1:
                    self.splitter.insertWidget(0, self.game_frame_ref)
                    self.splitter.setSizes([400, 300])
                self.hide_game_btn.setText(">")
                self.game_frame_ref.setVisible(True)
                if self.chat_frame_ref.isVisible():
                    main_window.setFixedWidth(700)
                else:
                    main_window.setFixedWidth(400)
            if not checked:
                main_window._prev_full_width = main_window.width()

        def toggle_chat_area(checked):
            main_window = self.window()
            self.chat_frame_ref.setVisible(checked)
            if checked:
                self.message_toggle_btn.setText("Hide Chat")
                if self.splitter.count() == 2:
                    main_window.setFixedWidth(700)
                else:
                    main_window.setFixedWidth(300)
            else:
                self.message_toggle_btn.setText("Show Chat")
                if self.splitter.count() == 2:
                    main_window.setFixedWidth(400)
                else:
                    main_window.setFixedWidth(0)

        self.hide_game_btn.setChecked(True)
        self.hide_game_btn.toggled.connect(toggle_game_area)
        self.message_toggle_btn.setChecked(True)
        self.message_toggle_btn.toggled.connect(toggle_chat_area)
        if self.splitter.count() == 2:
            self.splitter.widget(0).setParent(None)
        self.hide_game_btn.setText("<")
        self.chat_frame_ref.setVisible(True)
        self.game_frame_ref.setVisible(False)
        QTimer.singleShot(0, lambda: self.setFixedWidth(300))

    # =========================================
    #         GAME LOGIC AND UI METHODS
    # =========================================
    def select_action(self, action):
        self.action = action  # Store selected action
        self.submit_btn.setEnabled(True)  # Enable submit
        # Highlight the selected action button
        highlight_style = (
            "background-color: #ffcc00; color: #222; border: 2px solid #fff;"
        )
        default_style = ""
        self.attack_btn.setStyleSheet(default_style)
        self.block_btn.setStyleSheet(default_style)
        self.load_btn.setStyleSheet(default_style)
        if action == "attack":
            self.attack_btn.setStyleSheet(highlight_style)
        elif action == "block":
            self.block_btn.setStyleSheet(highlight_style)
        elif action == "load":
            self.load_btn.setStyleSheet(highlight_style)

    def submit_action(self):
        if self.websocket and self.action:
            import asyncio

            asyncio.create_task(
                self.websocket.send(
                    json.dumps({"type": "submit", "action": self.action})
                )
            )
            self.submit_btn.setEnabled(False)
            self.disable_buttons()
            self.action = None

    def reset_game(self):
        if self.websocket:
            import asyncio

            asyncio.create_task(self.websocket.send(json.dumps({"type": "reset"})))
        self.reset_btn.setEnabled(False)
        self.game_frame.setStyleSheet("QFrame#GameArea { border: none; }")
        self.round_label.setText("Round: 1")
        self.round = 1
        self.last_actions = None
        self._last_round_for_chat = 1
        self.round = 1
        self.round_label.setText("Round: 1")
        self.last_actions = None
        self._last_round_for_chat = 1

    def enable_buttons(self):
        self.attack_btn.setEnabled(self.loaded)
        self.block_btn.setEnabled(True)
        self.load_btn.setEnabled(not self.loaded)
        self.attack_btn.setStyleSheet("")
        self.block_btn.setStyleSheet("")
        self.load_btn.setStyleSheet("")

    def disable_buttons(self):
        self.attack_btn.setEnabled(False)
        self.block_btn.setEnabled(False)
        self.load_btn.setEnabled(False)

    def highlight_label(self, label):
        original_style = label.styleSheet()
        label.setStyleSheet("background-color: red; color: white;")
        QTimer.singleShot(1000, lambda: label.setStyleSheet(original_style))

    def append_chat_message(
        self,
        sender,
        message,
        highlight=None,
        round_sep=False,
        round_number=None,
        match_end_sep=False,
    ):
        from PyQt6.QtGui import QTextCursor

        # If chat is collapsed, add alert emoji to the toggle button
        if not self.chat_container.isVisible():
            if not self.message_toggle_btn.text().startswith("Show Chat 🚨"):
                self.message_toggle_btn.setText("Show Chat 🚨")

        html = ""
        # Add a round separator if needed
        if round_sep and round_number is not None:
            html += (
                f'<div style="margin:12px 0 4px 0; border-bottom:2px solid #888; font-size:13px; color:#bbb;">— Round {round_number} —</div>'
                "<br>"
            )
        # Add a match end divider if requested
        if match_end_sep:
            html += (
                '<div style="margin:16px 0 8px 0; border-bottom:3px double #ffcc00; font-size:15px; color:#ffcc00; text-align:center;">=== End of Match ===</div>'
                "<br>"
            )
        # Distinguish between action summaries and player-typed messages
        if highlight == "action":
            if sender == "You":
                sender_display = self.username
                name_color = "#1565c0"  # blue
                msg_style = "background-color:#cce4ff; color:#1565c0; padding:2px 6px; border-radius:6px;"
            elif sender in ("Player", "Enemy"):
                sender_display = self.opponent_name
                name_color = "#c62828"  # red
                msg_style = "background-color:#ffe3e3; color:#c62828; padding:2px 6px; border-radius:6px;"
            else:
                sender_display = sender
                name_color = "#fff"
                msg_style = ""
            html += (
                f'<b><span style="color:{name_color};">{sender_display}:</span></b> '
                f'<span style="{msg_style}">{message}</span>'
            )
        else:
            if sender == "You":
                sender_display = self.username
                name_color = "#1565c0"  # blue
            else:
                # Any message not sent by the user is considered opponent/other and is red
                sender_display = (
                    self.opponent_name
                    if sender in ("Player", "Enemy", self.opponent_name)
                    else sender
                )
                name_color = "#c62828"  # red
            msg_style = "color:#fff;"
            html += (
                f'<b><span style="color:{name_color};">{sender_display}:</span></b> '
                f'<span style="{msg_style}">{message}</span>'
            )

        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    async def receive_messages(self):
        self.websocket = await connect_to_server("ws://localhost:8765")
        if not self.websocket:
            self.status_label.setText("Could not connect to server.")
            return
        if self.username:
            await self.websocket.send(
                json.dumps({"type": "name", "name": self.username})
            )
        else:
            await self.websocket.send(json.dumps({"type": "name"}))
        self._last_round_for_chat = 1
        try:
            async for msg in self.websocket:
                data = json.loads(msg)
                msg_type = data.get("type")
                if msg_type == "lobby_joined":
                    if not self.username:
                        self.username = data.get("name", "client?")
                elif msg_type == "waiting":
                    self.status_label.setText("Waiting for opponent...")
                    self.round = 1
                    self.round_label.setText("Round: 1")
                    self._last_round_for_chat = 1
                elif msg_type == "update":
                    self.round = data["round"]
                    self.opponent_name = data.get("opponent_name", "Enemy")
                    if self.round == 1:
                        self._last_round_for_chat = 1
                        self.round_label.setText("Round: 1")
                    if self.last_actions is not None:
                        my_action, opp_action = self.last_actions
                        my_result, opp_result = self.get_action_results(
                            my_action, opp_action
                        )
                        round_sep = (
                            self._last_round_for_chat is None
                            or self.round != self._last_round_for_chat
                        )
                        sep_round_number = self.round if round_sep else None
                        self.append_chat_message(
                            "You",
                            my_result,
                            highlight="action",
                            round_sep=round_sep,
                            round_number=sep_round_number,
                        )
                        self.append_chat_message(
                            "Enemy", opp_result, highlight="action"
                        )
                        self._last_round_for_chat = self.round
                    self.last_actions = None
                    self.loaded = data["loaded"]
                    self.opponent_name = data.get("opponent_name", "Enemy")
                    self.opponent_loaded = data.get("opponent_loaded", False)
                    if data["hp"] < self.hp:
                        self.highlight_label(self.hp_label)
                    if data["opponent_hp"] < self.opponent_hp:
                        self.highlight_label(self.opponent_hp_label)
                    self.hp = data["hp"]
                    self.opponent_hp = data["opponent_hp"]
                    self.update_hp_labels()
                    self.round_label.setText(f"Round: {self.round}")
                    loaded_emoji = "✅" if self.loaded else "❌"
                    self.loaded_label.setText(f"Loaded: {loaded_emoji}")
                    self.status_label.setText("Select your move")
                    self.enable_buttons()
                elif msg_type == "game_over":
                    winner = data["winner"]
                    if self.hp <= 0 and self.opponent_hp > 0:
                        color = "#ff0000"
                        self.status_label.setText(f"Defeat! {self.opponent_name} wins.")
                    elif self.hp > 0 and self.opponent_hp <= 0:
                        color = "#00ff00"
                        self.status_label.setText(f"Victory! You win!")
                    elif self.hp <= 0 and self.opponent_hp <= 0:
                        color = "#FFD600"
                        self.status_label.setText("Draw! Nobody wins.")
                    else:
                        color = "#888888"
                        self.status_label.setText(f"Game Over! Winner: {winner}")
                    self.game_frame.setStyleSheet(
                        f"QFrame#GameArea {{ border: 4px solid {color}; border-radius: 10px; }}"
                    )
                    self.disable_buttons()
                    self.reset_btn.setEnabled(True)
                    self.append_chat_message("", "", match_end_sep=True)
                elif msg_type == "chat":
                    sender = data.get("sender", "Enemy")
                    message = data.get("message", "")
                    if sender == "Player":
                        sender = "Enemy"
                    self.append_chat_message(sender, message)
                elif msg_type == "actions":
                    self.last_actions = (data["your_action"], data["opponent_action"])
        except (Exception,):
            self.status_label.setText("Connection error.")

    # =========================================
    #         CHAT LOGIC AND DISPLAY
    # =========================================
    def append_chat_message(
        self,
        sender,
        message,
        highlight=None,
        round_sep=False,
        round_number=None,
        match_end_sep=False,
    ):
        from PyQt6.QtGui import QTextCursor

        # If chat is collapsed, add alert emoji to the toggle button
        if not self.chat_container.isVisible():
            if not self.message_toggle_btn.text().startswith("Show Chat 🚨"):
                self.message_toggle_btn.setText("Show Chat 🚨")

        html = ""
        # Add a round separator if needed
        if round_sep and round_number is not None:
            html += (
                f'<div style="margin:12px 0 4px 0; border-bottom:2px solid #888; font-size:13px; color:#bbb;">— Round {round_number} —</div>'
                "<br>"
            )
        # Add a match end divider if requested
        if match_end_sep:
            html += (
                '<div style="margin:16px 0 8px 0; border-bottom:3px double #ffcc00; font-size:15px; color:#ffcc00; text-align:center;">=== End of Match ===</div>'
                "<br>"
            )
        # Distinguish between action summaries and player-typed messages
        if highlight == "action":
            if sender == "You":
                sender_display = self.username
                name_color = "#1565c0"  # blue
                msg_style = "background-color:#cce4ff; color:#1565c0; padding:2px 6px; border-radius:6px;"
            elif sender in ("Player", "Enemy"):
                sender_display = self.opponent_name
                name_color = "#c62828"  # red
                msg_style = "background-color:#ffe3e3; color:#c62828; padding:2px 6px; border-radius:6px;"
            else:
                sender_display = sender
                name_color = "#fff"
                msg_style = ""
            html += (
                f'<b><span style="color:{name_color};">{sender_display}:</span></b> '
                f'<span style="{msg_style}">{message}</span>'
            )
        else:
            if sender == "You":
                sender_display = self.username
                name_color = "#1565c0"  # blue
            else:
                # Any message not sent by the user is considered opponent/other and is red
                sender_display = (
                    self.opponent_name
                    if sender in ("Player", "Enemy", self.opponent_name)
                    else sender
                )
                name_color = "#c62828"  # red
            msg_style = "color:#fff;"
            html += (
                f'<b><span style="color:{name_color};">{sender_display}:</span></b> '
                f'<span style="{msg_style}">{message}</span>'
            )

        self.chat_display.append(html)
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)

    # =========================================
    #         NETWORK AND GAME STATE
    # =========================================
    async def receive_messages(self):
        try:
            async for msg in self.websocket:
                data = json.loads(msg)
                msg_type = data.get("type")

                # If a game window is open, forward game messages to it
                if self.parent_lobby.game_window:
                    # Forward only game-related messages
                    if msg_type in (
                        "update",
                        "game_over",
                        "chat",
                        "actions",
                        "room_left",
                    ):
                        await self.parent_lobby.game_window.handle_game_message(data)
                        if msg_type == "room_left":
                            self.parent_lobby.show_lobby()
                        continue
                # Otherwise, handle lobby messages as before
                if msg_type == "lobby_update":
                    self.parent_lobby.update_users(data.get("users", []))
                    self.parent_lobby.update_rooms(data.get("open_rooms", []))
                elif msg_type == "room_joined":
                    self.parent_lobby.open_room(data.get("usernames", []))
                elif msg_type == "room_left":
                    self.parent_lobby.show_lobby()
                elif msg_type == "invite_received":
                    from_user = data.get("from")
                    reply = QMessageBox.question(
                        None,  # Use None as parent for cross-backend compatibility
                        "Invitation",
                        f"You have been invited by {from_user}! Accept?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        await self.websocket.send(
                            json.dumps(
                                {
                                    "type": "invite_response",
                                    "from": from_user,
                                    "accepted": True,
                                }
                            )
                        )
                    else:
                        await self.websocket.send(
                            json.dumps(
                                {
                                    "type": "invite_response",
                                    "from": from_user,
                                    "accepted": False,
                                }
                            )
                        )
                elif msg_type == "invite_result":
                    from_user = data.get("from")
                    accepted = data.get("accepted")
                    if accepted:
                        QMessageBox.information(
                            None,
                            "Invite Accepted",
                            f"{from_user} accepted your invitation!",
                        )
                        await self.websocket.send(json.dumps({"type": "enter_room"}))
                    else:
                        QMessageBox.information(
                            None,
                            "Invite Declined",
                            f"{from_user} declined your invitation.",
                        )
        except (websockets.ConnectionClosed, websockets.ConnectionClosedOK):
            self.status_label.setText("Disconnected from server.")
        except Exception as e:
            self.status_label.setText("Connection error.")

    # =========================================
    #         GAME LOGIC HELPERS
    # =========================================
    def get_action_results(self, my_action, opp_action):
        if my_action == "attack":
            if opp_action == "block":
                return ("attacked, but your opponent blocked", "blocked your attack")
            elif opp_action == "load":
                return ("hit your opponent", "loaded")
            else:
                return ("attacked", "attacked")
        elif my_action == "block":
            if opp_action == "attack":
                return ("blocked", "attacked, but you blocked")
            elif opp_action == "load":
                return ("blocked", "loaded")
            else:
                return ("blocked", "blocked")
        elif my_action == "load":
            if opp_action == "attack":
                return ("loaded", "attacked")
            elif opp_action == "block":
                return ("loaded", "blocked")
            else:
                return ("loaded", "loaded")
        return (my_action, opp_action)

    def send_message(self):
        message = self.message_input.toPlainText().strip()
        if not message or not self.websocket:
            return
        import asyncio

        asyncio.create_task(
            self.websocket.send(json.dumps({"type": "chat", "message": message}))
        )
        self.append_chat_message("You", message)
        self.message_input.clear()

    def update_hp_labels(self):
        self.hp_label.setText(
            f"Your HP: {self.hp_to_hearts(self.hp, '#ff2d55')}"  # Red
        )
        self.opponent_hp_label.setText(
            f"Enemy HP: {self.hp_to_hearts(self.opponent_hp, '#a259ff')}"  # Purple
        )
        loaded_emoji = "✅" if self.loaded else "❌"
        self.loaded_label.setText(f"Loaded: {loaded_emoji}")
        enemy_loaded_emoji = "✅" if getattr(self, "opponent_loaded", False) else "❌"
        self.enemy_loaded_label.setText(f"Loaded: {enemy_loaded_emoji}")

    def receive_update(self, hp, opponent_hp, loaded, round_num, opponent_name):
        self.hp = hp
        self.opponent_hp = opponent_hp
        self.opponent_name = opponent_name
        self.update_hp_labels()
        self.loaded = loaded
        self.round = round_num
        self.round_label.setText(f"Round: {self.round}")
        loaded_emoji = "✅" if self.loaded else "❌"
        self.loaded_label.setText(f"Loaded: {loaded_emoji}")
        self.status_label.setText("Select your move")
        self.enable_buttons()

    async def handle_game_message(self, data):
        msg_type = data.get("type")
        if msg_type == "update":
            self.round = data.get("round", 1)
            self.opponent_name = data.get("opponent_name", "Enemy")
            if self.round == 1:
                self._last_round_for_chat = 1
                self.round_label.setText("Round: 1")
            if self.last_actions is not None:
                my_action, opp_action = self.last_actions
                my_result, opp_result = self.get_action_results(my_action, opp_action)
                round_sep = (
                    self._last_round_for_chat is None
                    or self.round != self._last_round_for_chat
                )
                sep_round_number = self.round if round_sep else None
                self.append_chat_message(
                    "You",
                    my_result,
                    highlight="action",
                    round_sep=round_sep,
                    round_number=sep_round_number,
                )
                self.append_chat_message("Enemy", opp_result, highlight="action")
                self._last_round_for_chat = self.round
            self.last_actions = None
            self.loaded = data.get("loaded", False)
            self.opponent_name = data.get("opponent_name", "Enemy")
            self.opponent_loaded = data.get("opponent_loaded", False)
            if data.get("hp", self.hp) < self.hp:
                self.highlight_label(self.hp_label)
            if data.get("opponent_hp", self.opponent_hp) < self.opponent_hp:
                self.highlight_label(self.opponent_hp_label)
            self.hp = data.get("hp", self.hp)
            self.opponent_hp = data.get("opponent_hp", self.opponent_hp)
            self.update_hp_labels()
            self.round_label.setText(f"Round: {self.round}")
            loaded_emoji = "✅" if self.loaded else "❌"
            self.loaded_label.setText(f"Loaded: {loaded_emoji}")
            self.status_label.setText("Select your move")
            self.enable_buttons()
        elif msg_type == "game_over":
            winner = data["winner"]
            if self.hp <= 0 and self.opponent_hp > 0:
                color = "#ff0000"
                self.status_label.setText(f"Defeat! {self.opponent_name} wins.")
            elif self.hp > 0 and self.opponent_hp <= 0:
                color = "#00ff00"
                self.status_label.setText(f"Victory! You win!")
            elif self.hp <= 0 and self.opponent_hp <= 0:
                color = "#FFD600"
                self.status_label.setText("Draw! Nobody wins.")
            else:
                color = "#888888"
                self.status_label.setText(f"Game Over! Winner: {winner}")
            self.game_frame.setStyleSheet(
                f"QFrame#GameArea {{ border: 4px solid {color}; border-radius: 10px; }}"
            )
            self.disable_buttons()
            self.reset_btn.setEnabled(True)
            self.append_chat_message("", "", match_end_sep=True)
        elif msg_type == "chat":
            sender = data.get("sender", "Enemy")
            message = data.get("message", "")
            if sender == "Player":
                sender = "Enemy"
            self.append_chat_message(sender, message)
        elif msg_type == "actions":
            self.last_actions = (data["your_action"], data["opponent_action"])
        elif msg_type == "room_left":
            self.close()
            if self.parent_lobby:
                self.parent_lobby.show()


# =========================================
#              LOBBY CLIENT
# =========================================
class LobbyWindow(QtWidgets.QWidget):
    def __init__(self, ws, username):
        super().__init__()
        self.ws = ws
        self.username = username
        self.setWindowTitle(f"Lobby - {username}")
        self.resize(600, 400)
        self.layout = QtWidgets.QHBoxLayout(self)
        # User list
        self.user_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.user_list)
        # Invite button
        self.invite_button = QtWidgets.QPushButton("Invite")
        self.invite_button.setEnabled(False)
        self.layout.addWidget(self.invite_button)
        # Open rooms list
        self.room_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.room_list)
        # Create open room button
        self.create_room_button = QtWidgets.QPushButton("Create Open Room")
        self.create_room_button.clicked.connect(self.create_open_room)
        room_col = QtWidgets.QVBoxLayout()
        room_col.addWidget(self.room_list)
        room_col.addWidget(self.create_room_button)
        room_col.addStretch()
        # --- Add Close Room button ---
        self.close_room_button = QtWidgets.QPushButton("Close Room")
        self.close_room_button.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold; border-radius: 6px; padding: 8px 0;"
        )
        self.close_room_button.setEnabled(False)
        self.close_room_button.clicked.connect(self.close_own_room)
        room_col.addWidget(self.close_room_button)
        # --- End of Close Room button addition ---
        room_col_widget = QtWidgets.QWidget()
        room_col_widget.setLayout(room_col)
        self.layout.addWidget(room_col_widget)
        # Connect signals
        self.user_list.itemSelectionChanged.connect(self.on_user_selected)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)
        # Add join room button
        self.join_room_button = QtWidgets.QPushButton("Join Room")
        self.join_room_button.setEnabled(False)
        self.join_room_button.clicked.connect(self.join_selected_room)
        room_col.addWidget(self.join_room_button)
        self.room_window = None
        self.game_window = None

        # Connect invite logic
        from chat import connect_lobby_invite

        connect_lobby_invite(self, self.user_list)

    def on_user_selected(self):
        selected = self.user_list.selectedItems()
        if not selected:
            self.invite_button.setEnabled(False)
            return
        selected_user = (
            selected[0].text().replace(" (you)", "").replace(" (in room)", "")
        )
        # Disable invite if selected user is self or in a room
        if selected_user == self.username or "(in room)" in selected[0].text():
            self.invite_button.setEnabled(False)
            return
        # Disable invite if current user is in a room
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            if item.text().startswith(self.username) and "(in room)" in item.text():
                self.invite_button.setEnabled(False)
                return
        self.invite_button.setEnabled(True)

    def on_room_selected(self):
        selected = self.room_list.selectedItems()
        if not selected:
            self.join_room_button.setEnabled(False)
            self.join_room_button.setStyleSheet("")
            return
        room_id = selected[0].text()
        # Check if the room is joinable (open room with only one user)
        # We'll use the open_rooms list and user_list to infer this
        # If the room name matches <username>'s room and the current user is not in a room
        is_joinable = False
        if room_id.endswith("'s room"):
            # Find the user who owns the room
            owner = room_id[:-7]
            # Check if the current user is not in a room
            user_in_room = False
            for i in range(self.user_list.count()):
                item = self.user_list.item(i)
                if item.text().startswith(self.username) and "(in room)" in item.text():
                    user_in_room = True
                    break
            if not user_in_room and owner != self.username:
                is_joinable = True
        if is_joinable:
            self.join_room_button.setEnabled(True)
            self.join_room_button.setStyleSheet(
                "background-color: #43a047; color: white; font-weight: bold; border-radius: 6px; padding: 8px 0;"
            )
        else:
            self.join_room_button.setEnabled(False)
            self.join_room_button.setStyleSheet("")

    def update_users(self, users):
        # users is a list of usernames, possibly with ' (in room)' suffix from the server
        self.user_list.clear()
        for user in users:
            label = user
            # Always mark yourself as (you), even if server already added it
            if user.startswith(self.username):
                if "(you)" not in label:
                    label = label.replace(" (in room)", "") + " (you)"
                    if " (in room)" in user:
                        label += " (in room)"
            self.user_list.addItem(label)
        self.user_list.repaint()
        self.on_user_selected()  # Update invite button state

    def update_rooms(self, rooms):
        self.room_list.clear()
        for room in rooms:
            self.room_list.addItem(room)
        # --- Enable/disable Close Room button logic ---
        # User can only close their own open room if they are alone in it
        has_own_room = False
        for room in rooms:
            if room.startswith(f"{self.username}'s room"):
                has_own_room = True
                break
        # Check if user is in a room (alone)
        user_in_room = False
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            if item.text().startswith(self.username) and "(in room)" in item.text():
                user_in_room = True
                break
        # Enable Close Room if user has their own open room and is alone in it
        enabled = has_own_room and user_in_room
        self.close_room_button.setEnabled(enabled)
        if enabled:
            self.close_room_button.setStyleSheet(
                "background-color: #c62828; color: white; font-weight: bold; border-radius: 6px; padding: 8px 0;"
            )
        else:
            self.close_room_button.setStyleSheet(
                "background-color: #888; color: #eee; font-weight: bold; border-radius: 6px; padding: 8px 0;"
            )

    def close_own_room(self):
        # Send leave_room to server
        import asyncio, json

        asyncio.create_task(self.ws.send(json.dumps({"type": "leave_room"})))

    def join_selected_room(self):
        selected = self.room_list.selectedItems()
        if selected:
            room_id = selected[0].text()
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "join_room", "room_id": room_id}))
            )

    def open_room(self, usernames):
        # If two users, start game session
        if len(usernames) == 2:
            opponent = [u for u in usernames if u != self.username][0]
            from client import GameClient

            # Instead of starting a new receive_messages coroutine, just create the GameClient and switch UI
            self.game_window = GameClient(
                self.ws.loop, self.ws, self.username, opponent, parent_lobby=self
            )
            self.game_window.show()
            self.hide()
            # --- Trigger game session creation for open room flow ---
            import asyncio, json

            asyncio.create_task(self.ws.send(json.dumps({"type": "enter_room"})))
            # Do NOT start a new receive_messages coroutine here!
            # The main handle_ws_messages coroutine will continue to dispatch messages.
        else:
            # Show waiting room UI (optional, or just keep lobby open)
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.information(
                None, "Room Created", "Waiting for another player to join..."
            )

    def show_lobby(self):
        self.show()
        if self.game_window:
            self.game_window.close()
            self.game_window = None

    def create_open_room(self):
        import asyncio, json

        asyncio.create_task(self.ws.send(json.dumps({"type": "create_room"})))


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


class RoomWindow(QtWidgets.QWidget):
    def __init__(self, ws, usernames, my_username, lobby):
        super().__init__()
        self.ws = ws
        self.usernames = usernames
        self.my_username = my_username
        self.lobby = lobby
        self.setWindowTitle(f"Room - {', '.join(usernames)}")
        self.resize(300, 200)
        layout = QtWidgets.QVBoxLayout(self)
        self.user_list = QtWidgets.QListWidget()
        self.update_user_list(usernames)
        layout.addWidget(self.user_list)
        self.leave_button = QtWidgets.QPushButton("Leave Room")
        self.leave_button.clicked.connect(self.leave_room)
        layout.addWidget(self.leave_button)

    def update_user_list(self, usernames):
        self.user_list.clear()
        for user in usernames:
            label = user
            if user == self.my_username:
                label += " (you)"
            self.user_list.addItem(label)

    def leave_room(self):
        asyncio.create_task(self.ws.send(json.dumps({"type": "leave_room"})))
        self.close()
        self.lobby.show()


async def handle_ws_messages(ws, lobby):
    from PyQt6.QtWidgets import QMessageBox

    async for msg in ws:
        data = json.loads(msg)
        # If a game window is open, forward game messages to it
        if lobby.game_window:
            # Forward only game-related messages
            if data.get("type") in (
                "update",
                "game_over",
                "chat",
                "actions",
                "room_left",
            ):
                await lobby.game_window.handle_game_message(data)
                if data.get("type") == "room_left":
                    lobby.show_lobby()
                continue
        # Otherwise, handle lobby messages as before
        if data.get("type") == "lobby_update":
            lobby.update_users(data.get("users", []))
            lobby.update_rooms(data.get("open_rooms", []))
        elif data.get("type") == "room_joined":
            lobby.open_room(data.get("usernames", []))
        elif data.get("type") == "room_left":
            lobby.show_lobby()
        elif data.get("type") == "invite_received":
            from_user = data.get("from")
            reply = QMessageBox.question(
                None,  # Use None as parent for cross-backend compatibility
                "Invitation",
                f"You have been invited by {from_user}! Accept?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                await ws.send(
                    json.dumps(
                        {
                            "type": "invite_response",
                            "from": from_user,
                            "accepted": True,
                        }
                    )
                )
            else:
                await ws.send(
                    json.dumps(
                        {
                            "type": "invite_response",
                            "from": from_user,
                            "accepted": False,
                        }
                    )
                )
        elif data.get("type") == "invite_result":
            from_user = data.get("from")
            accepted = data.get("accepted")
            if accepted:
                QMessageBox.information(
                    None, "Invite Accepted", f"{from_user} accepted your invitation!"
                )
                await ws.send(json.dumps({"type": "enter_room"}))
            else:
                QMessageBox.information(
                    None, "Invite Declined", f"{from_user} declined your invitation."
                )


async def main_async():
    app = QtWidgets.QApplication(sys.argv)
    prompt = NamePrompt()
    if prompt.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        username = prompt.get_name()
        if not username:
            sys.exit()
        async with websockets.connect("ws://localhost:8765") as ws:
            ws.loop = asyncio.get_event_loop()
            await ws.send(json.dumps({"name": username}))
            lobby = LobbyWindow(ws, username)
            lobby.show()
            await handle_ws_messages(ws, lobby)
    else:
        sys.exit()


# Remove or comment out this block to avoid double event loop
# if __name__ == "__main__":
#     asyncio.run(main_async())
