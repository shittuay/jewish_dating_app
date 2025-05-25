import sqlite3
import os

DATABASE = os.path.join('instance', 'jewish_dating.sqlite')

def add_column_if_not_exists():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Check if 'last_active' column exists in 'users' table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'last_active' not in columns:
            print(f"Column 'last_active' not found in 'users' table. Adding column...")
            # Add the last_active column
            conn.execute("ALTER TABLE users ADD COLUMN last_active DATETIME DEFAULT CURRENT_TIMESTAMP;")
            conn.commit()
            print("Column 'last_active' added successfully to 'users' table.")
        else:
            print("Column 'last_active' already exists in 'users' table. No migration needed.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print(f"Attempting to connect to database: {DATABASE}")
    if not os.path.exists(DATABASE):
        print(f"Database file not found at {DATABASE}. Please ensure you have run the application at least once to create the database.")
    else:
        add_column_if_not_exists() 