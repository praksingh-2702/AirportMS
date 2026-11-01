"""Payment window (SIMULATED gateway): fare breakdown, Card / UPI / Net banking, processing animation and an
animated "payment successful" screen with a receipt download. No real money moves."""
import math
import re
import tkinter as tk
from tkinter import ttk
from typing import Callable, Tuple

from ..config import BANKS
from ..errors import AMSError
from ..models import FareBreakdown
from .widgets import (COLORS, Button, animate, center_on, ease_in_out, fade_in, linear, mix, run_action,
                      save_file)

METHODS = (("CARD", "Card"), ("UPI", "UPI"), ("NETBANKING", "Net banking"))


def rs(amount: int) -> str:
    return f"Rs {amount:,}"


class PaymentDialog(tk.Toplevel):
    PROCESSING_MS = 1100            # how long the "processing" animation runs (tests set this to 0)

    def __init__(self, parent, ctx, summary: Tuple[str, str], breakdown: FareBreakdown,
                 submit: Callable[[str, dict], tuple], on_done: Callable = None):
        """submit(method, details) must return (booking, payment) or raise; on_done(result) runs after success."""
        super().__init__(parent)
        self.ctx, self.submit, self.on_done, self.breakdown = ctx, submit, on_done, breakdown
        self.method = "CARD"
        self.busy = False
        self.result = None
        self.title("Secure payment (demo)")
        self.configure(bg=COLORS["card"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())

        head = tk.Frame(self, bg=COLORS["header"], padx=22, pady=14)
        head.pack(fill="x")
        tk.Label(head, text="Secure payment", font="AMSHeading", bg=COLORS["header"], fg="white").pack(anchor="w")
        tk.Label(head, text="DEMO MODE - no real money is charged", font="AMSSmall", bg=COLORS["header"],
                 fg=COLORS["gold"]).pack(anchor="w")

        self.body = tk.Frame(self, bg=COLORS["card"], padx=22, pady=14)
        self.body.pack(fill="both", expand=True)
        self._build_form(summary)
        self.transient(parent.winfo_toplevel())
        center_on(self, parent)
        self.grab_set()
        fade_in(self, 200)

    # ------------------------------------------------------------------ payment form
    def _build_form(self, summary):
        body = self.body
        tk.Label(body, text=summary[0], font="AMSHeading", bg=COLORS["card"]).pack(anchor="w")
        tk.Label(body, text=summary[1], bg=COLORS["card"], fg=COLORS["muted"]).pack(anchor="w", pady=(0, 8))

        table = tk.Frame(body, bg=COLORS["bg"], padx=14, pady=8)
        table.pack(fill="x")
        b = self.breakdown
        rows = (("Base fare", b.base_fare), ("Airport user fee", b.airport_fee), ("GST (5%)", b.gst),
                ("Convenience fee", b.convenience_fee))
        for i, (label, amount) in enumerate(rows):
            tk.Label(table, text=label, bg=COLORS["bg"], fg=COLORS["muted"]).grid(row=i, column=0, sticky="w")
            tk.Label(table, text=rs(amount), bg=COLORS["bg"]).grid(row=i, column=1, sticky="e")
        tk.Frame(table, bg=COLORS["border"], height=1).grid(row=len(rows), column=0, columnspan=2, sticky="we", pady=4)
        tk.Label(table, text="Total to pay", font="AMSBold", bg=COLORS["bg"]).grid(row=len(rows) + 1, column=0, sticky="w")
        self.total_label = tk.Label(table, text=rs(b.total), font="AMSHeading", bg=COLORS["bg"], fg=COLORS["accent"])
        self.total_label.grid(row=len(rows) + 1, column=1, sticky="e")
        table.columnconfigure(0, weight=1)
        table.columnconfigure(1, weight=1)

        # method selector (segmented control)
        seg = tk.Frame(body, bg=COLORS["border"], padx=1, pady=1)
        seg.pack(fill="x", pady=(14, 8))
        self.tabs = {}
        for i, (value, text) in enumerate(METHODS):
            lab = tk.Label(seg, text=text, font="AMSBold", pady=7, cursor="hand2", bg="#FFFFFF", fg=COLORS["text"])
            lab.grid(row=0, column=i, sticky="we", padx=(0 if i == 0 else 1, 0))
            lab.bind("<Button-1>", lambda _e, m=value: self._select(m))
            lab.bind("<Enter>", lambda _e, m=value: self._tab_hover(m, True))
            lab.bind("<Leave>", lambda _e, m=value: self._tab_hover(m, False))
            seg.columnconfigure(i, weight=1, uniform="seg")
            self.tabs[value] = lab

        self.v_number, self.v_name, self.v_expiry, self.v_cvv = (tk.StringVar() for _ in range(4))
        self.v_upi, self.v_bank = tk.StringVar(), tk.StringVar()
        # Reformat after the write has finished: changing the variable from inside its own write callback
        # leaves the entry box showing the stale text.
        self.v_number.trace_add("write", lambda *_a: self.after_idle(self._reformat, self.v_number, self._fmt_number))
        self.v_expiry.trace_add("write", lambda *_a: self.after_idle(self._reformat, self.v_expiry, self._fmt_expiry))

        self.forms = {}
        card = tk.Frame(body, bg=COLORS["card"])
        self._field(card, "Card number", self.v_number, 0, 0, colspan=2, width=30)
        self._field(card, "Name on card", self.v_name, 1, 0, colspan=2, width=30)
        self._field(card, "Expiry (MM/YY)", self.v_expiry, 2, 0, width=12)
        self._field(card, "CVV", self.v_cvv, 2, 1, width=8, show="*")
        self.forms["CARD"] = card
        upi = tk.Frame(body, bg=COLORS["card"])
        self._field(upi, "UPI ID", self.v_upi, 0, 0, colspan=2, width=30)
        self.forms["UPI"] = upi
        net = tk.Frame(body, bg=COLORS["card"])
        tk.Label(net, text="Your bank", bg=COLORS["card"], fg=COLORS["muted"], font="AMSSmall").grid(row=0, column=0, sticky="w")
        ttk.Combobox(net, textvariable=self.v_bank, values=BANKS, state="readonly", width=32).grid(row=1, column=0, sticky="we", pady=(2, 6))
        self.forms["NETBANKING"] = net

        self.hint = tk.Label(body, bg=COLORS["card"], fg=COLORS["muted"], font="AMSSmall", justify="left", wraplength=420)
        self.hint.pack(anchor="w", pady=(2, 0))
        self.error = tk.Label(body, text="", bg=COLORS["card"], fg=COLORS["danger"], font="AMSBold", justify="left", wraplength=420)
        self.error.pack(anchor="w", pady=(6, 0))
        self.progress = ttk.Progressbar(body, mode="indeterminate", length=420)

        self.buttons = tk.Frame(body, bg=COLORS["card"])
        self.buttons.pack(fill="x", pady=(10, 0))
        self.pay_btn = Button(self.buttons, text=f"Pay {rs(b.total)}", style="Accent.TButton", command=self.pay)
        self.pay_btn.pack(side="right")
        self.cancel_btn = Button(self.buttons, text="Cancel", command=self.close)
        self.cancel_btn.pack(side="right", padx=8)
        self._select("CARD", animate_it=False)

    def _field(self, parent, label, var, row, col, colspan=1, width=20, show=""):
        cell = tk.Frame(parent, bg=COLORS["card"])
        cell.grid(row=row, column=col, columnspan=colspan, sticky="we", padx=(0 if col == 0 else 14, 0), pady=(0, 6))
        tk.Label(cell, text=label, bg=COLORS["card"], fg=COLORS["muted"], font="AMSSmall").pack(anchor="w")
        entry = ttk.Entry(cell, textvariable=var, width=width, show=show)
        entry.pack(anchor="w", fill="x", pady=(2, 0))
        entry.bind("<Return>", lambda _e: self.pay())
        return entry

    # ------------------------------------------------------------------ small behaviours
    @staticmethod
    def _fmt_number(text: str) -> str:
        raw = re.sub(r"\D", "", text)[:19]
        return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))

    @staticmethod
    def _fmt_expiry(text: str) -> str:
        digits = re.sub(r"\D", "", text)[:4]
        return f"{digits[:2]}/{digits[2:]}" if len(digits) > 2 else digits

    def _reformat(self, var: tk.StringVar, fmt: Callable[[str], str]):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        new = fmt(var.get())
        if new != var.get():
            var.set(new)

    def _tab_hover(self, method, inside):
        if method != self.method:
            self.tabs[method].configure(bg=COLORS["accent_soft"] if inside else "#FFFFFF")

    def _select(self, method: str, animate_it: bool = True):
        self.method = method
        for value, lab in self.tabs.items():
            active = value == method
            target_bg, target_fg = (COLORS["accent"], "#FFFFFF") if active else ("#FFFFFF", COLORS["text"])
            start = lab.cget("bg")
            if animate_it:
                animate(lab, 180, lambda t, l=lab, s=start, tb=target_bg: l.configure(bg=mix(s, tb, t)), key="bg")
            else:
                lab.configure(bg=target_bg)
            lab.configure(fg=target_fg)
        for value, frame in self.forms.items():
            frame.pack_forget()
        self.forms[method].pack(fill="x", before=self.hint)
        self.hint.configure(text={
            "CARD": "Demo cards: 4111 1111 1111 1111 is approved, 4000 0000 0000 0002 is declined, "
                    "4000 0000 0000 9995 has no funds. Any future expiry and a 3-digit CVV.",
            "UPI": "Demo: any ID like name@okaxis is approved; an ID containing \"fail\" is rejected.",
            "NETBANKING": "Demo: every bank approves except \"Demo Bank (offline)\"."}[method])
        self.error.configure(text="")

    def details(self) -> dict:
        if self.method == "CARD":
            return dict(number=self.v_number.get(), expiry=self.v_expiry.get(), cvv=self.v_cvv.get(),
                        name=self.v_name.get())
        if self.method == "UPI":
            return dict(upi_id=self.v_upi.get())
        return dict(bank=self.v_bank.get())

    # ------------------------------------------------------------------ paying
    def pay(self):
        if self.busy or self.result is not None:
            return
        self.busy = True
        self.error.configure(text="")
        self.pay_btn.configure(state="disabled", text="Processing...")
        self.cancel_btn.configure(state="disabled")
        if self.PROCESSING_MS > 0:
            self.progress.pack(anchor="w", pady=(8, 0), before=self.buttons)
            self.progress.start(12)
            self.after(self.PROCESSING_MS, self._finish)
        else:
            self._finish()

    def _finish(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        self.progress.stop()
        self.progress.pack_forget()
        self.busy = False
        try:
            result = self.submit(self.method, self.details())
        except Exception as exc:   # noqa: BLE001 - every failure must reach the user
            self.pay_btn.configure(state="normal", text=f"Pay {rs(self.breakdown.total)}")
            self.cancel_btn.configure(state="normal")
            self.error.configure(text=str(exc) if isinstance(exc, AMSError) else f"Unexpected error: {exc}")
            self._shake()
            return
        self.result = result
        if self.on_done:
            self.on_done(result)
        self._show_success(result)

    def _shake(self):
        x, y = self.winfo_x(), self.winfo_y()
        animate(self, 380, lambda t: self.geometry(f"+{int(x + math.sin(t * math.pi * 7) * (1 - t) * 9)}+{y}"),
                ease=linear, key="shake")

    def close(self):
        if self.busy:
            return
        try:
            self.grab_release()
            self.destroy()
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ success screen
    def _show_success(self, result):
        booking, payment = result
        for child in self.body.winfo_children():
            child.destroy()
        box = tk.Frame(self.body, bg=COLORS["card"], padx=40, pady=10)
        box.pack()
        canvas = tk.Canvas(box, width=104, height=104, bg=COLORS["card"], highlightthickness=0)
        canvas.pack(pady=(4, 6))
        ring = canvas.create_arc(10, 10, 94, 94, start=90, extent=0, style="arc", outline=COLORS["ok"], width=6)
        tick = canvas.create_line(30, 54, 30, 54, fill=COLORS["ok"], width=7, capstyle="round", joinstyle="round",
                                  state="hidden")

        def draw_ring(t):
            canvas.itemconfigure(ring, extent=-359.9 * t)

        def draw_tick(t):
            canvas.itemconfigure(tick, state="normal")
            p1, p2, p3 = (30, 54), (46, 70), (76, 36)
            if t < 0.45:
                k = t / 0.45
                canvas.coords(tick, *p1, p1[0] + (p2[0] - p1[0]) * k, p1[1] + (p2[1] - p1[1]) * k)
            else:
                k = (t - 0.45) / 0.55
                canvas.coords(tick, *p1, *p2, p2[0] + (p3[0] - p2[0]) * k, p2[1] + (p3[1] - p2[1]) * k)

        animate(canvas, 520, draw_ring, done=lambda: animate(canvas, 320, draw_tick, key="tick"), ease=ease_in_out, key="ring")
        tk.Label(box, text="Payment successful", font="AMSTitle", bg=COLORS["card"], fg=COLORS["ok"]).pack()
        tk.Label(box, text=f"{rs(payment.amount)} paid by {payment.instrument}", bg=COLORS["card"]).pack(pady=(4, 0))
        tk.Label(box, text=f"PNR {booking.pnr}   |   Seat {booking.seat}", font="AMSHeading", bg=COLORS["card"]).pack(pady=(10, 0))
        tk.Label(box, text=f"Invoice {payment.invoice_no}   |   Ref {payment.reference}", bg=COLORS["card"],
                 fg=COLORS["muted"], font="AMSSmall").pack(pady=(2, 12))
        row = tk.Frame(box, bg=COLORS["card"])
        row.pack(fill="x")
        Button(row, text="Download receipt (PDF)", style="Accent.TButton", command=self.download_receipt).pack(side="left")
        Button(row, text="Done", command=self.close).pack(side="right")
        self.update_idletasks()
        center_on(self, self.master)

    def download_receipt(self):
        booking, _payment = self.result
        run_action(self, lambda: self.ctx.payments.receipt_file(self.ctx.user, booking.booking_id),
                   lambda f: save_file(self, f[1], f[0], "Save receipt"))
