import sqlite3
import os
from flask import Flask

# Create Flask app instance to access the database path
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    DATABASE=os.path.join(app.instance_path, 'jewish_dating.sqlite')
)

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        if 'email' not in existing_columns or 'first_name' not in existing_columns or 'last_name' not in existing_columns:
            print("Creating new users table with additional columns...")
            
            # Drop temporary table if it exists
            cursor.execute("DROP TABLE IF EXISTS users_new")
            
            # Create new table with all desired columns
            conn.execute('''
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE,
                    first_name TEXT,
                    last_name TEXT,
                    balance INTEGER NOT NULL DEFAULT 0,
                    last_active DATETIME,
                    latitude REAL,
                    longitude REAL,
                    min_age_preference INTEGER DEFAULT 18,
                    max_age_preference INTEGER DEFAULT 120
                )
            ''')
            
            # Get list of columns that exist in both tables
            common_columns = [col for col in existing_columns if col in ['id', 'username', 'password']]
            
            # Build the INSERT statement dynamically
            columns_str = ', '.join(common_columns)
            placeholders = ', '.join(['?' for _ in common_columns])
            
            # Copy existing data
            print("Copying existing data...")
            cursor.execute(f'SELECT {columns_str} FROM users')
            rows = cursor.fetchall()
            
            for row in rows:
                values = [row[col] for col in common_columns]
                cursor.execute(f'''
                    INSERT INTO users_new ({columns_str})
                    VALUES ({placeholders})
                ''', values)
            
            # Drop old table and rename new one
            print("Replacing old table with new one...")
            conn.execute('DROP TABLE users')
            conn.execute('ALTER TABLE users_new RENAME TO users')
            
            print("Database migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Database migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    with app.app_context():
        migrate_db() 