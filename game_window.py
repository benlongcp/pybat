import json
import asyncio
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout
from splitters import DoubleLineSplitter
from ui import create_main_ui, apply_dark_theme
from chat import create_chat_ui, connect_chat_signals
from network import connect_to_server


class GameClient(QtWidgets.QWidget):
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
        self.block_points = 3
        self.init_ui()
        apply_dark_theme(self)
        self._last_round_for_chat = 0
        self.setMinimumSize(700, 500)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

    def prompt_for_username(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Enter Username", "Choose a username:"
        )
        if ok and name.strip():
            return name.strip()
        return None

    def init_ui(self):
        layout = create_main_ui(self)
        create_chat_ui(self)
        connect_chat_signals(self)
        self.game_frame = QFrame()
        self.game_frame.setObjectName("GameArea")
        game_layout = QVBoxLayout(self.game_frame)
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(0)
        game_layout.addLayout(layout)
        self.chat_frame = QFrame()
        self.chat_frame.setObjectName("ChatArea")
        chat_layout = QVBoxLayout(self.chat_frame)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        chat_layout.addWidget(self.chat_container)
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
        self.setFixedWidth(700)
        self.splitter = splitter
        self.game_frame_ref = self.game_frame
        self.chat_frame_ref = self.chat_frame
        layout.addWidget(self.message_toggle_btn)
        self.attack_btn.clicked.connect(lambda: self.select_action("attack"))
        self.block_btn.clicked.connect(lambda: self.select_action("block"))
        self.load_btn.clicked.connect(lambda: self.select_action("load"))
        self.standby_btn.clicked.connect(lambda: self.select_action("standby"))
        self.submit_btn.clicked.connect(self.submit_action)
        self.reset_btn.clicked.connect(self.reset_game)

        def clear_chat_alert(checked):
            if checked:
                self.message_toggle_btn.setText("Hide Chat")
            else:
                self.message_toggle_btn.setText("Show Chat")

        self.message_toggle_btn.toggled.connect(clear_chat_alert)

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
                self.hide_game_btn.setText("}")
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

    def block_points_to_emojis(self, points):
        # Always return exactly the number of shields as block points
        return "🛡️" * points + " " * (3 - points)

    def update_block_points_ui(self):
        if hasattr(self, "block_points_label"):
            # Show your block points and opponent's block points
            self.block_points_label.setText(
                f"🛡️" * self.block_points
                + " | Enemy: "
                + "🛡️" * getattr(self, "opponent_block_points", 3)
            )

    def enable_buttons(self):
        self.attack_btn.setEnabled(self.loaded)
        self.block_btn.setEnabled(self.block_points > 0)
        self.load_btn.setEnabled(not self.loaded)
        self.standby_btn.setEnabled(True)
        self.attack_btn.setStyleSheet("")
        self.block_btn.setStyleSheet("")
        self.load_btn.setStyleSheet("")
        self.standby_btn.setStyleSheet("")
        self.update_block_points_ui()

    def disable_buttons(self):
        self.attack_btn.setEnabled(False)
        self.block_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.standby_btn.setEnabled(False)
        self.submit_btn.setEnabled(False)
        self.reset_btn.setVisible(False)  # Always hide reset except at game over

    def select_action(self, action):
        self.action = action
        self.submit_btn.setEnabled(True)
        highlight_style = (
            "background-color: #ffcc00; color: #222; border: 2px solid #fff;"
        )
        default_style = ""
        self.attack_btn.setStyleSheet(default_style)
        self.block_btn.setStyleSheet(default_style)
        self.load_btn.setStyleSheet(default_style)
        self.standby_btn.setStyleSheet(default_style)
        if action == "attack":
            self.attack_btn.setStyleSheet(highlight_style)
        elif action == "block":
            self.block_btn.setStyleSheet(highlight_style)
        elif action == "load":
            self.load_btn.setStyleSheet(highlight_style)
        elif action == "standby":
            self.standby_btn.setStyleSheet(highlight_style)
        self.update_block_points_ui()

    def submit_action(self):
        if self.websocket and self.action:
            # Block points logic: decrement if block, increment if not block or standby
            if self.action == "block":
                if self.block_points > 0:
                    self.block_points -= 1
            elif self.action in ("load", "attack"):
                if self.block_points < 3:
                    self.block_points += 1
            elif self.action == "standby":
                if self.block_points < 3:
                    self.block_points += 1
            self.update_block_points_ui()
            if self.block_points == 0:
                self.block_btn.setEnabled(False)
            else:
                self.block_btn.setEnabled(True)
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
            import asyncio, json

            asyncio.create_task(self.websocket.send(json.dumps({"type": "reset"})))
        self.reset_btn.setEnabled(False)
        self.reset_btn.setVisible(False)  # Hide reset after clicking
        self.game_frame.setStyleSheet("QFrame#GameArea { border: none; }")
        self.round_label.setText("Round: 1")
        self.round = 1
        self.last_actions = None
        self._last_round_for_chat = 1
        self.block_points = 3
        self.update_block_points_ui()
        self.block_btn.setEnabled(True)

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

        if not self.chat_container.isVisible():
            if not self.message_toggle_btn.text().startswith("Show Chat 🚨"):
                self.message_toggle_btn.setText("Show Chat 🚨")
        html = ""
        if round_sep and round_number is not None:
            html += (
                f'<div style="margin:12px 0 4px 0; border-bottom:2px solid #888; font-size:13px; color:#bbb;">— Round {round_number} —</div>'
                "<br>"
            )
        if match_end_sep:
            html += (
                '<div style="margin:16px 0 8px 0; border-bottom:3px double #ffcc00; font-size:15px; color:#ffcc00; text-align:center;">=== End of Match ===</div>'
                "<br>"
            )
        if highlight == "action":
            if sender == "You":
                sender_display = self.username
                name_color = "#1565c0"
                msg_style = "background-color:#cce4ff; color:#1565c0; padding:2px 6px; border-radius:6px;"
            elif sender in ("Player", "Enemy"):
                sender_display = self.opponent_name
                name_color = "#c62828"
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
                name_color = "#1565c0"
            else:
                sender_display = (
                    self.opponent_name
                    if sender in ("Player", "Enemy", self.opponent_name)
                    else sender
                )
                name_color = "#c62828"
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
                    # Update block points from server
                    self.block_points = data.get("block_points", self.block_points)
                    self.opponent_block_points = data.get("opponent_block_points", 3)
                    self.update_hp_labels()
                    self.round_label.setText(f"Round: {self.round}")
                    loaded_emoji = "✅" if self.loaded else "❌"
                    self.loaded_label.setText(f"Loaded: {loaded_emoji}")
                    self.status_label.setText("Select your move")
                    self.enable_buttons()
                    self.update_block_points_ui()  # Ensure shield UI updates every round
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
                    self.reset_btn.setVisible(True)  # Show reset at game over
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

    def get_action_results(self, my_action, opp_action):
        if my_action == "attack":
            if opp_action == "block":
                return ("attacked, but your opponent blocked", "blocked your attack")
            elif opp_action == "load":
                return ("hit your opponent", "loaded")
            elif opp_action == "standby":
                return ("attacked", "stood by and got hit")
            else:
                return ("attacked", "attacked")
        elif my_action == "block":
            if opp_action == "attack":
                return ("blocked", "attacked, but you blocked")
            elif opp_action == "load":
                return ("blocked", "loaded")
            elif opp_action == "standby":
                return ("blocked", "stood by")
            else:
                return ("blocked", "blocked")
        elif my_action == "load":
            if opp_action == "attack":
                return ("loaded", "attacked")
            elif opp_action == "block":
                return ("loaded", "blocked")
            elif opp_action == "standby":
                return ("loaded", "stood by")
            else:
                return ("loaded", "loaded")
        elif my_action == "standby":
            if opp_action == "attack":
                return ("stood by and got hit", "attacked")
            elif opp_action == "block":
                return ("stood by", "blocked")
            elif opp_action == "load":
                return ("stood by", "loaded")
            elif opp_action == "standby":
                return ("stood by", "stood by")
        return (my_action, opp_action)

    def send_message(self):
        message = self.message_input.toPlainText().strip()
        if not message or not self.websocket:
            return
        asyncio.create_task(
            self.websocket.send(json.dumps({"type": "chat", "message": message}))
        )
        self.append_chat_message("You", message)
        self.message_input.clear()

    def update_hp_labels(self):
        self.hp_label.setText(f"Your HP: {self.hp_to_hearts(self.hp, '#ff2d55')}")
        self.opponent_hp_label.setText(
            f"Enemy HP: {self.hp_to_hearts(self.opponent_hp, '#a259ff')}"
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
        self.update_block_points_ui()

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
            # Update block points from server
            self.block_points = data.get("block_points", self.block_points)
            self.opponent_block_points = data.get("opponent_block_points", 3)
            self.update_hp_labels()
            self.round_label.setText(f"Round: {self.round}")
            loaded_emoji = "✅" if self.loaded else "❌"
            self.loaded_label.setText(f"Loaded: {loaded_emoji}")
            self.status_label.setText("Select your move")
            self.enable_buttons()
            self.update_block_points_ui()  # Ensure shield UI updates every round
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
            self.reset_btn.setVisible(True)  # Show reset at game over
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
