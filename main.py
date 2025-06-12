# =========================================
#              IMPORTS
# =========================================
from PyQt6.QtWidgets import QApplication
import asyncio
import qasync
from client import GameClient


# =========================================
#         MAIN ENTRY POINT
# =========================================
async def main():
    app = QApplication([])  # Create Qt application
    loop = qasync.QEventLoop(app)  # Use qasync event loop for Qt/asyncio integration
    asyncio.set_event_loop(loop)

    client = GameClient(loop)  # Create game client window
    client.show()  # Show the main window

    asyncio.create_task(client.receive_messages())  # Start receiving messages

    await asyncio.Future()  # Run forever (until app exit)


if __name__ == "__main__":
    qasync.run(main())  # Start the async Qt app
