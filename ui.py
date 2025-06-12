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
        heart = f'<span style="color:{color};">❤</span>'
        empty = f'<span style="color:#555;">❤</span>'
        return heart * hp + empty * (3 - hp)

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
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    round_row.addWidget(self.round_label, alignment=Qt.AlignmentFlag.AlignLeft)
    round_row.addStretch(1)
    layout.addLayout(round_row)

    # --- Action Buttons Row ---
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(4)  # Spacing between buttons
    self.attack_btn = QPushButton("Attack 🚀💢")
    self.block_btn = QPushButton("Block 🛡️🛡️")
    self.load_btn = QPushButton("Load 🔫⏳")
    btn_layout.addWidget(self.attack_btn)
    btn_layout.addWidget(self.block_btn)
    btn_layout.addWidget(self.load_btn)
    layout.addLayout(btn_layout)

    layout.addSpacing(16)  # Spacing between action and submit

    # --- Submit Button ---
    self.submit_btn = QPushButton("Submit Move")
    self.submit_btn.setEnabled(False)
    layout.addWidget(self.submit_btn)

    layout.addSpacing(16)  # Spacing between submit and reset

    # --- Reset Button ---
    self.reset_btn = QPushButton("Reset Game")
    self.reset_btn.setEnabled(False)
    layout.addWidget(self.reset_btn)

    layout.addSpacing(16)  # Spacing between reset and hide chat

    # --- Hide Chat Button (if present) ---
    if hasattr(self, "message_toggle_btn"):
        layout.addWidget(self.message_toggle_btn)

    return layout


# =========================================
#         DARK THEME STYLESHEET
# =========================================
def apply_dark_theme(self):
    self.setStyleSheet(
        """
        QWidget {
            background-color: #121212;
            color: #ffffff;
            font-size: 16px;
        }
        QLabel {
            padding: 6px;
            border-radius: 6px;
        }
        QPushButton {
            background-color: #222;
            color: #ffcc00;
            padding: 8px;
            border: 2px solid #ffcc00;
            border-radius: 6px;
        }
        QPushButton:disabled {
            background-color: #444;
            color: #888;
            border-color: #666;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #333;
            border-radius: 6px;
        }
    """
    )
    self.setMinimumSize(800, 500)
