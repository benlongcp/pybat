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
#         UTILITY FUNCTIONS
# =========================================
async def notify_pair_status(room_id):
    # Notifies both players in a room that the game is ready to update
    for player in rooms[room_id]["players"]:
        await player.send(json.dumps({"type": "update"}))


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
        # Client submitted their action (attack, block, load)
        action = data["action"]
        room_id = players[ws]["room"]
        submitted_actions.setdefault(room_id, {})[ws] = action
        if len(submitted_actions[room_id]) == 2:
            await process_round(room_id)
    elif data["type"] == "reset":
        room_id = players[ws]["room"]
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
            rooms[room_id][
                "round"
            ] = -1  # Offset round to -1 so broadcast_state sends round 1
            submitted_actions[room_id] = {}
            pending_resets[room_id] = set()
            await broadcast_state(room_id)
        else:
            await ws.send(json.dumps({"type": "waiting_for_reset"}))
    elif data["type"] == "chat":
        room_id = players[ws]["room"]
        sender_name = players[ws].get("name", "Player")
        message = data["message"]
        for player in rooms[room_id]["players"]:
            if player != ws:
                await player.send(
                    json.dumps(
                        {"type": "chat", "sender": sender_name, "message": message}
                    )
                )


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
        elif attacker_action == "load":
            if not attacker["loaded"]:
                attacker["loaded"] = True

    resolve(a, b, a_action, b_action)
    resolve(b, a, b_action, a_action)
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
        rooms[room_id]["round"] = 0
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
        await player.send(
            json.dumps(
                {
                    "type": "update",
                    "hp": players[player]["hp"],
                    "opponent_hp": players[opponent]["hp"],
                    "loaded": players[player]["loaded"],
                    "opponent_loaded": players[opponent]["loaded"],
                    "round": round_number,
                    "your_name": your_name,
                    "opponent_name": opponent_name,
                }
            )
        )


# =========================================
#         CONNECTION HANDLER
# =========================================
async def handler(ws):
    players[ws] = {"room": None, "hp": 3, "loaded": False, "name": "Player"}
    assigned = False
    for room_id, room in rooms.items():
        if len(room["players"]) == 1:
            room["players"].append(ws)
            players[ws]["room"] = room_id
            players[room["players"][0]]["room"] = room_id
            if room["round"] == 0:
                room["round"] = 1
            assigned = True
            break
    if assigned:
        await broadcast_state(room_id)
    if not assigned:
        room_id = str(uuid.uuid4())
        rooms[room_id] = {"players": [ws], "round": -1}
        players[ws]["room"] = room_id
        await ws.send(json.dumps({"type": "waiting"}))
    try:
        async for message in ws:
            data = json.loads(message)
            await handle_message(ws, data)
    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        room_id = players[ws]["room"]
        if room_id in rooms:
            rooms[room_id]["players"] = [
                p for p in rooms[room_id]["players"] if p != ws
            ]
            if not rooms[room_id]["players"]:
                del rooms[room_id]
            else:
                for player in rooms[room_id]["players"]:
                    try:
                        if player.open:
                            await player.send(json.dumps({"type": "waiting"}))
                    except Exception as e:
                        print(f"Error sending to player during cleanup: {e}")
        if ws in players:
            del players[ws]
        if room_id in submitted_actions:
            del submitted_actions[room_id]
        if room_id in pending_resets:
            if not rooms.get(room_id) or not rooms[room_id]["players"]:
                del pending_resets[room_id]


# =========================================
#         SERVER ENTRY POINT
# =========================================
async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
