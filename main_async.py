import sys
import json
import asyncio
from PyQt6 import QtWidgets
from dialogs import NamePrompt
from lobby import LobbyWindow
from handlers import handle_ws_messages
import websockets
from qasync import QEventLoop, asyncSlot


async def main_async():
    print("[main_async] Starting QApplication")
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    prompt = NamePrompt()
    print("[main_async] Showing NamePrompt dialog")
    if prompt.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        username = prompt.get_name()
        print(f"[main_async] Username entered: {username}")
        if not username:
            print("[main_async] No username entered, exiting.")
            sys.exit()
        print("[main_async] Connecting to websocket server...")
        async with websockets.connect("ws://localhost:8765") as ws:
            ws.loop = asyncio.get_event_loop()
            print("[main_async] Connected to server, sending name...")
            print(
                f"[main_async] Sending name message: {{'type': 'name', 'name': username}}"
            )
            await ws.send(json.dumps({"type": "name", "name": username}))
            print("[main_async] Name sent, creating LobbyWindow...")
            lobby = LobbyWindow(ws, username)
            lobby.show()
            print("[main_async] LobbyWindow shown, entering handle_ws_messages loop...")
            await handle_ws_messages(ws, lobby)
            print(
                "[main_async] handle_ws_messages returned (should not happen unless disconnect)"
            )
    else:
        print("[main_async] NamePrompt dialog cancelled, exiting.")
        sys.exit()


if __name__ == "__main__":
    print("[main_async] __main__ entry point")
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    print("[main_async] Running main_async() in event loop")
    loop.run_until_complete(main_async())
    print("[main_async] Event loop finished, closing loop.")
    loop.close()
