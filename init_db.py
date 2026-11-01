"""Create (or with --reset, recreate) the SQLite database with realistic sample data."""
import sys

from ams.config import DB_PATH
from ams.database import create_database
from ams.services import PaymentService, ScheduleService


if __name__ == "__main__":
    conn = create_database(DB_PATH, reset="--reset" in sys.argv)
    print(ScheduleService(conn).ensure_schedule().summary())
    PaymentService(conn).migrate_legacy()
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("users", "flights", "flight_templates", "bookings", "payments", "baggage")}
    conn.close()
    print(f"Database ready at {DB_PATH}")
    print(", ".join(f"{n} {t}" for t, n in counts.items()))
