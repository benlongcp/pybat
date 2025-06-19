# main.py - Entry point for launching the game client

# =========================================
#              IMPORTS
# =========================================
from qasync import run
from main_async import main_async


# =========================================
#         MAIN ENTRY POINT
# =========================================
if __name__ == "__main__":
    # TODO: Add comments to all main functions and logic, including any stubs or placeholders.
    run(main_async())
