from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import pandas as pd

app = Flask(__name__)

DATABASE = "database.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- INIT DATABASE --------------------

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        hourly_rate REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        client TEXT,
        budget REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS time_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        project_id INTEGER,
        hours REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        description TEXT,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------- DASHBOARD --------------------

@app.route("/")
def dashboard():
    conn = get_db()
    cur = conn.cursor()

    projects = cur.execute("SELECT * FROM projects").fetchall()
    project_data = []

    for project in projects:
        pid = project["id"]

        emp_cost = cur.execute("""
            SELECT SUM(t.hours * e.hourly_rate)
            FROM time_entries t
            JOIN employees e ON t.employee_id = e.id
            WHERE t.project_id = ?
        """, (pid,)).fetchone()[0] or 0

        expenses = cur.execute("""
            SELECT SUM(amount) FROM expenses
            WHERE project_id = ?
        """, (pid,)).fetchone()[0] or 0

        total_cost = emp_cost + expenses
        profit = project["budget"] - total_cost

        margin = 0
        if project["budget"] > 0:
            margin = (profit / project["budget"]) * 100

        project_data.append({
            "name": project["name"],
            "client": project["client"],
            "budget": project["budget"],
            "employee_cost": emp_cost,
            "expenses": expenses,
            "total_cost": total_cost,
            "profit": profit,
            "margin": round(margin, 2)
        })

    conn.close()
    return render_template("dashboard.html", projects=project_data)

# -------------------- EXCEL EXPORT --------------------

@app.route("/export")
def export_excel():
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT p.name, p.client, p.budget,
        IFNULL(SUM(t.hours * e.hourly_rate),0) AS employee_cost
        FROM projects p
        LEFT JOIN time_entries t ON p.id = t.project_id
        LEFT JOIN employees e ON t.employee_id = e.id
        GROUP BY p.id
    """, conn)

    file = "project_report.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

# -------------------- RUN --------------------

if __name__ == "__main__":
    app.run(debug=True)