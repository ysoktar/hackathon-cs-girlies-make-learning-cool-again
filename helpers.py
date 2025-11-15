from cs50 import SQL
from flask import redirect, session
from functools import wraps

db = SQL("sqlite:///users.db")

levels = ['a1', 'a2', 'b1', 'b2', 'c1', 'c2']

def login_required(f):
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function


def is_admin():
    user = db.execute("SELECT role FROM users WHERE id = ?", session.get("user_id"))
    return user and user[0]["role"] == "admin"