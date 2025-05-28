import sqlite3
import os
from datetime import datetime

def get_db_connection():
    conn = sqlite3.connect('instance/jewish_dating.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Add new columns to profiles table
    new_columns = [
        # Education and Career
        ('education_level', 'TEXT'),
        ('occupation', 'TEXT'),
        ('employer', 'TEXT'),
        ('annual_income_range', 'TEXT'),
        
        # Family and Background
        ('family_background', 'TEXT'),
        ('parents_observance', 'TEXT'),
        ('siblings', 'INTEGER'),
        ('children', 'INTEGER'),
        ('want_children', 'TEXT'),
        
        # Jewish Community
        ('community_involvement', 'TEXT'),
        ('jewish_education', 'TEXT'),
        ('languages', 'TEXT'),
        ('aliyah_interest', 'TEXT'),
        
        # Relationship
        ('relationship_goals', 'TEXT'),
        ('dating_preferences', 'TEXT'),
        ('deal_breakers', 'TEXT'),
        
        # Profile Status
        ('profile_completion', 'INTEGER DEFAULT 0'),
        ('is_verified', 'BOOLEAN DEFAULT 0'),
        ('verification_method', 'TEXT'),
        ('verification_date', 'TIMESTAMP'),
        ('last_updated', 'TIMESTAMP'),
        
        # Additional Preferences
        ('min_age_preference', 'INTEGER DEFAULT 18'),
        ('max_age_preference', 'INTEGER DEFAULT 120'),
        ('location_preference', 'TEXT'),
        ('distance_preference', 'INTEGER DEFAULT 50')
    ]

    # Check existing columns
    cursor.execute("PRAGMA table_info(profiles)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    # Add new columns if they don't exist
    for column_name, column_type in new_columns:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE profiles ADD COLUMN {column_name} {column_type}")
                print(f"Added column: {column_name}")
            except sqlite3.OperationalError as e:
                print(f"Error adding column {column_name}: {e}")

    # Create verification table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profile_verification (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        verification_type TEXT NOT NULL,
        verification_status TEXT NOT NULL,
        verification_data TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        verified_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id)
    )
    ''')

    # Create profile_completion_rules table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profile_completion_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        field_name TEXT NOT NULL,
        weight INTEGER NOT NULL,
        is_required BOOLEAN DEFAULT 0,
        description TEXT
    )
    ''')

    # Insert default completion rules
    completion_rules = [
        ('profile_picture', 20, True, 'Profile picture'),
        ('bio', 15, True, 'About me'),
        ('age', 10, True, 'Age'),
        ('observance_level', 10, True, 'Level of religious observance'),
        ('education_level', 5, False, 'Education level'),
        ('occupation', 5, False, 'Occupation'),
        ('family_background', 5, False, 'Family background'),
        ('community_involvement', 5, False, 'Community involvement'),
        ('languages', 5, False, 'Languages spoken'),
        ('relationship_goals', 10, False, 'Relationship goals')
    ]

    cursor.execute("DELETE FROM profile_completion_rules")
    cursor.executemany(
        "INSERT INTO profile_completion_rules (field_name, weight, is_required, description) VALUES (?, ?, ?, ?)",
        completion_rules
    )

    conn.commit()
    conn.close()
    print("Database migration completed successfully!")

if __name__ == '__main__':
    migrate_db() 