"""Module 4 GUI - Admin user management: list accounts and create staff/admin accounts."""
from tkinter import messagebox, ttk

from ..models import Role
from .widgets import Button, DataTable, FormPanel, run_action

COLUMNS = [("username", "Username", 110), ("role", "Role", 90), ("name", "Full name", 160),
           ("email", "E-mail", 200), ("phone", "Phone", 110)]
FIELDS = [("username", "Username", "entry", ()), ("full_name", "Full name", "entry", ()),
          ("password", "Password", "password", ()), ("role", "Role", "combo", ("STAFF", "ADMIN")),
          ("email", "E-mail", "entry", ()), ("phone", "Mobile number", "entry", ())]


class UsersView(ttk.Frame):
    def __init__(self, parent, ctx):
        super().__init__(parent, padding=12)
        self.ctx = ctx
        ttk.Label(self, text="User accounts", style="Heading.TLabel", font="AMSHeading").pack(anchor="w")
        box = ttk.LabelFrame(self, text="Create staff / admin account", padding=10)
        box.pack(side="bottom", fill="x")
        self.table = DataTable(self, COLUMNS, height=4, empty_text="No users.")
        self.table.pack(fill="both", expand=True, pady=8)
        self.form = FormPanel(box, FIELDS, columns=2, entry_width=26)
        self.form.pack(anchor="w")
        self.form.set({"role": "STAFF"})
        Button(box, text="Create account", style="Accent.TButton", command=self.create).pack(anchor="e", pady=(8, 0))
        self.refresh()

    def on_show(self):
        self.refresh()

    def refresh(self):
        self.table.load([(u.user_id, (u.username, u.role.value, u.full_name, u.email, u.phone), "")
                         for u in self.ctx.auth.list_users(self.ctx.user)])

    def create(self):
        d = self.form.get()
        run_action(self, lambda: self.ctx.auth.create_staff_account(
            self.ctx.user, d["username"], d["password"], d["full_name"], d["email"], d["phone"],
            Role(d["role"] or "STAFF"), now=self.ctx.now()),
            lambda u: (self.refresh(), self.form.clear(), self.form.set({"role": "STAFF"}),
                       messagebox.showinfo("Created", f"{u.role.value} account '{u.username}' created.", parent=self)))
