from flask import Flask  # Flask framework
import pyodbc   # ODBC library for SQL Server

# Start Flask app
app = Flask(__name__)

# 🔹 Function to connect to SQL Server
def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"   # Use Driver 17
        "SERVER=DESKTOP-15VGM3T\\SQLEXPRESS;"       # Your SQL Server instance
        "DATABASE=ExpenseTracker;"                  # Your database name
        "Trusted_Connection=yes;"                   # Windows Authentication
    )
    return conn

# 🔹 Homepage route
@app.route("/")
def home():
    try:
        conn = get_db_connection()   # open database
        cursor = conn.cursor()       # make cursor to run queries

        # Example query: get first category
        cursor.execute("SELECT TOP 1 category_name FROM Categories;")
        row = cursor.fetchone()

        conn.close()  # always close connection

        return f"Connected to DB! Example Category: {row[0]}"
    except Exception as e:
        return f"Error connecting to DB: {e}"

# 🔹 Start the server
if __name__ == "__main__":
    app.run(debug=True, port=5000)
