import json
from PyQt6.QtWidgets import QMessageBox


async def handle_ws_messages(ws, lobby):
    print("[handle_ws_messages] Entered message loop")
    async for msg in ws:
        print(f"[handle_ws_messages] Received: {msg}")
        data = json.loads(msg)
        if lobby.game_window:
            print(f"[handle_ws_messages] Forwarding to game_window: {data.get('type')}")
            if data.get("type") in (
                "update",
                "game_over",
                "chat",
                "actions",
                "room_left",
            ):
                await lobby.game_window.handle_game_message(data)
                if data.get("type") == "room_left":
                    print("[handle_ws_messages] room_left received, showing lobby")
                    lobby.show_lobby()
                continue
        if data.get("type") == "lobby_update":
            print(
                f"[handle_ws_messages] lobby_update: users={data.get('users', [])}, rooms={data.get('open_rooms', [])}"
            )
            lobby.update_users(data.get("users", []))
            lobby.update_rooms(data.get("open_rooms", []))
        elif data.get("type") == "room_joined":
            print(
                f"[handle_ws_messages] room_joined: usernames={data.get('usernames', [])}"
            )
            lobby.open_room(data.get("usernames", []))
        elif data.get("type") == "room_left":
            print("[handle_ws_messages] room_left: showing lobby")
            lobby.show_lobby()
        elif data.get("type") == "invite_received":
            from_user = data.get("from")
            print(f"[handle_ws_messages] invite_received from {from_user}")
            reply = QMessageBox.question(
                None,
                "Invitation",
                f"You have been invited by {from_user}! Accept?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                print("[handle_ws_messages] Invite accepted")
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
                print("[handle_ws_messages] Invite declined")
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
            print(
                f"[handle_ws_messages] invite_result from {from_user}, accepted={accepted}"
            )
            if accepted:
                QMessageBox.information(
                    None, "Invite Accepted", f"{from_user} accepted your invitation!"
                )
                await ws.send(json.dumps({"type": "enter_room"}))
            else:
                QMessageBox.information(
                    None, "Invite Declined", f"{from_user} declined your invitation."
                )
