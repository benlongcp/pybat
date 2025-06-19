# game-server.py - Game server logic for handling multiplayer matches
# =========================================
#              IMPORTS
# =========================================
import asyncio  # Async event loop
import websockets  # WebSocket server
import json  # JSON encoding/decoding
import uuid  # Unique room IDs

# =========================================
#         GLOBAL GAME STATE
# =========================================
rooms = {}  # Maps room_id to dict: { 'players': [ws1, ws2], 'round': int }
players = {}  # Maps WebSocket to player state
submitted_actions = (
    {}
)  # Tracks submitted actions per room: { room_id: { ws: "action" } }
pending_resets = {}  # Tracks which players in a room have requested reset
client_counter = 1  # Global counter for assigning default client names

# =========================================
#         GLOBAL LOBBY STATE
# =========================================
USERS = set()  # Set of all connected websockets
LOBBY = {}  # Maps websocket to username
OPEN_ROOMS = {}  # Maps room_id to dict: { 'id': room_id, 'users': [usernames] }
USERS_IN_ROOM = set()  # Set of users currently in a room
INVITES = {}  # Maps inviter websocket to invitee websocket


# =========================================
#         UTILITY FUNCTIONS
# =========================================
async def notify_pair_status(room_id):
    # Notifies both players in a room that the game is ready to update
    for player in rooms[room_id]["players"]:
        await player.send(json.dumps({"type": "update"}))


async def notify_lobby():
    if USERS:
        # Mark users in a room
        usernames = []
        for user in USERS:
            name = LOBBY.get(user, "?")
            if user in USERS_IN_ROOM:
                name += " (in room)"
            usernames.append(name)
        open_rooms = [r["id"] for r in OPEN_ROOMS.values()]
        message = json.dumps(
            {
                "type": "lobby_update",
                "users": usernames,
                "open_rooms": open_rooms,
            }
        )
        # Remove closed websockets before broadcasting
        to_remove = set()
        for user in USERS:
            try:
                await user.send(message)
            except Exception:
                to_remove.add(user)
        for user in to_remove:
            USERS.discard(user)
            LOBBY.pop(user, None)


# =========================================
#         MESSAGE HANDLER
# =========================================
async def handle_message(ws, data):
    global client_counter
    if data["type"] == "name":
        # Client sent their chosen name; store it or assign default
        name = data.get("name", None)
        if name and name.strip():
            players[ws]["name"] = name.strip()
        else:
            players[ws]["name"] = f"client{client_counter}"
            await ws.send(
                json.dumps({"type": "lobby_joined", "name": players[ws]["name"]})
            )
            client_counter += 1
    elif data["type"] == "submit":
        room_id = players[ws].get("room")
        if not room_id or room_id not in rooms:
            return
        action = data["action"]
        submitted_actions.setdefault(room_id, {})[ws] = action
        if len(submitted_actions[room_id]) == 2:
            await process_round(room_id)
    elif data["type"] == "reset":
        room_id = players[ws].get("room")
        if not room_id or room_id not in rooms:
            return
        if room_id not in pending_resets:
            pending_resets[room_id] = set()
        pending_resets[room_id].add(ws)
        if (
            room_id in rooms
            and len(rooms[room_id]["players"]) == 2
            and len(pending_resets[room_id]) == 2
        ):
            for player in rooms[room_id]["players"]:
                players[player]["hp"] = 3
                players[player]["loaded"] = False
                players[player]["block_points"] = 3
            rooms[room_id][
                "round"
            ] = -1  # Offset round to -1 so broadcast_state sends round 1
            submitted_actions[room_id] = {}
            pending_resets[room_id] = set()
            await broadcast_state(room_id)
        else:
            await ws.send(json.dumps({"type": "waiting_for_reset"}))
    elif data["type"] == "chat":
        room_id = players[ws].get("room")
        if not room_id or room_id not in rooms:
            return
        sender_name = players[ws].get("name", "Player")
        message = data["message"]
        for player in rooms[room_id]["players"]:
            if player != ws:
                await player.send(
                    json.dumps(
                        {"type": "chat", "sender": sender_name, "message": message}
                    )
                )
    elif data["type"] == "lobby_chat":
        # Broadcast lobby chat message to all users in the lobby
        sender = LOBBY.get(ws, "?")
        message = data.get("message", "")
        print(f"[SERVER] Received lobby_chat from {sender}: {message}")
        print(f"[SERVER] USERS: {[LOBBY.get(u, '?') for u in USERS]}")
        print(f"[SERVER] USERS_IN_ROOM: {[LOBBY.get(u, '?') for u in USERS_IN_ROOM]}")
        for user_ws in USERS:
            if user_ws in LOBBY and user_ws not in USERS_IN_ROOM:
                try:
                    print(f"[SERVER] Sending lobby_chat to {LOBBY.get(user_ws, '?')}")
                    await user_ws.send(
                        json.dumps(
                            {"type": "lobby_chat", "sender": sender, "message": message}
                        )
                    )
                except Exception as e:
                    print(
                        f"[SERVER] Failed to send lobby_chat to {LOBBY.get(user_ws, '?')}: {e}"
                    )


