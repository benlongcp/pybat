# =========================================
#              IMPORTS
# =========================================
import websockets  # WebSocket client
import json  # JSON encoding/decoding
import asyncio  # Asyncio event loop


# =========================================
#         CONNECT TO SERVER
# =========================================
async def connect_to_server(uri, name="Player"):
    """
    Connect to the game server via WebSocket.
    Sends the player's name after connecting.
    Returns the websocket object or None on failure.
    """
    try:
        websocket = await websockets.connect(uri)
        await websocket.send(json.dumps({"type": "name", "name": name}))
        return websocket
    except (websockets.ConnectionClosed, websockets.ConnectionClosedOK):
        print("WebSocket connection closed cleanly during connect.")
        return None
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        return None
