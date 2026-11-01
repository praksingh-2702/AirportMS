"""Drive the real GUI and save a screenshot of each screen (used in Section 10.5 of the report).

Run on a machine with a display:  python tools/capture_screenshots.py
Screenshots are written to docs/screenshots/. It uses a separate throw-away database with the full 30-day
schedule, so it never touches data/airport.db. Needs Pillow (ImageGrab); the two PDF pictures also need
pypdfium2 (pip install pypdfium2) and are skipped without it.

Message boxes are intercepted so the script never blocks; the one to be shown is redrawn as a plain window,
with the program's own text, so that it appears in the capture.
"""
import os
import sys
import tempfile
import time
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ams.database import create_database               # noqa: E402
from ams.gui import widgets                            # noqa: E402
from ams.gui.app import AirportApp                     # noqa: E402
from ams.gui.payment_dialog import PaymentDialog       # noqa: E402
from ams.gui.widgets import DateEntry                  # noqa: E402
from ams.services import PaymentService, ScheduleService  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
shown = []


def intercept():
    for kind in ("showinfo", "showerror", "showwarning", "askyesno"):
        setattr(messagebox, kind, (lambda k: lambda title=None, msg=None, **kw: (shown.append((k, title, msg)), True)[1])(kind))
    widgets.filedialog.asksaveasfilename = lambda **kw: os.path.join(tempfile.gettempdir(), kw["initialfile"])
    widgets.open_file = lambda path: None
    PaymentDialog.PROCESSING_MS = 0