# =========================================
#         MESSAGE HANDLER (LOBBY)
# =========================================
async def handle_lobby_message(ws, data):
    global INVITES
    if data.get("type") == "create_room":
        # Prevent user from creating more than one open room or being in multiple rooms
        if ws in USERS_IN_ROOM:
            # Already in a room, ignore request
            return
        for room in OPEN_ROOMS.values():
            if LOBBY[ws] in room["users"]:
                # Already has an open room, ignore request
                return
        room_id = f"{LOBBY[ws]}'s room"
        OPEN_ROOMS[room_id] = {"id": room_id, "users": [LOBBY[ws]]}
        USERS_IN_ROOM.add(ws)
        await ws.send(json.dumps({"type": "room_joined", "usernames": [LOBBY[ws]]}))
        await notify_lobby()
    elif data.get("type") == "join_room":
        # Prevent user from joining if already in a room
        if ws in USERS_IN_ROOM:
            return
        room_id = data.get("room_id")
        room = OPEN_ROOMS.get(room_id)
        if room and len(room["users"]) == 1:
            room["users"].append(LOBBY[ws])
            # Find the websocket of the room creator
            creator_ws = None
            for w, name in LOBBY.items():
                if name == room["users"][0]:
                    creator_ws = w
                    break
            USERS_IN_ROOM.add(ws)
            USERS_IN_ROOM.add(creator_ws)
            usernames = room["users"]
            # Notify both clients that they have joined the room
            await ws.send(json.dumps({"type": "room_joined", "usernames": usernames}))
            await creator_ws.send(
                json.dumps({"type": "room_joined", "usernames": usernames})
            )
            await notify_lobby()
    elif data.get("type") == "leave_room":
        name = LOBBY.get(ws)
        USERS_IN_ROOM.discard(ws)
        # Remove user from any open room
        for room_id, room in list(OPEN_ROOMS.items()):
            if name in room["users"]:
                room["users"].remove(name)
                if not room["users"]:
                    del OPEN_ROOMS[room_id]
        # --- Notify the other player in a game room, if any ---
        user_room = players.get(ws, {}).get("room")
        if user_room and user_room in rooms:
            other_players = [p for p in rooms[user_room]["players"] if p != ws]
            for other in other_players:
                try:
                    await other.send(json.dumps({"type": "room_left"}))
                    USERS_IN_ROOM.discard(
                        other
                    )  # Remove the other player from USERS_IN_ROOM
                    if other in players:
                        players[other]["room"] = None
                except Exception:
                    pass
            del rooms[user_room]
        if ws in players:
            players[ws]["room"] = None
        await ws.send(json.dumps({"type": "room_left"}))
        await notify_lobby()
    elif data.get("type") == "invite":
        # Only allow one invite at a time per user
        to_name = data.get("to")
        from_name = LOBBY.get(ws)
        if not to_name or not from_name:
            return
        # Find the websocket for the invitee
        to_ws = None
        for user_ws, name in LOBBY.items():
            if name == to_name:
                to_ws = user_ws
                break
        if not to_ws or to_ws in INVITES.values() or ws in INVITES:
            # Already invited or has a pending invite
            return
        INVITES[ws] = to_ws
        await to_ws.send(json.dumps({"type": "invite_received", "from": from_name}))
    elif data.get("type") == "invite_response":
        from_name = data.get("from")
        accepted = data.get("accepted")
        # Find inviter websocket
        inviter_ws = None
        for user_ws, name in LOBBY.items():
            if name == from_name:
                inviter_ws = user_ws
                break
        if not inviter_ws or inviter_ws not in INVITES:
            return
        invitee_ws = INVITES[inviter_ws]
        # Notify inviter of result
        await inviter_ws.send(
            json.dumps(
                {"type": "invite_result", "from": LOBBY.get(ws), "accepted": accepted}
            )
        )
        if accepted:
            # Create a room for both users
            room_id = f"{from_name} vs {LOBBY.get(ws)}"
            OPEN_ROOMS[room_id] = {"id": room_id, "users": [from_name, LOBBY.get(ws)]}
            USERS_IN_ROOM.add(inviter_ws)
            USERS_IN_ROOM.add(ws)
            await inviter_ws.send(
                json.dumps(
                    {"type": "room_joined", "usernames": [from_name, LOBBY.get(ws)]}
                )
            )
            await ws.send(
                json.dumps(
                    {"type": "room_joined", "usernames": [from_name, LOBBY.get(ws)]}
                )
            )
            await notify_lobby()
        INVITES.pop(inviter_ws, None)
        await notify_lobby()
    elif data.get("type") == "enter_room":
        # This is sent by the inviter after invite is accepted, to trigger game session
        # Find the open room with both users
        inviter_name = LOBBY.get(ws)
        for room_id, room in list(OPEN_ROOMS.items()):
            if inviter_name in room["users"] and len(room["users"]) == 2:
                # Create a game session for both users
                user_names = room["users"]
                ws1 = None
                ws2 = None
                for user_ws, name in LOBBY.items():
                    if name == user_names[0]:
                        ws1 = user_ws
                    elif name == user_names[1]:
                        ws2 = user_ws
                if ws1 and ws2:
                    # Set up the game room
                    room_uuid = str(uuid.uuid4())
                    rooms[room_uuid] = {"players": [ws1, ws2], "round": 0}
                    players[ws1]["room"] = room_uuid
                    players[ws2]["room"] = room_uuid
                    players[ws1]["hp"] = 3
                    players[ws2]["hp"] = 3
                    players[ws1]["loaded"] = False
                    players[ws2]["loaded"] = False
                    players[ws1]["block_points"] = 3
                    players[ws2]["block_points"] = 3
                    # Remove from open rooms
                    del OPEN_ROOMS[room_id]
                    await notify_lobby()
                    await notify_pair_status(room_uuid)
                break


