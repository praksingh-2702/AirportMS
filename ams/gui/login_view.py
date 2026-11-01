"""Animated login screen (sky, planes, runway lights) and the passenger registration dialog."""
import math
import random
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .widgets import (COLORS, Button, FormPanel, animate, center_on, draw_plane, ease_out, fade_in, linear, mix,
                      run_action, show_error)

SKY_TOP, SKY_MID, SKY_BOTTOM = "#06142B", "#164A8A", "#6FB1E6"


class LoginView(tk.Canvas):
    def __init__(self, parent, ctx, on_login: Callable):
        super().__init__(parent, highlightthickness=0, bg=SKY_TOP)
        self.ctx, self.on_login = ctx, on_login
        self._sw = self._sh = 0
        self._cx = self._cy = 0
        self._card_t = 0.0           # 0 -> card below its resting place, 1 -> in place
        self._frame = 0
        self._rng = random.Random(7)
        self.stars, self.clouds, self.planes, self.lights = [], [], [], []

        card = ttk.Frame(self, style="Card.TFrame", padding=(34, 26))
        self.card_win = self.create_window(0, 0, window=card, anchor="center")
        self._build_card(card)
        self.bind("<Configure>", self._on_resize)
        animate(self, 650, self._slide_card, key="card")
        self.after(33, self._tick)

    # ----- card -----
    def _build_card(self, card):
        logo = tk.Canvas(card, width=64, height=64, bg="white", highlightthickness=0)
        logo.create_oval(2, 2, 62, 62, fill=COLORS["accent"], outline="")
        draw_plane(logo, 32, 32, 0.9, "white", "logo")
        logo.grid(row=0, column=0, columnspan=2, pady=(0, 8))
        ttk.Label(card, text="Airport Management System", style="Title.TLabel", font="AMSTitle",
                  background="white").grid(row=1, column=0, columnspan=2)
        ttk.Label(card, text="Sign in to continue", style="Card.TLabel",
                  foreground=COLORS["muted"]).grid(row=2, column=0, columnspan=2, pady=(2, 16))

        self.username, self.password = tk.StringVar(), tk.StringVar()
        ttk.Label(card, text="Username", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        self.user_entry = ttk.Entry(card, textvariable=self.username, width=30)
        self.user_entry.grid(row=3, column=1, pady=6, padx=(10, 0))
        ttk.Label(card, text="Password", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=6)
        self.pass_entry = ttk.Entry(card, textvariable=self.password, width=30, show="*")
        self.pass_entry.grid(row=4, column=1, pady=6, padx=(10, 0))
        self.show_pw = tk.BooleanVar(value=False)
        ttk.Checkbutton(card, text="Show password", variable=self.show_pw, style="Card.TCheckbutton",
                        command=lambda: self.pass_entry.configure(show="" if self.show_pw.get() else "*")
                        ).grid(row=5, column=1, sticky="w", padx=(10, 0))
        for entry in (self.user_entry, self.pass_entry):
            entry.bind("<Return>", lambda _e: self.login())

        Button(card, text="Login", style="Accent.TButton", command=self.login).grid(
            row=6, column=0, columnspan=2, sticky="we", pady=(14, 6))
        Button(card, text="New passenger? Register", command=self.open_register).grid(
            row=7, column=0, columnspan=2, sticky="we")
        ttk.Label(card, text="Quick fill demo account", style="Card.TLabel", foreground=COLORS["muted"],
                  font="AMSSmall").grid(row=8, column=0, columnspan=2, pady=(16, 4))
        chips = ttk.Frame(card, style="Card.TFrame")
        chips.grid(row=9, column=0, columnspan=2)
        for label, user, pw in (("Admin", "admin", "admin123"), ("Staff", "staff1", "staff123"),
                                ("Passenger", "priya", "pass1234")):
            Button(chips, text=label, command=lambda u=user, p=pw: self.fill(u, p)).pack(side="left", padx=4)
        self.user_entry.focus_set()

    def fill(self, user, pw):
        self.username.set(user)
        self.password.set(pw)
        self.pass_entry.focus_set()

    # ----- scene -----
    def _on_resize(self, e):
        if e.width < 50 or e.height < 50:
            return
        self._sw, self._sh = e.width, e.height
        self._draw_scene()
        self._place_card()

    def _draw_scene(self):
        w, h, rng = self._sw, self._sh, self._rng
        self.delete("scene")
        bands = 70
        for i in range(bands):
            t = i / (bands - 1)
            color = mix(SKY_TOP, SKY_MID, t / 0.6) if t < 0.6 else mix(SKY_MID, SKY_BOTTOM, (t - 0.6) / 0.4)
            self.create_rectangle(0, h * i / bands, w, h * (i + 1) / bands + 1, fill=color, outline="", tags="scene")
        self.stars = [self.create_oval(x, y, x + s, y + s, fill="#FFFFFF", outline="", tags="scene")
                      for x, y, s in ((rng.uniform(0, w), rng.uniform(0, h * 0.55), rng.choice((1.5, 2, 2.5)))
                                      for _ in range(80))]
        self.clouds = []
        for i in range(6):
            x, y, sc = rng.uniform(0, w), rng.uniform(h * 0.12, h * 0.62), rng.uniform(0.7, 1.5)
            tag = f"cloud{i}"
            shade = mix(SKY_MID, "#FFFFFF", rng.uniform(0.22, 0.4))
            for dx, dy, rx, ry in ((0, 0, 60, 20), (-38, 6, 38, 15), (40, 5, 44, 16), (6, -12, 34, 18)):
                self.create_oval(x + (dx - rx) * sc, y + (dy - ry) * sc, x + (dx + rx) * sc, y + (dy + ry) * sc,
                                 fill=shade, outline="", tags=("scene", tag))
            self.clouds.append((tag, rng.uniform(0.15, 0.5)))
        self.planes = []
        for y_frac, scale, speed, x in ((0.2, 1.1, 2.6, w * 0.15), (0.42, 0.7, 1.5, w * 0.7)):
            tag = f"plane{len(self.planes)}"
            y = h * y_frac
            for k in range(6):   # fading contrail made of shrinking dashes
                self.create_line(x - 40 * scale - k * 34 * scale, y, x - 40 * scale - k * 34 * scale - 22 * scale, y,
                                 fill=mix("#FFFFFF", mix(SKY_MID, SKY_TOP, 0.5), k / 6), width=2.2 * scale,
                                 tags=("scene", tag))
            draw_plane(self, x, y, scale, "#FFFFFF", ("scene", tag))
            self.planes.append((tag, speed, y))
        # runway
        top = h - 56
        self.create_rectangle(0, top, w, h, fill="#0A1426", outline="", tags="scene")
        for x in range(0, int(w), 90):
            self.create_rectangle(x, top + 34, x + 46, top + 38, fill="#D9E2EF", outline="", tags="scene")
        self.lights = [self.create_oval(x - 4, top + 10, x + 4, top + 18, fill="#5B4A1E", outline="", tags="scene")
                       for x in range(20, int(w), 40)]
        self.tag_lower("scene")

    def _place_card(self):
        self._cx, self._cy = self._sw / 2, self._sh * 0.46
        self._slide_card(self._card_t)

    def _slide_card(self, t):
        self._card_t = t
        self.coords(self.card_win, self._cx, self._cy + (1 - t) * 70)

    def _tick(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        self._frame += 1
        w = self._sw or 1
        for tag, speed in self.clouds:
            self.move(tag, speed, 0)
            x0, _y0, _x1, _y1 = self.bbox(tag)
            if x0 > w + 20:
                self.move(tag, -(w + 360), 0)
        for tag, speed, _y in self.planes:
            self.move(tag, speed, math.sin(self._frame / 30) * 0.15)
            x0, _y0, _x1, _y1 = self.bbox(tag)
            if x0 > w + 20:
                self.move(tag, -(w + 520), 0)
        if self.stars and self._frame % 3 == 0:
            for item in self._rng.sample(self.stars, min(4, len(self.stars))):
                self.itemconfigure(item, fill=self._rng.choice(("#FFFFFF", "#9DB7DC", "#5C7AA8")))
        if self.lights and self._frame % 3 == 0:
            lit = (self._frame // 3) % len(self.lights)
            for i, item in enumerate(self.lights):
                d = (lit - i) % len(self.lights)
                self.itemconfigure(item, fill=mix(COLORS["gold"], "#5B4A1E", min(d / 5, 1)))
        self.after(33, self._tick)

    def shake(self):
        def step(t):
            self.coords(self.card_win, self._cx + math.sin(t * math.pi * 7) * (1 - t) * 14, self._cy)
        animate(self, 420, step, ease=linear, key="shake")

    # ----- actions -----
    def login(self):
        if not self.winfo_exists() or not self.winfo_ismapped():
            return
        try:
            user = self.ctx.auth.login(self.username.get(), self.password.get())
        except Exception as exc:   # noqa: BLE001
            self.shake()
            show_error(self, exc)
            return
        self._success(user)

    def _success(self, user):
        self.password.set("")
        self.on_login(user)

    def open_register(self):
        RegisterDialog(self, self.ctx, on_done=lambda u: self.username.set(u.username))


class RegisterDialog(tk.Toplevel):
    FIELDS = [("username", "Username", "entry", ()), ("full_name", "Full name", "entry", ()),
              ("password", "Password", "password", ()), ("confirm", "Confirm password", "password", ()),
              ("email", "E-mail", "entry", ()), ("phone", "Mobile number", "entry", ())]

    def __init__(self, parent, ctx, on_done: Callable):
        super().__init__(parent)
        self.ctx, self.on_done = ctx, on_done
        self.title("Passenger Registration")
        self.configure(padx=24, pady=18, bg=COLORS["bg"])
        self.resizable(False, False)
        ttk.Label(self, text="Create a passenger account", style="Heading.TLabel", font="AMSHeading").pack(anchor="w", pady=(0, 10))
        self.form = FormPanel(self, self.FIELDS, columns=1, entry_width=32)
        self.form.pack()
        ttk.Label(self, text="Password: 6-64 chars with a letter and a digit. Phone: 10 digits.",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(14, 0))
        Button(row, text="Register", style="Accent.TButton", command=self.submit).pack(side="right")
        Button(row, text="Cancel", command=self.destroy).pack(side="right", padx=8)
        self.bind("<Return>", lambda _e: self.submit())     # Enter registers (does not touch the login form)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.transient(parent.winfo_toplevel())
        center_on(self, parent)
        self.grab_set()
        self.form.widgets["username"].focus_set()
        fade_in(self, 220)

    def submit(self):
        d = self.form.get()
        if d["password"] != d["confirm"]:
            messagebox.showerror("Cannot complete action", "Passwords do not match.", parent=self)
            return
        run_action(self, lambda: self.ctx.auth.register_passenger(
            d["username"], d["password"], d["full_name"], d["email"], d["phone"], now=self.ctx.now()),
            self._done)

    def _done(self, user):
        messagebox.showinfo("Registered", f"Account '{user.username}' created. You can now log in.", parent=self)
        self.on_done(user)
        self.destroy()