def main():
    os.makedirs(OUT, exist_ok=True)
    intercept()
    conn = create_database(os.path.join(tempfile.mkdtemp(), "shots.db"), reset=True)
    ScheduleService(conn).ensure_schedule()
    app = AirportApp(conn)
    app.geometry("1240x780+0+0")

    def pump(n=5):
        for _ in range(n):
            app.update_idletasks()
            app.update()

    def grab(name):
        from PIL import ImageGrab
        for _ in range(45):                               # let fades, slides and ticks finish (about 1.3 s)
            time.sleep(0.03)
            app.update()
        img = ImageGrab.grab()
        f = img.width / app.winfo_screenwidth()           # screen pixels per Tk pixel (display scaling)
        x, y = app.winfo_rootx(), app.winfo_rooty()
        img.crop((int(x * f), int(y * f), int((x + app.winfo_width()) * f), int((y + app.winfo_height()) * f))
                 ).save(os.path.join(OUT, name + ".png"))
        print("saved", name)

    def dialog(entry):
        kind, title, msg = entry
        top = tk.Toplevel(app)
        top.title(title)
        top.geometry("+470+300")
        tk.Label(top, text=msg, justify="left", font=("Segoe UI", 11), padx=26, pady=20).pack()
        tk.Button(top, text="OK", width=10, command=top.destroy).pack(pady=(0, 16))
        pump()
        return top

    def login(user, pw):
        app.show_login()
        pump()
        app.current.username.set(user)
        app.current.password.set(pw)
        shown.clear()
        app.current.login()
        pump()

    def tab(title):
        app.notebook.select(app.tabs[title])
        pump()
        return app.tabs[title]

    def find(root, cls):
        out = []
        for c in root.winfo_children():
            if isinstance(c, cls):
                out.append(c)
            out += find(c, cls)
        return out

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # ---- LOGIN
    app.update()
    grab("00_login")
    app.current.username.set("admin")
    app.current.password.set("wrongpass1")
    shown.clear()
    app.current.login()
    d = dialog(shown[-1]); grab("01_login_error"); d.destroy()
    app.current.open_register(); pump()
    grab("02_register")
    for w in app.current.winfo_children():
        if isinstance(w, tk.Toplevel):
            w.destroy()

    # ---- ADMINISTRATOR
    login("admin", "admin123")
    fv = tab("Flights")
    grab("03_admin_flights")
    de = find(fv, DateEntry)[0]
    de.open(); pump()
    grab("04_calendar")
    de.popup.close(); pump()
    fv.form.set({"flight_no": "AI2O2", "airline": "Air India", "origin": "DEL", "destination": "IXE",
                 "departure": f"{tomorrow} 10:00", "arrival": f"{tomorrow} 12:00", "rows": "20", "fare": "5000", "gate": ""})
    shown.clear(); fv.add()
    d = dialog(shown[-1]); grab("05_admin_flight_validation_error"); d.destroy(); fv.clear()
    sv = tab("Schedule")
    sv.filter_var.set("IXE"); pump()
    grab("06_admin_schedule")
    tab("Users"); grab("07_admin_users")
    tab("Bookings"); grab("08_admin_all_bookings")

    # ---- PASSENGER: search, seat, pay, cancel
    login("priya", "pass1234")
    bv = tab("Book Flights")
    bv.origin.set("IXE - Mangalore"); bv.dest.set("BLR - Bengaluru"); bv.date.set(tomorrow)
    bv.search(); pump()
    grab("09_passenger_search")
    first = bv.results.tree.get_children()[0]
    bv.results.select(first); pump()
    bv.book(); pump()
    seatmap = [w for w in bv.winfo_children() if isinstance(w, tk.Toplevel)][0]
    seatmap.pick("3C"); pump()
    grab("10_passenger_seat_map")
    seatmap.confirm(); pump()
    dlg = [w for w in bv.winfo_children() if isinstance(w, PaymentDialog)][0]
    dlg.v_number.set("4111111111111111"); dlg.v_name.set("Priya Verma"); dlg.v_expiry.set("1229"); dlg.v_cvv.set("123")
    pump()
    grab("11_payment_window")
    dlg.v_number.set("4000000000000002"); pump(); dlg.pay(); pump()
    grab("12_payment_declined")
    dlg.v_number.set("4111111111111111"); pump(); dlg.pay(); pump()
    grab("13_payment_success")
    booking, payment = dlg.result
    dlg.close(); pump()
    row = [i for i in bv.bookings.tree.get_children() if bv.bookings.tree.set(i, "pnr") == booking.pnr][0]
    bv.bookings.select(row); pump()
    shown.clear(); bv.cancel(); pump()
    d = dialog(next(s for s in shown if s[0] == "askyesno")); grab("14_passenger_cancel_refund"); d.destroy()

    # ---- CHECK-IN STAFF: unpaid booking is refused, paid booking checks in
    uid = conn.execute("SELECT user_id FROM users WHERE username='sneha'").fetchone()[0]
    fid = conn.execute("SELECT flight_id FROM flights WHERE flight_no='AI202'").fetchone()[0]
    conn.execute("INSERT INTO bookings (pnr, user_id, flight_id, seat, fare, status, booked_at)"
                 " VALUES ('UNPAD1', ?, ?, '15A', 5400, 'BOOKED', ?)", (uid, fid, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    login("staff1", "staff123")
    cv = tab("Check-in & Baggage")
    cv.pnr.set("UNPAD1"); cv.lookup(); pump()
    shown.clear(); cv.check_in(); pump()
    d = dialog(shown[-1]); grab("15_staff_unpaid_refused"); d.destroy()
    cv.pnr.set("K7Q2MA"); cv.lookup(); pump(); cv.check_in(); pump()
    for w in ("17.5", "4"):
        cv.weight.set(w); cv.add_bag(); pump()
    grab("16_staff_checkin_boarding_pass")
    cv.weight.set("40"); shown.clear(); cv.add_bag(); pump()
    d = dialog(shown[-1]); grab("17_staff_bag_weight_error"); d.destroy()

    # ---- PASSENGER: boarding pass tab
    login("priya", "pass1234")
    tab("Boarding Pass")
    grab("18_passenger_boarding_pass")

    # ---- the two PDFs, rendered to pictures
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print("pypdfium2 not installed: skipping the PDF pictures")
    else:
        user = app.ctx.user
        _name, data = app.ctx.checkin.boarding_pass_file(user, "K7Q2MA")
        pdfium.PdfDocument(data)[0].render(scale=2.0).to_pil().save(os.path.join(OUT, "19_boarding_pass_pdf.png"))
        pay = PaymentService(conn)
        bid = conn.execute("SELECT booking_id FROM bookings WHERE pnr='K7Q2MA'").fetchone()[0]
        _name, data = pay.receipt_file(user, bid)
        pdfium.PdfDocument(data)[0].render(scale=1.6).to_pil().save(os.path.join(OUT, "20_receipt_pdf.png"))
        print("saved 19_boarding_pass_pdf, 20_receipt_pdf")
    app.destroy()


if __name__ == "__main__":
    main()