# =========================================
#         ROUND RESOLUTION
# =========================================
async def process_round(room_id):
    actions = submitted_actions[room_id]
    players_list = rooms[room_id]["players"]
    a_ws, b_ws = players_list
    a_action = actions[a_ws]
    b_action = actions[b_ws]
    a = players[a_ws]
    b = players[b_ws]

    def resolve(attacker, defender, attacker_action, defender_action):
        if attacker_action == "attack":
            if attacker["loaded"]:
                if defender_action != "block":
                    defender["hp"] -= 1
                attacker["loaded"] = False
        elif attacker_action == "block":
            # Deplete block points when block is used
            if "block_points" not in attacker:
                attacker["block_points"] = 3
            if attacker["block_points"] > 0:
                attacker["block_points"] -= 1
        elif attacker_action == "load":
            if not attacker["loaded"]:
                attacker["loaded"] = True
        elif attacker_action == "standby":
            # Standby does nothing except replenish block points (handled below)
            pass

    resolve(a, b, a_action, b_action)
    resolve(b, a, b_action, a_action)

    # Block point replenishment for standby (max 3)
    if a_action == "standby":
        if "block_points" not in a:
            a["block_points"] = 3
        if a["block_points"] < 3:
            a["block_points"] += 1
    if b_action == "standby":
        if "block_points" not in b:
            b["block_points"] = 3
        if b["block_points"] < 3:
            b["block_points"] += 1

    if "round" in rooms[room_id]:
        rooms[room_id]["round"] += 1
    for ws, my_action, opp_action in [
        (a_ws, a_action, b_action),
        (b_ws, b_action, a_action),
    ]:
        await ws.send(
            json.dumps(
                {
                    "type": "actions",
                    "your_action": my_action,
                    "opponent_action": opp_action,
                }
            )
        )
    submitted_actions[room_id] = {}
    await broadcast_state(room_id)
    for player in players_list:
        if players[player]["hp"] <= 0:
            winner = (
                players[a_ws]["name"]
                if players[a_ws]["hp"] > 0
                else players[b_ws]["name"]
            )
            for p in players_list:
                await p.send(json.dumps({"type": "game_over", "winner": winner}))
            return


