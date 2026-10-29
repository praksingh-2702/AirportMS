"""Login screen and passenger self-registration dialog."""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .widgets import FormPanel, run_action


class LoginView(ttk.Frame):
    def __init__(self, parent, ctx, on_login: Callable):
        super().__init__(parent)
        self.ctx, self.on_login = ctx, on_login
        card = ttk.Frame(self, style="Card.TFrame", padding=32)
        card.place(relx=0.5, rely=0.45, anchor="center")

        ttk.Label(card, text="Airport Management System", style="Title.TLabel",
                  background="white").grid(row=0, column=0, columnspan=2, pady=(0, 4))
        ttk.Label(card, text="Sign in to continue", style="Card.TLabel",
                  foreground="#5B6675").grid(row=1, column=0, columnspan=2, pady=(0, 18))

        self.username, self.password = tk.StringVar(), tk.StringVar()
        ttk.Label(card, text="Username", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        self.user_entry = ttk.Entry(card, textvariable=self.username, width=30)
        self.user_entry.grid(row=2, column=1, pady=6)
        ttk.Label(card, text="Password", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(card, textvariable=self.password, width=30, show="*").grid(row=3, column=1, pady=6)

        ttk.Button(card, text="Login", style="Accent.TButton", command=self.login).grid(
            row=4, column=0, columnspan=2, sticky="we", pady=(16, 6))
        ttk.Button(card, text="New passenger? Register", command=self.open_register).grid(
            row=5, column=0, columnspan=2, sticky="we")
        ttk.Label(card, text="Demo accounts: admin/admin123 · staff1/staff123 · priya/pass1234",
                  style="Card.TLabel", foreground="#5B6675").grid(row=6, column=0, columnspan=2, pady=(18, 0))
        self.bind_all("<Return>", lambda _e: self.login())
        self.user_entry.focus_set()

    def login(self):
        if not self.winfo_exists() or not self.winfo_ismapped():
            return
        run_action(self, lambda: self.ctx.auth.login(self.username.get(), self.password.get()),
                   self._success)

    def _success(self, user):
        self.unbind_all("<Return>")
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
        self.configure(padx=20, pady=16)
        self.resizable(False, False)
        ttk.Label(self, text="Create a passenger account", style="Heading.TLabel").pack(anchor="w", pady=(0, 10))
        self.form = FormPanel(self, self.FIELDS, columns=1, entry_width=32)
        self.form.pack()
        ttk.Label(self, text="Password: 6-64 chars with a letter and a digit. Phone: 10 digits.",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(12, 0))
        ttk.Button(row, text="Register", style="Accent.TButton", command=self.submit).pack(side="right")
        ttk.Button(row, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

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
