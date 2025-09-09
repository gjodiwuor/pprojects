#app.py - complete backend (Flask + pyodbc)
from flask import Flask, request, jsonify
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta

app = Flask(__name__)

# ---------- DATABASE CONNECTION ----------
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-15VGM3T\\SQLEXPRESS;"
    "DATABASE=ExpenseTracker;"
    "Trusted_Connection=yes;"
)

def get_db_connection():
    return pyodbc.connect(CONN_STR)

# ---------- HELPERS ----------
#Used to parse date strings and apply date filters in SQL queries
def parse_date(s):
    """Parse YYYY-MM-DD to date object, return None on failure/empty."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def apply_date_filter_sql(base_query, params, filter_type, from_str, to_str):
    """
    Mutates base_query string and params list to add a date filter.
    filter_type: 'all'|'daily'|'weekly'|'monthly'
    from_str/to_str: YYYY-MM-DD (strings) - explicit range overrides filter_type
    Returns (query, params)
    """
    # explicit range if provided
    from_date = parse_date(from_str)
    to_date = parse_date(to_str)
    today = date.today()

    if from_date and to_date:
        base_query += " AND date BETWEEN ? AND ?"
        params.extend([from_date, to_date])
        return base_query, params

    if filter_type == "daily":
        base_query += " AND date = ?"
        params.append(today)
    elif filter_type == "weekly":
        # Monday as start of the week
        start_of_week = today - timedelta(days=today.weekday())
        base_query += " AND date BETWEEN ? AND ?"
        params.extend([start_of_week, today])
    elif filter_type == "monthly":
        start_of_month = today.replace(day=1)
        base_query += " AND date BETWEEN ? AND ?"
        params.extend([start_of_month, today])
    # else 'all' - no addition
    return base_query, params

# ---------- ROOT ----------
# Basic health check
@app.route("/")
def root():
    return "Expense Tracker backend running."

# ---------- AUTH ----------
# User registration and login
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "username, email and password are required"}), 400

    hashed = generate_password_hash(password)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed)
        )
        conn.commit()
        return jsonify({"message": "User registered"}), 201
    except Exception as e:
        # common error: UNIQUE constraint on username/email
        return jsonify({"error": str(e)}), 400
    finally:
        if conn:
            conn.close()

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, password FROM Users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Invalid username or password"}), 401
        stored_hash = row[1]
        if check_password_hash(stored_hash, password):
            return jsonify({"message": "Login successful", "user_id": int(row[0])}), 200
        return jsonify({"error": "Invalid username or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ---------- CATEGORIES ----------
# Get all categories
@app.route("/categories", methods=["GET"])
def categories():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_id, category_name FROM Categories")
        rows = cursor.fetchall()
        out = [{"id": int(r[0]), "name": r[1]} for r in rows]
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ---------- ADD / GET EXPENSES ----------
# Add an expense
@app.route("/expenses", methods=["POST"])
def add_expense():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    category_id = data.get("category_id")
    amount = data.get("amount")
    date_str = data.get("date")
    description = data.get("description", None)

    if not all([user_id, category_id, amount, date_str]):
        return jsonify({"error": "user_id, category_id, amount and date required"}), 400

    d = parse_date(date_str)
    if not d:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Expenses (user_id, category_id, amount, description, date) VALUES (?, ?, ?, ?, ?)",
            (user_id, category_id, amount, description, d)
        )
        conn.commit()
        return jsonify({"message": "Expense added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if conn:
            conn.close()

@app.route("/expenses/<int:user_id>", methods=["GET"])
def get_expenses_for_user(user_id):
    """
    Optional query params:
      - from=YYYY-MM-DD
      - to=YYYY-MM-DD
      - filter=daily|weekly|monthly|all  (if from/to not provided)
    """
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    filter_type = request.args.get("filter", "all").lower()

    base_query = ("SELECT expense_id, user_id, category_id, amount, description, date "
                  "FROM Expenses WHERE user_id = ?")
    params = [user_id]
    base_query, params = apply_date_filter_sql(base_query, params, filter_type, from_str, to_str)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        out = []
        for r in rows:
            out.append({
                "expense_id": int(r[0]),
                "user_id": int(r[1]),
                "category_id": int(r[2]),
                "amount": float(r[3]),
                "description": r[4],
                "date": r[5].isoformat() if isinstance(r[5], date) else str(r[5])
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ---------- ADD / GET INCOME ----------
# Add income
@app.route("/income", methods=["POST"])
def add_income():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    amount = data.get("amount")
    source = data.get("source")
    date_str = data.get("date")

    if not all([user_id, amount, source, date_str]):
        return jsonify({"error": "user_id, amount, source and date required"}), 400
    d = parse_date(date_str)
    if not d:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Income (user_id, amount, source, date) VALUES (?, ?, ?, ?)",
            (user_id, amount, source, d)
        )
        conn.commit()
        return jsonify({"message": "Income added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if conn:
            conn.close()

@app.route("/income/<int:user_id>", methods=["GET"])
def get_income_for_user(user_id):
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    filter_type = request.args.get("filter", "all").lower()

    base_query = "SELECT income_id, user_id, amount, source, date FROM Income WHERE user_id = ?"
    params = [user_id]
    base_query, params = apply_date_filter_sql(base_query, params, filter_type, from_str, to_str)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        out = []
        for r in rows:
            out.append({
                "income_id": int(r[0]),
                "user_id": int(r[1]),
                "amount": float(r[2]),
                "source": r[3],
                "date": r[4].isoformat() if isinstance(r[4], date) else str(r[4])
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ---------- EXPENSES BY CATEGORY (with filters) ----------
# Get expenses by category with optional filters
@app.route("/expenses/category/<int:category_id>", methods=["GET"])
def expenses_by_category(category_id):
    """
    Optional query params:
      - filter=daily|weekly|monthly|all
      - from=YYYY-MM-DD
      - to=YYYY-MM-DD
      - user_id (optional) - if you want to restrict to a single user
    """
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    filter_type = request.args.get("filter", "all").lower()
    user_id_param = request.args.get("user_id")

    base_query = ("SELECT expense_id, user_id, category_id, amount, description, date "
                  "FROM Expenses WHERE category_id = ?")
    params = [category_id]

    if user_id_param:
        base_query += " AND user_id = ?"
        params.append(int(user_id_param))

    base_query, params = apply_date_filter_sql(base_query, params, filter_type, from_str, to_str)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        out = []
        for r in rows:
            out.append({
                "expense_id": int(r[0]),
                "user_id": int(r[1]),
                "category_id": int(r[2]),
                "amount": float(r[3]),
                "description": r[4],
                "date": r[5].isoformat() if isinstance(r[5], date) else str(r[5])
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ---------- REPORTS / SUMMARY ----------
# Summary report (income vs expenses) with filters
@app.route("/reports/summary", methods=["GET"])
def reports_summary():
    """
    Summary for a user (income vs expenses).
    Query params:
      - user_id (required)
      - from (optional YYYY-MM-DD)
      - to   (optional YYYY-MM-DD)
      - filter (optional daily|weekly|monthly|all) - used only if from/to not provided
    """
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    from_str = request.args.get("from")
    to_str = request.args.get("to")
    filter_type = request.args.get("filter", "all").lower()

    income_query = "SELECT ISNULL(SUM(amount), 0) FROM Income WHERE user_id = ?"
    expense_query = "SELECT ISNULL(SUM(amount), 0) FROM Expenses WHERE user_id = ?"
    params = [user_id]

    # prefer explicit range
    if parse_date(from_str) and parse_date(to_str):
        income_query += " AND date BETWEEN ? AND ?"
        expense_query += " AND date BETWEEN ? AND ?"
        params.extend([parse_date(from_str), parse_date(to_str)])
    else:
        # apply filter to both queries
        today = date.today()
        if filter_type == "daily":
            income_query += " AND date = ?"
            expense_query += " AND date = ?"
            params.append(today)
        elif filter_type == "weekly":
            start_of_week = today - timedelta(days=today.weekday())
            income_query += " AND date BETWEEN ? AND ?"
            expense_query += " AND date BETWEEN ? AND ?"
            params.extend([start_of_week, today])
        elif filter_type == "monthly":
            start_of_month = today.replace(day=1)
            income_query += " AND date BETWEEN ? AND ?"
            expense_query += " AND date BETWEEN ? AND ?"
            params.extend([start_of_month, today])

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(income_query, params)
        total_income = cursor.fetchone()[0] or 0
        cursor.execute(expense_query, params)
        total_expenses = cursor.fetchone()[0] or 0
        return jsonify({
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_balance": float(total_income) - float(total_expenses)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# ---------- CONTACT MESSAGES (linked to users) ----------
# Save a contact message
@app.route("/contact", methods=["POST"])
def contact():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    subject = data.get("subject")
    message = data.get("message")
    if not all([user_id, subject, message]):
        return jsonify({"error": "user_id, subject and message required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ContactMessages (user_id, subject, message) VALUES (?, ?, ?)",
            (user_id, subject, message)
        )
        conn.commit()
        return jsonify({"message": "Message saved"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        if conn:
            conn.close()

# ---------- RUN ----------
# Run the app
if __name__ == "__main__":
    app.run(debug=True, port=5000)