# =========================================
#         BROADCAST GAME STATE
# =========================================
async def broadcast_state(room_id):
    if "round" not in rooms[room_id]:
        rooms[room_id]["round"] = -2
    round_number = rooms[room_id]["round"] + 1
    players_list = rooms[room_id]["players"]
    if len(players_list) == 2:
        name_a = players[players_list[0]].get("name", "Player1")
        name_b = players[players_list[1]].get("name", "Player2")
    else:
        name_a = name_b = "Player"
    for player in rooms[room_id]["players"]:
        opponent = [p for p in rooms[room_id]["players"] if p != player][0]
        your_name = players[player].get("name", "Player")
        opponent_name = players[opponent].get("name", "Enemy")
        # Ensure block_points is always present
        if "block_points" not in players[player]:
            players[player]["block_points"] = 3
        if "block_points" not in players[opponent]:
            players[opponent]["block_points"] = 3
        await player.send(
            json.dumps(
                {
                    "type": "update",
                    "hp": players[player]["hp"],
                    "opponent_hp": players[opponent]["hp"],
                    "loaded": players[player]["loaded"],
                    "opponent_loaded": players[opponent]["loaded"],
                    "block_points": players[player]["block_points"],
                    "opponent_block_points": players[opponent]["block_points"],
                    "round": round_number,
                    "your_name": your_name,
                    "opponent_name": opponent_name,
                }
            )
        )


# =========================================
#         CONNECTION HANDLER (LOBBY)
# =========================================
async def handler(ws):
    try:
        name_msg = await ws.recv()
        name_data = (
            json.loads(name_msg) if name_msg.startswith("{") else {"name": name_msg}
        )
        name = name_data.get("name", "Player")
        LOBBY[ws] = name
        USERS.add(ws)
        players[ws] = {"name": name, "hp": 3, "loaded": False, "room": None}
        await notify_lobby()
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            # Lobby message handling
            if data.get("type") in (
                "create_room",
                "join_room",
                "leave_room",
                "invite",
                "invite_response",
                "enter_room",
            ):
                await handle_lobby_message(ws, data)
            # Game message handling
            elif data.get("type") in ("submit", "reset", "chat", "lobby_chat"):
                await handle_message(ws, data)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        USERS.discard(ws)
        name = LOBBY.pop(ws, None)
        USERS_IN_ROOM.discard(ws)
        # Remove user from any open room
        for rid, room in list(OPEN_ROOMS.items()):
            if name in room["users"]:
                room["users"].remove(name)
                if not room["users"]:
                    del OPEN_ROOMS[rid]
        # --- Notify the other player in a game room, if any ---
        user_room = players.get(ws, {}).get("room")
        if user_room and user_room in rooms:
            other_players = [p for p in rooms[user_room]["players"] if p != ws]
            for other in other_players:
                try:
                    await other.send(json.dumps({"type": "room_left"}))
                    USERS_IN_ROOM.discard(
                        other
                    )  # Remove the other player from USERS_IN_ROOM
                    if other in players:
                        players[other]["room"] = None
                except Exception:
                    pass
            del rooms[user_room]
        if ws in players:
            players[ws]["room"] = None
        await notify_lobby()


# =========================================
#         SERVER ENTRY POINT
# =========================================
async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

# TODO: Add comments to all server functions and classes, including any stubs or placeholders.
