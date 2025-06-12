# =========================================
#              IMPORTS
# =========================================
from PyQt6.QtWidgets import (
    QWidget,  # Base class for all UI objects
    QHBoxLayout,  # Horizontal layout manager
    QFrame,  # Frame widget for grouping
    QVBoxLayout,  # Vertical layout manager
    QSplitter,  # Widget for resizing child widgets
    QSplitterHandle,  # Handle for QSplitter
    QInputDialog,  # Dialog for user text input
)
from PyQt6.QtCore import QTimer, Qt  # Timer and Qt constants
from PyQt6.QtGui import QPainter, QColor  # Painting and color utilities
import json  # For encoding/decoding JSON
from ui import create_main_ui, apply_dark_theme  # UI helpers
from chat import create_chat_ui, connect_chat_signals  # Chat UI helpers
from network import connect_to_server  # Network connection helper


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
    def __init__(self, loop):
        super().__init__()
        self.setObjectName("GameClient")
        self.setStyleSheet(self.styleSheet() + "\n#GameClient { border: none; }")
        self.setWindowTitle("PyQt Game Client")

        # === GAME STATE ===
        self.action = None  # Current selected action (attack, block, load)
        self.loaded = False  # Whether player is loaded
        self.hp = 3  # Player HP
        self.opponent_hp = 3  # Opponent HP
        self.round = 1  # Current round number
        self.opponent_name = "Enemy"  # Opponent's username
        self.username = None  # Player's username
        self.websocket = None  # WebSocket connection
        self.loop = loop  # Asyncio event loop
        self.last_actions = None  # Store last round's actions

        # === USERNAME PROMPT ===
        self.username = self.prompt_for_username()  # Prompt for username on startup

        # === UI INITIALIZATION ===
        self.init_ui()  # Build UI
        apply_dark_theme(self)  # Apply dark theme

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
            self.loop.create_task(
                self.websocket.send(
                    json.dumps({"type": "submit", "action": self.action})
                )
            )
            self.submit_btn.setEnabled(False)
            self.disable_buttons()
            self.action = None

    def reset_game(self):
        if self.websocket:
            self.loop.create_task(self.websocket.send(json.dumps({"type": "reset"})))
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
        import websockets

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
        except (websockets.ConnectionClosed, websockets.ConnectionClosedOK):
            print("WebSocket connection closed cleanly.")
            self.status_label.setText("Disconnected from server.")
        except Exception as e:
            print(f"WebSocket error: {e}")
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
        self.loop.create_task(
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
