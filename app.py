import os
from flask import Flask, jsonify, request
import psycopg2
from psycopg2 import sql
import time # NEW: Import time module for sleep
import sys  # NEW: Import sys module for exiting

app = Flask(__name__)

# Database connection details from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'todo_db')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

def get_db_connection():
    """Establishes and returns a database connection."""
    # NEW: For better debugging, print connection details here
    print(f"Attempting to connect to DB: host={DB_HOST}, dbname={DB_NAME}, user={DB_USER}", flush=True)
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# Initialize database: creates the todos table if it doesn't exist
# NEW: Added retry logic and improved error handling
def init_db(max_retries=10, retry_delay_seconds=5):
    conn = None
    for i in range(max_retries):
        try:
            print(f"Attempt {i+1}/{max_retries}: Initializing database...", flush=True)
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(sql.SQL('''CREATE TABLE IF NOT EXISTS todos (id SERIAL PRIMARY KEY,title VARCHAR(255) NOT NULL,completed BOOLEAN DEFAULT FALSE,created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);'''))
            conn.commit()
            cur.close()
            print("Database initialized successfully!", flush=True)
            return # Success, exit function
        except psycopg2.OperationalError as e: # Catch specific connection errors
            print(f"Database connection failed (OperationalError): {e}", flush=True)
            print(f"Retrying in {retry_delay_seconds} seconds...", flush=True)
            time.sleep(retry_delay_seconds)
        except Exception as e:
            print(f"Error initializing database (general exception): {e}", flush=True)
            print("This is a critical error. Exiting application.", flush=True)
            sys.exit(1) # Exit immediately if a non-operational error occurs
        finally:
            if conn:
                conn.close()
    print(f"Failed to initialize database after {max_retries} attempts. Exiting application.", flush=True)
    sys.exit(1) # Exit if all retries fail

# Route to check API health and DB connection
@app.route('/health', methods=['GET'])
def health_check():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "OK", "database_connection": "successful", "version": "1.3"}), 200
    except Exception as e:
        # Capture more specific error in health check too
        return jsonify({"status": "ERROR", "database_connection": f"failed: {e}"}), 500

# Get all todos
@app.route('/todos', methods=['GET'])
def get_todos():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, completed, created_at FROM todos ORDER BY created_at DESC;")
    todos = cur.fetchall()
    cur.close()
    conn.close()
    # Convert fetched rows to a list of dictionaries for JSON serialization
    todos_list = []
    for t in todos:
        todos_list.append({
            "id": t[0],
            "title": t[1],
            "completed": t[2],
            "created_at": t[3].isoformat() # Convert datetime to ISO format string
        })
    return jsonify(todos_list)

# Add a new todo
@app.route('/todos', methods=['POST'])
def add_todo():
    data = request.json
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400

    title = data['title']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO todos (title) VALUES (%s) RETURNING id, title, completed, created_at;", (title,))
    new_todo = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    # Return the newly created todo details
    return jsonify({
        "id": new_todo[0],
        "title": new_todo[1],
        "completed": new_todo[2],
        "created_at": new_todo[3].isoformat()
    }), 201

# Update a todo
@app.route('/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updates = []
    params = []
    if 'title' in data:
        updates.append(sql.SQL("title = %s"))
        params.append(data['title'])
    if 'completed' in data:
        updates.append(sql.SQL("completed = %s"))
        params.append(data['completed'])

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    # Construct the query dynamically and safely
    query = sql.SQL("UPDATE todos SET {} WHERE id = %s RETURNING id;").format(
        sql.SQL(', ').join(updates)
    )
    params.append(todo_id)

    cur.execute(query, tuple(params))
    updated_id = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not updated_id:
        return jsonify({"error": "Todo not found"}), 404
    return jsonify({"message": "Todo updated successfully"}), 200

# Delete a todo
@app.route('/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos WHERE id = %s RETURNING id;", (todo_id,))
    deleted_id = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not deleted_id:
        return jsonify({"error": "Todo not found"}), 404
    return jsonify({"message": "Todo deleted successfully"}), 204 # 204 No Content for successful deletion

# Initialize database on application startup
# Use app.app_context() to ensure we're within the Flask application context
with app.app_context():
    init_db() # Call the init_db with retry logic

if __name__ == '__main__':
    # When running locally via `python app.py`
    # In Docker, Gunicorn will handle running the app
    app.run(debug=True, host='0.0.0.0', port=5000)