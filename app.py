from flask import Flask, render_template, request, redirect, send_file, session
import sqlite3
import pandas as pd
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "electrack_secret"

DATABASE = "database.db"


# ---------------- DATABASE CONNECTION ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- CREATE TABLES ----------------

def init_db():

    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # Employees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        rate REAL
    )
    """)

    # Projects
    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        client TEXT,
        budget REAL
    )
    """)

    # Time tracking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS time_entries(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        project_id INTEGER,
        hours REAL
    )
    """)

    # Expenses
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        description TEXT,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:
            session["user"] = user["username"]
            return redirect("/")
        else:
            return "Invalid login"

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------------- DASHBOARD ----------------

@app.route("/")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    projects = cur.execute("SELECT * FROM projects").fetchall()

    data = []

    total_budget = 0
    total_cost = 0

    for p in projects:

        pid = p["id"]

        emp_cost = cur.execute("""
        SELECT SUM(hours * rate)
        FROM time_entries
        JOIN employees
        ON employees.id = time_entries.employee_id
        WHERE project_id=?
        """, (pid,)).fetchone()[0] or 0

        expenses = cur.execute("""
        SELECT SUM(amount)
        FROM expenses
        WHERE project_id=?
        """, (pid,)).fetchone()[0] or 0

        cost = emp_cost + expenses
        profit = p["budget"] - cost

        margin = 0
        if p["budget"] > 0:
            margin = (profit / p["budget"]) * 100

        total_budget += p["budget"]
        total_cost += cost

        data.append({
            "id": pid,
            "name": p["name"],
            "client": p["client"],
            "budget": p["budget"],
            "cost": cost,
            "profit": profit,
            "margin": round(margin, 2)
        })

    conn.close()

    total_profit = total_budget - total_cost

    return render_template(
        "dashboard.html",
        projects=data,
        total_budget=total_budget,
        total_cost=total_cost,
        total_profit=total_profit
    )


# ---------------- PROJECTS ----------------

@app.route("/projects")
def projects():

    conn = get_db()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()

    return render_template("projects.html", projects=projects)


@app.route("/add_project", methods=["POST"])
def add_project():

    name = request.form["name"]
    client = request.form["client"]
    budget = request.form["budget"]

    conn = get_db()

    conn.execute(
        "INSERT INTO projects(name,client,budget) VALUES(?,?,?)",
        (name, client, budget)
    )

    conn.commit()
    conn.close()

    return redirect("/projects")


# ---------------- EMPLOYEES ----------------

@app.route("/employees")
def employees():

    conn = get_db()
    employees = conn.execute("SELECT * FROM employees").fetchall()
    conn.close()

    return render_template("employees.html", employees=employees)


@app.route("/add_employee", methods=["POST"])
def add_employee():

    name = request.form["name"]
    role = request.form["role"]
    rate = request.form["rate"]

    conn = get_db()

    conn.execute(
        "INSERT INTO employees(name,role,rate) VALUES(?,?,?)",
        (name, role, rate)
    )

    conn.commit()
    conn.close()

    return redirect("/employees")


# ---------------- TIME TRACKING ----------------

@app.route("/time", methods=["GET", "POST"])
def time():

    conn = get_db()

    employees = conn.execute("SELECT * FROM employees").fetchall()
    projects = conn.execute("SELECT * FROM projects").fetchall()

    if request.method == "POST":

        employee = request.form["employee"]
        project = request.form["project"]
        hours = request.form["hours"]

        conn.execute(
            "INSERT INTO time_entries(employee_id,project_id,hours) VALUES(?,?,?)",
            (employee, project, hours)
        )

        conn.commit()

    conn.close()

    return render_template("time.html", employees=employees, projects=projects)


# ---------------- EXPENSES ----------------

@app.route("/expenses", methods=["GET", "POST"])
def expenses():

    conn = get_db()

    projects = conn.execute("SELECT * FROM projects").fetchall()

    if request.method == "POST":

        project = request.form["project"]
        desc = request.form["description"]
        amount = request.form["amount"]

        conn.execute(
            "INSERT INTO expenses(project_id,description,amount) VALUES(?,?,?)",
            (project, desc, amount)
        )

        conn.commit()

    conn.close()

    return render_template("expenses.html", projects=projects)


# ---------------- EXCEL EXPORT ----------------

@app.route("/export")
def export_excel():

    conn = get_db()

    df = pd.read_sql_query("SELECT * FROM projects", conn)

    file = "projects_report.xlsx"

    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)


# ---------------- INVOICE PDF ----------------

@app.route("/invoice/<int:project_id>")
def invoice(project_id):

    file = "invoice.pdf"

    c = canvas.Canvas(file)

    c.drawString(100, 750, "Electrical Consultancy Invoice")

    c.drawString(100, 700, f"Project ID: {project_id}")

    c.drawString(100, 650, "Generated by ElecTrack System")

    c.save()

    return send_file(file, as_attachment=True)


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)