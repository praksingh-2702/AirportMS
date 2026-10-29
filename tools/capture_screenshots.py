"""Drive the real GUI and save a screenshot of each screen (used for the report).

Run on a machine with a display:  python tools/capture_screenshots.py
Screenshots are written to docs/screenshots/. Uses a separate throw-away database.
Requires Pillow (pip install pillow) for ImageGrab.
"""
import os
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ams.database import create_database          # noqa: E402
from ams.gui.app import AirportApp                 # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
GRAB_CMD = os.environ.get("AMS_GRAB_CMD")          # e.g. "import -window root {path}" under Xvfb


def grab(root, name):
    root.update()
    root.after(250)
    root.update()
    path = os.path.join(OUT, f"{name}.png")
    if GRAB_CMD:
        os.system(GRAB_CMD.format(path=path))
    else:
        from PIL import ImageGrab
        x, y = root.winfo_rootx(), root.winfo_rooty()
        ImageGrab.grab((x, y, x + root.winfo_width(), y + root.winfo_height())).save(path)
    print("saved", path)


def main():
    os.makedirs(OUT, exist_ok=True)
    db = os.path.join(tempfile.mkdtemp(), "shots.db")
    conn = create_database(db, reset=True)
    app = AirportApp(conn)
    app.geometry("1100x700+0+0")
    shown = []
    # Record dialogs instead of blocking on them; one chosen dialog is drawn as a Toplevel for its screenshot.
    messagebox.showinfo = lambda title, msg, **k: shown.append((title, msg))
    messagebox.showerror = lambda title, msg, **k: shown.append((title, msg))
    messagebox.showwarning = lambda title, msg, **k: shown.append((title, msg))
    messagebox.askyesno = lambda *a, **k: True

    def dialog(title, msg):
        top = tk.Toplevel(app)
        top.title(title)
        top.geometry("+380+260")
        tk.Label(top, text=msg, justify="left", font=("Courier", 11), padx=24, pady=18).pack()
        tk.Button(top, text="OK", width=10, command=top.destroy).pack(pady=(0, 14))
        return top

    def login(user, pw):
        app.show_login()
        app.update()
        app.current.username.set(user)
        app.current.password.set(pw)
        grab(app, f"00_login_{user}") if user == "admin" else None
        app.current.login()
        app.update()

    # ---- invalid login (error message) ----
    app.update()
    app.current.username.set("admin")
    app.current.password.set("wrongpass1")
    app.current.login()
    d = dialog(*shown[-1]); grab(app, "01_login_error"); d.destroy()

    # ---- ADMIN ----
    login("admin", "admin123")
    grab(app, "02_admin_flights")
    fv = app.tabs["Flights"]
    fv.form.set({"flight_no": "AI2O2", "airline": "Air India", "origin": "DEL", "destination": "BOM",
                 "departure": "2020-01-01 10:00", "arrival": "2020-01-01 12:00", "rows": "20",
                 "fare": "5000", "gate": "Z9"})
    fv.add()
    d = dialog(*shown[-1]); grab(app, "03_admin_flight_validation_error"); d.destroy()
    nb = app.notebook
    nb.select(app.tabs["Users"]); grab(app, "04_admin_users")
    nb.select(app.tabs["Bookings"]); grab(app, "05_admin_all_bookings")

    # ---- PASSENGER ----
    login("priya", "pass1234")
    grab(app, "06_passenger_search")
    bv = app.tabs["Book Flights"]
    first = bv.results.tree.get_children()[1]
    bv.results.select(first)
    bv.book()
    app.update()
    seatmap = [w for w in bv.winfo_children() if isinstance(w, tk.Toplevel)][-1]
    seatmap.geometry("+700+60")
    seatmap.pick("2C")
    grab(app, "07_passenger_seat_map")
    seatmap.confirm()
    d = dialog(*shown[-1]); grab(app, "08_passenger_booking_confirmed"); d.destroy()

    # ---- STAFF ----
    login("staff1", "staff123")
    cv = app.tabs["Check-in & Baggage"]
    cv.pnr.set("K7Q2MA")
    cv.check_in()
    cv.weight.set("17.5"); cv.add_bag()
    cv.weight.set("4.0"); cv.add_bag()
    grab(app, "09_staff_checkin_boarding_pass")
    cv.weight.set("40"); cv.add_bag()
    d = dialog(*shown[-1]); grab(app, "10_staff_bag_weight_error"); d.destroy()

    # ---- PASSENGER boarding pass ----
    login("priya", "pass1234")
    app.notebook.select(app.tabs["Boarding Pass"]); app.tabs["Boarding Pass"].refresh()
    grab(app, "11_passenger_boarding_pass")
    app.destroy()


if __name__ == "__main__":
    main()
