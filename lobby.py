from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox
import asyncio
import json


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


class LobbyWindow(QtWidgets.QWidget):
    def __init__(self, ws, username):
        super().__init__()
        self.ws = ws
        self.username = username
        self.setWindowTitle(f"Lobby - {username}")
        self.resize(600, 400)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.user_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.user_list)
        self.invite_button = QtWidgets.QPushButton("Invite")
        self.invite_button.setEnabled(False)
        self.layout.addWidget(self.invite_button)
        self.room_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.room_list)
        self.create_room_button = QtWidgets.QPushButton("Create Open Room")
        self.create_room_button.clicked.connect(self.create_open_room)
        room_col = QtWidgets.QVBoxLayout()
        room_col.addWidget(self.room_list)
        room_col.addWidget(self.create_room_button)
        room_col.addStretch()
        self.close_room_button = QtWidgets.QPushButton("Close Room")
        self.close_room_button.setStyleSheet(
            "background-color: #c62828; color: white; font-weight: bold; border-radius: 6px; padding: 8px 0;"
        )
        self.close_room_button.setEnabled(False)
        self.close_room_button.clicked.connect(self.close_own_room)
        room_col.addWidget(self.close_room_button)
        room_col_widget = QtWidgets.QWidget()
        room_col_widget.setLayout(room_col)
        self.layout.addWidget(room_col_widget)
        self.user_list.itemSelectionChanged.connect(self.on_user_selected)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)
        self.join_room_button = QtWidgets.QPushButton("Join Room")
        self.join_room_button.setEnabled(False)
        self.join_room_button.clicked.connect(self.join_selected_room)
        room_col.addWidget(self.join_room_button)
        self.room_window = None
        self.game_window = None
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
        if selected_user == self.username or "(in room)" in selected[0].text():
            self.invite_button.setEnabled(False)
            return
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
        is_joinable = False
        if room_id.endswith("'s room"):
            owner = room_id[:-7]
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
        print(f"[LobbyWindow] update_users called with: {users}")
        self.user_list.clear()
        for user in users:
            label = user
            if user.startswith(self.username):
                if "(you)" not in label:
                    label = label.replace(" (in room)", "") + " (you)"
                    if " (in room)" in user:
                        label += " (in room)"
            self.user_list.addItem(label)
        self.user_list.repaint()
        self.on_user_selected()

    def update_rooms(self, rooms):
        print(f"[LobbyWindow] update_rooms called with: {rooms}")
        self.room_list.clear()
        for room in rooms:
            self.room_list.addItem(room)
        has_own_room = False
        for room in rooms:
            if room.startswith(f"{self.username}'s room"):
                has_own_room = True
                break
        user_in_room = False
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            if item.text().startswith(self.username) and "(in room)" in item.text():
                user_in_room = True
                break
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
        asyncio.create_task(self.ws.send(json.dumps({"type": "leave_room"})))

    def join_selected_room(self):
        selected = self.room_list.selectedItems()
        if selected:
            room_id = selected[0].text()
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "join_room", "room_id": room_id}))
            )

    def open_room(self, usernames):
        print(f"[LobbyWindow] open_room called with: {usernames}")
        if len(usernames) == 2:
            opponent = [u for u in usernames if u != self.username][0]
            from game_window import GameClient

            self.game_window = GameClient(
                self.ws.loop, self.ws, self.username, opponent, parent_lobby=self
            )
            self.game_window.show()
            self.hide()
            import asyncio, json

            asyncio.create_task(self.ws.send(json.dumps({"type": "enter_room"})))
        else:
            QMessageBox.information(
                None, "Room Created", "Waiting for another player to join..."
            )

    def show_lobby(self):
        print("[LobbyWindow] show_lobby called")
        self.show()
        if self.game_window:
            self.game_window.close()
            self.game_window = None

    def create_open_room(self):
        asyncio.create_task(self.ws.send(json.dumps({"type": "create_room"})))
