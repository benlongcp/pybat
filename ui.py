# =========================================
#              IMPORTS
# =========================================
from PyQt6.QtWidgets import (
    QLabel,  # Label widget for text
    QPushButton,  # Button widget
    QVBoxLayout,  # Vertical layout manager
    QHBoxLayout,  # Horizontal layout manager
    QWidget,  # Base widget
    QTextEdit,  # Multi-line text input
    QGroupBox,  # Group box for grouping widgets
    QFrame,  # Frame for grouping/layout
)
from PyQt6.QtCore import Qt  # Qt constants for alignment, etc.


# =========================================
#         MAIN GAME UI LAYOUT
# =========================================
def create_main_ui(self):
    layout = QVBoxLayout()  # Main vertical layout for the game area

    # --- Status Section ---
    status_row = QHBoxLayout()  # Row for status bar
    status_row.addStretch(1)  # Left column stretch for centering
    status_box = QFrame()  # Frame for status label
    status_box.setFrameShape(QFrame.Shape.StyledPanel)
    status_box.setFrameShadow(QFrame.Shadow.Raised)
    status_box.setStyleSheet(
        "QFrame { background: #181818; border-radius: 2px; margin-bottom: 2px; padding: 0 12px; min-height: 0; }"
    )
    status_layout = QHBoxLayout(status_box)
    status_layout.setContentsMargins(0, 0, 0, 0)
    status_layout.setSpacing(0)
    status_layout.setAlignment(
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    )
    self.status_label = QLabel("Connecting to server...")  # Status text
    self.status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    self.status_label.setStyleSheet("padding: 0; margin: 0;")
    status_layout.addWidget(self.status_label)
    status_row.addWidget(status_box, stretch=0)
    status_row.addStretch(1)  # Right column stretch for centering
    layout.addLayout(status_row)

    # --- HP Row (Player and Opponent HP) ---
    hp_row = QHBoxLayout()
    self.hp_label = QLabel()  # Player HP label
    self.hp_label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    self.opponent_hp_label = QLabel()  # Opponent HP label
    self.opponent_hp_label.setAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )
    hp_row.addWidget(self.hp_label)
    hp_row.addStretch(1)
    hp_row.addWidget(self.opponent_hp_label)
    layout.addLayout(hp_row)

    # --- Loaded Row (Player and Opponent Loaded Status) ---
    loaded_row = QHBoxLayout()
    self.loaded_label = QLabel("Loaded: No")
    self.loaded_label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    self.enemy_loaded_label = QLabel("Loaded: No")
    self.enemy_loaded_label.setAlignment(
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )
    loaded_row.addWidget(self.loaded_label)
    loaded_row.addStretch(1)
    loaded_row.addWidget(self.enemy_loaded_label)
    layout.addLayout(loaded_row)

    # --- HP Display Helper Function ---
    def hp_to_hearts(hp, color):
        heart = f'<span style="color:{color}; font-size:18px;">&#10084;</span>'
        return (
            heart * hp
            + '<span style="color:#444; font-size:18px;">&#10084;</span>' * (3 - hp)
        )

    self.hp_to_hearts = hp_to_hearts  # Attach for later use
    self.hp_label.setText(f"Your HP: {hp_to_hearts(3, '#ff2d55')}")  # Red hearts
    self.opponent_hp_label.setText(
        f"Enemy HP: {hp_to_hearts(3, '#a259ff')}"
    )  # Purple hearts
    self.loaded_label.setText("Loaded: ❌")
    self.enemy_loaded_label.setText("Loaded: ❌")

    # --- Game Area Frame (Main Game Board) ---
    self.game_area_frame = QFrame()
    self.game_area_frame.setObjectName("GameAreaFrame")
    self.game_area_frame.setStyleSheet(
        "QFrame#GameAreaFrame { background: #444; border-radius: 8px; padding: 4px; border: 4px solid #000; }"
    )
    self.game_area_frame.setMinimumHeight(120)
    layout.addWidget(self.game_area_frame, stretch=1)

    # --- Round Row (Round Number) ---
    round_row = QHBoxLayout()
    self.round_label = QLabel("Round: 1")
    self.round_label.setAlignment(
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    )
    self.round_label.setStyleSheet("font-size: 16px; color: #ffcc00; margin: 8px 0;")
    round_row.addWidget(self.round_label)
    round_row.addStretch(1)
    layout.addLayout(round_row)

    # --- Action Buttons Row ---
    action_row = QHBoxLayout()
    action_row.setSpacing(4)  # Spacing between buttons
    self.attack_btn = QPushButton("Attack")
    self.block_btn = QPushButton("Block")
    self.load_btn = QPushButton("Load")
    self.submit_btn = QPushButton("Submit")
    self.reset_btn = QPushButton("Reset")
    self.hide_game_btn = QPushButton(">")
    self.hide_game_btn.setCheckable(True)
    # Restore original button styles
    btn_style = (
        "QPushButton {"
        "  background-color: #222;"
        "  color: #fff;"
        "  font-size: 18px;"
        "  font-weight: bold;"
        "  border-radius: 8px;"
        "  padding: 12px 0;"
        "  margin: 0 4px;"
        "}"
        "QPushButton:disabled {"
        "  background-color: #444;"
        "  color: #888;"
        "}"
    )
    for btn in [
        self.attack_btn,
        self.block_btn,
        self.load_btn,
        self.submit_btn,
        self.reset_btn,
        self.hide_game_btn,
    ]:
        btn.setStyleSheet(btn_style)
    self.attack_btn.setMinimumWidth(90)
    self.block_btn.setMinimumWidth(90)
    self.load_btn.setMinimumWidth(90)
    self.submit_btn.setMinimumWidth(90)
    self.reset_btn.setMinimumWidth(90)
    self.hide_game_btn.setMinimumWidth(40)
    action_row.addWidget(self.attack_btn)
    action_row.addWidget(self.block_btn)
    action_row.addWidget(self.load_btn)
    action_row.addWidget(self.submit_btn)
    action_row.addWidget(self.reset_btn)
    action_row.addWidget(self.hide_game_btn)
    layout.addLayout(action_row)

    # --- Block Points Row (Shield Emojis) ---
    self.block_points_label = QLabel()
    self.block_points_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    self.block_points_label.setStyleSheet(
        "font-size: 18px; color: #00bcd4; margin: 4px 0;"
    )
    layout.addWidget(self.block_points_label)

    # --- Block Points Display Helper Function ---
    def block_points_to_emojis(points):
        shield = '<span style="font-size:22px;">🛡️</span>'
        return (
            shield * points
            + '<span style="font-size:22px; color:#444;">🛡️</span>' * (3 - points)
        )

    self.block_points_to_emojis = block_points_to_emojis
    self.block_points_label.setText(block_points_to_emojis(3))

    return layout


# =========================================
#         DARK THEME STYLESHEET
# =========================================
def apply_dark_theme(self):
    self.setStyleSheet(
        self.styleSheet()
        + "\n"
        + """
        QWidget {
            background-color: #222;
            color: #fff;
        }
        QPushButton {
            background-color: #333;
            color: #fff;
            border-radius: 6px;
            padding: 8px 0;
        }
        QPushButton:disabled {
            background-color: #444;
            color: #888;
        }
        QLineEdit, QTextEdit {
            background-color: #181818;
            color: #fff;
            border: 1px solid #444;
            border-radius: 4px;
        }
        QFrame#GameArea {
            background: #181818;
            border-radius: 10px;
            border: none;
        }
        QFrame#ChatArea {
            background: #181818;
            border-radius: 10px;
            border: none;
        }
        """
    )
