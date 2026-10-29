"""Start the Airport Management System GUI.

Usage:
    python run.py            # start (creates data/airport.db with sample data on first run)
    python run.py --reset    # delete the database and recreate fresh sample data
"""
import sys

from ams.config import DB_PATH
from ams.database import create_database


def main() -> None:
    reset = "--reset" in sys.argv
    conn = create_database(DB_PATH, reset=reset)
    try:
        from ams.gui.app import AirportApp
    except ImportError as exc:   # tkinter missing (some Linux installs)
        sys.exit(f"Tkinter is not available: {exc}\nInstall it (e.g. 'sudo apt install python3-tk') and retry.")
    app = AirportApp(conn)
    app.mainloop()
    conn.close()


if __name__ == "__main__":
    main()
