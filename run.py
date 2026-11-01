"""Start the Airport Management System GUI.

Usage:
    python run.py            # start (creates data/airport.db with sample data on first run)
    python run.py --reset    # delete the database and recreate fresh sample data
"""
import sys

from ams.config import DB_PATH
from ams.database import create_database
from ams.services import PaymentService, ScheduleService


def main() -> None:
    reset = "--reset" in sys.argv
    conn = create_database(DB_PATH, reset=reset)
    ScheduleService(conn).ensure_schedule()      # keeps flights available for the next 30 days
    PaymentService(conn).migrate_legacy()        # one-time: bookings made before payments existed count as paid
    try:
        from ams.gui.app import AirportApp
    except ImportError as exc:   # tkinter missing (some Linux installs)
        sys.exit(f"Tkinter is not available: {exc}\nInstall it (e.g. 'sudo apt install python3-tk') and retry.")
    app = AirportApp(conn)
    app.mainloop()
    conn.close()


if __name__ == "__main__":
    main()
