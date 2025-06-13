# =========================================
#              IMPORTS
# =========================================
import asyncio
import qasync
from client import main_async


# =========================================
#         MAIN ENTRY POINT
# =========================================
if __name__ == "__main__":
    qasync.run(main_async())
