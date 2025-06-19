# main_async.py - Async entry point for launching the game client
# This module contains the main asynchronous logic for the game client,
# including the setup of the QApplication, event loop, and the connection
# to the WebSocket server. It also handles the user prompt for the username
# and the transition to the LobbyWindow upon successful connection.

# TODO: Add comments to all async main functions and logic, including any stubs or placeholders.

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
    # Start the QApplication and set up the event loop
    print("[main_async] Starting QApplication")
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Prompt the user for their name
    prompt = NamePrompt()
    print("[main_async] Showing NamePrompt dialog")
    if prompt.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        username = prompt.get_name()
        print(f"[main_async] Username entered: {username}")

        # Validate the entered username
        if not username:
            print("[main_async] No username entered, exiting.")
            sys.exit()

        # Connect to the WebSocket server
        print("[main_async] Connecting to websocket server...")
        async with websockets.connect("ws://localhost:8765") as ws:
            ws.loop = asyncio.get_event_loop()
            print("[main_async] Connected to server, sending name...")

            # Send the username to the server
            print(
                f"[main_async] Sending name message: {{'type': 'name', 'name': username}}"
            )
            await ws.send(json.dumps({"type": "name", "name": username}))
            print("[main_async] Name sent, creating LobbyWindow...")

            # Transition to the LobbyWindow
            lobby = LobbyWindow(ws, username)
            lobby.show()
            print("[main_async] LobbyWindow shown, entering handle_ws_messages loop...")

            # Handle incoming WebSocket messages
            await handle_ws_messages(ws, lobby)
            print(
                "[main_async] handle_ws_messages returned (should not happen unless disconnect)"
            )
    else:
        print("[main_async] NamePrompt dialog cancelled, exiting.")
        sys.exit()


if __name__ == "__main__":
    # Entry point for the application
    print("[main_async] __main__ entry point")
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    print("[main_async] Running main_async() in event loop")

    # Run the main_async function until completion
    loop.run_until_complete(main_async())
    print("[main_async] Event loop finished, closing loop.")
    loop.close()
