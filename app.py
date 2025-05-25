import os # Import os module
from werkzeug.utils import secure_filename # Import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort, jsonify, Response
import sqlite3
import hashlib
from functools import wraps
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import shutil
import random
import csv
from io import StringIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create the Flask application
app = Flask(__name__, instance_relative_config=True)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

app.config.from_mapping(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev'),
    DATABASE=os.path.join(app.instance_path, 'jewish_dating.sqlite'),
    UPLOAD_FOLDER=os.path.join('static', 'uploads'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='your-email@gmail.com',  # Update with your email
    MAIL_PASSWORD='your-app-password',     # Update with your app password
    MAIL_DEFAULT_SENDER='Jewish Dating App <your-email@gmail.com>',
    DEEPSEEK_API_KEY=os.getenv('DEEPSEEK_API_KEY', ''),  # Add DeepSeek API key
    DEEPSEEK_API_URL='https://api.deepseek.com/v1/chat/completions'  # DeepSeek API endpoint
)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions for profile pictures
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    try:
        # Create users table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0
            );
        ''')

        # Check and add last_active column if it doesn't exist
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'last_active' not in columns:
            print("Adding 'last_active' column to users table...")
            # Add the last_active column without default for compatibility
            conn.execute("ALTER TABLE users ADD COLUMN last_active DATETIME;")
            # Update existing rows with current timestamp
            conn.execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE last_active IS NULL;")
            print("'last_active' column added and existing rows updated successfully.")

        conn.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                age INTEGER,
                bio TEXT,
                observance_level TEXT,
                kosher_level TEXT,
                shabbat_observance TEXT,
                synagogue_affiliation TEXT,
                profile_picture TEXT, -- NEW COLUMN for profile picture filename
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                liker_id INTEGER NOT NULL,
                liked_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(liker_id, liked_id),
                FOREIGN KEY (liker_id) REFERENCES users(id),
                FOREIGN KEY (liked_id) REFERENCES users(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                review_text TEXT NOT NULL,
                photo TEXT,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS adverts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image TEXT,
                link TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                views INTEGER NOT NULL DEFAULT 0,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_at DATETIME
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                payment_id TEXT,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS newsletter_subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                unsubscribed_at DATETIME,
                last_email_sent DATETIME
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS newsletter_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_newsletters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                scheduled_for DATETIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                sent_at DATETIME,
                created_by INTEGER NOT NULL,
                template_id INTEGER,
                recurring_id INTEGER REFERENCES recurring_newsletters(id),
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (template_id) REFERENCES newsletter_templates(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_newsletter_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_newsletter_id INTEGER NOT NULL,
                subscriber_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                sent_at DATETIME,
                error_message TEXT,
                FOREIGN KEY (scheduled_newsletter_id) REFERENCES scheduled_newsletters(id),
                FOREIGN KEY (subscriber_id) REFERENCES newsletter_subscribers(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recurring_newsletters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                frequency TEXT NOT NULL CHECK(frequency IN ('daily', 'weekly', 'monthly')),
                start_date DATETIME NOT NULL,
                end_date DATETIME,
                last_sent DATETIME,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed')),
                created_by INTEGER NOT NULL,
                template_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (template_id) REFERENCES newsletter_templates(id)
            );
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS recurring_newsletter_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recurring_newsletter_id INTEGER NOT NULL,
                subscriber_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'excluded')),
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recurring_newsletter_id) REFERENCES recurring_newsletters(id),
                FOREIGN KEY (subscriber_id) REFERENCES newsletter_subscribers(id),
                UNIQUE(recurring_newsletter_id, subscriber_id)
            );
        ''')

        # Insert default templates if they don't exist
        default_templates = [
            {
                'name': 'Welcome Email',
                'subject': 'Welcome to Jewish Dating App!',
                'content': '''Welcome to our community!

We're excited to have you join us on your journey to find meaningful connections within the Jewish community.

Here's what you can do next:
1. Complete your profile
2. Browse potential matches
3. Join our upcoming events
4. Read success stories from other members

If you have any questions, our support team is here to help.

Best regards,
The Jewish Dating App Team''',
                'description': 'Welcome email for new subscribers'
            },
            {
                'name': 'Weekly Digest',
                'subject': 'Your Weekly Jewish Dating Digest',
                'content': '''Here's your weekly update from Jewish Dating App!

📅 Upcoming Events:
{events}

💝 Success Stories:
{success_stories}

🎯 Featured Profiles:
{featured_profiles}

💡 Dating Tips:
{dating_tips}

Stay connected with our community and keep checking your matches!

Best regards,
The Jewish Dating App Team''',
                'description': 'Weekly newsletter with updates and highlights'
            },
            {
                'name': 'Event Invitation',
                'subject': 'Join Our Upcoming Jewish Singles Event!',
                'content': '''We're hosting a special event for our community!

📅 Date: {event_date}
📍 Location: {event_location}
⏰ Time: {event_time}

What to expect:
- Meet other Jewish singles in a comfortable setting
- Enjoy kosher refreshments
- Participate in fun ice-breaker activities
- Connect with potential matches

RSVP now to secure your spot!

Best regards,
The Jewish Dating App Team''',
                'description': 'Template for event invitations'
            }
        ]
        
        for template in default_templates:
            conn.execute('''
                INSERT OR IGNORE INTO newsletter_templates (name, subject, content, description)
                VALUES (?, ?, ?, ?)
            ''', (template['name'], template['subject'], template['content'], template['description']))
        
        conn.commit()
    finally:
        conn.close()

# Initialize the database when the app starts
with app.app_context():
    init_db()

# --- Database Migration --- 
def migrate_db():
    conn = None  # Initialize conn to None
    try:
        conn = get_db_connection()
        # Check if last_active column exists in users table
        cursor = conn.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'last_active' not in columns:
            print("Adding 'last_active' column to users table...")
            conn.execute("ALTER TABLE users ADD COLUMN last_active DATETIME DEFAULT CURRENT_TIMESTAMP;")
            conn.commit()
            print("'last_active' column added successfully.")
        # Add other migrations here if needed

    except sqlite3.Error as e:
        print(f"Database migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# Run migrations after initializing the db
with app.app_context():
    init_db()
    migrate_db()

# Add context processor for current datetime
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

# --- Before each request, load the logged-in user if any ---
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        conn = get_db_connection()
        g.user = conn.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        # Update last_active timestamp for logged-in user
        conn.execute(
            'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?', (user_id,)
        )
        conn.commit()
        conn.close()

# --- Decorator to ensure a user is logged in ---
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('You need to be logged in to access this page.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view

# --- Admin check decorator ---
def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not g.user or g.user['id'] != 1:
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view

# --- ROUTES ---

@app.route('/')
def index():
    if g.user:
        conn = get_db_connection()
        try:
            profile = conn.execute(
                'SELECT * FROM profiles WHERE user_id = ?', (g.user['id'],)
            ).fetchone()
            reviews = conn.execute('SELECT * FROM reviews WHERE status = "approve" ORDER BY created_at DESC LIMIT 6').fetchall()

            # Get featured profiles (recently active users with high engagement)
            featured_profiles = conn.execute('''
                SELECT p.*, u.username, u.id as user_id,
                       COUNT(DISTINCT l.id) as like_count,
                       EXISTS(SELECT 1 FROM likes WHERE liker_id = ? AND liked_id = u.id) as is_liked_by_me
                FROM profiles p
                JOIN users u ON p.user_id = u.id
                LEFT JOIN likes l ON l.liked_id = u.id
                WHERE u.id != ?
                GROUP BY u.id
                ORDER BY like_count DESC, u.username ASC
                LIMIT 6
            ''', (g.user['id'], g.user['id'])).fetchall()

            # Get two random approved adverts for side banners
            adverts = conn.execute('SELECT * FROM adverts WHERE status = "approved"').fetchall()
            left_ad = right_ad = None
            if adverts:
                ads = random.sample(adverts, min(2, len(adverts)))
                left_ad = ads[0]
                if len(ads) > 1:
                    right_ad = ads[1]
                else:
                    right_ad = ads[0]

            return render_template('index.html', profile=profile, reviews=reviews, 
                                 featured_profiles=featured_profiles, left_ad=left_ad, right_ad=right_ad)
        finally:
            conn.close()
    else:
        conn = get_db_connection()
        try:
            reviews = conn.execute('SELECT * FROM reviews WHERE status = "approve" ORDER BY created_at DESC LIMIT 6').fetchall()
            
            # Get featured profiles for non-logged in users
            featured_profiles = conn.execute('''
                SELECT p.*, u.username, u.id as user_id,
                       COUNT(DISTINCT l.id) as like_count
                FROM profiles p
                JOIN users u ON p.user_id = u.id
                LEFT JOIN likes l ON l.liked_id = u.id
                GROUP BY u.id
                ORDER BY like_count DESC, u.username ASC
                LIMIT 6
            ''').fetchall()
            
            return render_template('index.html', reviews=reviews, featured_profiles=featured_profiles)
        finally:
            conn.close()

@app.route('/register', methods=('GET', 'POST'))
def register():
    if g.user:
        flash('You are already logged in.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        age = request.form['age']
        observance_level = request.form['observance_level']
        kosher_level = request.form['kosher_level']
        shabbat_observance = request.form['shabbat_observance']

        conn = get_db_connection()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif not age or not age.isdigit() or int(age) < 18 or int(age) > 120:
            error = 'Age must be a number between 18 and 120.'
        elif not observance_level:
            error = 'Level of observance is required.'
        elif not kosher_level:
            error = 'Kosher observance level is required.'
        elif not shabbat_observance:
            error = 'Shabbat observance level is required.'
        elif conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"User {username} is already registered."

        if error is None:
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            # First create the user
            cursor = conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, hashed_password))
            user_id = cursor.lastrowid
            
            # Then create their profile
            conn.execute('''INSERT INTO profiles 
                (user_id, age, observance_level, kosher_level, shabbat_observance)
                VALUES (?, ?, ?, ?, ?)''',
                (user_id, age, observance_level, kosher_level, shabbat_observance))
            
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        flash(error, 'error')
        conn.close()

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if g.user:
        flash('You are already logged in.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        error = None
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        conn.close()

        if user is None:
            error = 'Incorrect username.'
        elif hashlib.sha256(password.encode('utf-8')).hexdigest() != user['password']:
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            flash('You were successfully logged in!', 'success')
            return redirect(url_for('index'))

        flash(error, 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/online_users')
@login_required
def online_users():
    conn = get_db_connection()
    try:
        # Define the time threshold for considering a user online (e.g., last 5 minutes)
        time_threshold = datetime.datetime.now() - datetime.timedelta(minutes=5)

        # Query for users whose last_active timestamp is within the threshold, excluding the current user
        online_users_list = conn.execute(
            'SELECT id, username FROM users WHERE last_active >= ? AND id != ?',
            (time_threshold, g.user['id'])
        ).fetchall()

        # Convert the fetched rows to a list of dictionaries
        online_users_data = [{ 'id': user['id'], 'username': user['username'] } for user in online_users_list]

        return jsonify(online_users_data)
    except Exception as e:
        # Log the error or handle it as needed
        print(f"Error fetching online users: {e}")
        return jsonify({"error": "Could not fetch online users"}), 500
    finally:
        conn.close()

# --- PROFILE ROUTE (for logged-in user's own profile) ---
@app.route('/profile', methods=('GET', 'POST'))
@login_required
def profile():
    conn = get_db_connection()
    user_id = g.user['id']

    if request.method == 'POST':
        age = request.form['age']
        bio = request.form['bio']
        observance_level = request.form.get('observance_level')
        kosher_level = request.form.get('kosher_level')
        shabbat_observance = request.form.get('shabbat_observance')
        synagogue_affiliation = request.form.get('synagogue_affiliation')
        
        # Handle profile picture upload
        profile_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
                # Generate a unique filename
                filename = secure_filename(f"{user_id}_{int(datetime.datetime.now().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                profile_picture = filename

        error = None
        if not age or not bio:
            error = 'Age and About Me are required.'
        elif not age.isdigit() or int(age) < 18 or int(age) > 120:
            error = 'Age must be a number between 18 and 120.'

        if error is None:
            existing_profile = conn.execute(
                'SELECT * FROM profiles WHERE user_id = ?', (user_id,)
            ).fetchone()

            if existing_profile:
                # If there's a new profile picture, delete the old one
                if profile_picture and existing_profile['profile_picture']:
                    old_file = os.path.join(app.config['UPLOAD_FOLDER'], existing_profile['profile_picture'])
                    if os.path.exists(old_file):
                        os.remove(old_file)

                # Update profile with or without new picture
                if profile_picture:
                    conn.execute(
                        '''UPDATE profiles SET
                            age = ?, bio = ?,
                            observance_level = ?, kosher_level,
                            shabbat_observance = ?, synagogue_affiliation = ?,
                            profile_picture = ?
                        WHERE user_id = ?''',
                        (age, bio,
                         observance_level, kosher_level,
                         shabbat_observance, synagogue_affiliation,
                         profile_picture, user_id)
                    )
                else:
                    conn.execute(
                        '''UPDATE profiles SET
                            age = ?, bio = ?,
                            observance_level = ?, kosher_level = ?,
                            shabbat_observance = ?, synagogue_affiliation = ?
                        WHERE user_id = ?''',
                        (age, bio,
                         observance_level, kosher_level,
                         shabbat_observance, synagogue_affiliation,
                         user_id)
                    )
                flash('Profile updated successfully!', 'success')
            else:
                conn.execute(
                    '''INSERT INTO profiles
                        (user_id, age, bio,
                         observance_level, kosher_level,
                         shabbat_observance, synagogue_affiliation,
                         profile_picture)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, age, bio,
                     observance_level, kosher_level,
                     shabbat_observance, synagogue_affiliation,
                     profile_picture)
                )
                flash('Profile created successfully!', 'success')
            conn.commit()
            conn.close()
            return redirect(url_for('profile'))

        flash(error, 'error')
        conn.close()

    profile_data = conn.execute(
        'SELECT age, bio, observance_level, kosher_level, shabbat_observance, synagogue_affiliation, profile_picture FROM profiles WHERE user_id = ?', (user_id,)
    ).fetchone()
    photos = conn.execute('SELECT id, filename FROM user_photos WHERE user_id = ? ORDER BY uploaded_at DESC', (user_id,)).fetchall()
    conn.close()

    return render_template('profile.html', profile=profile_data, gallery_photos=photos)

# --- BROWSE PROFILES ROUTE (MODIFIED for likes) ---
@app.route('/browse')
@login_required
def browse_profiles():
    conn = get_db_connection()
    current_user_id = g.user['id']

    profiles_data = conn.execute(
        '''SELECT p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation,
                  p.profile_picture, u.username, u.id as user_id,
                  EXISTS(SELECT 1 FROM likes WHERE liker_id = ? AND liked_id = u.id) AS is_liked_by_me
           FROM profiles p JOIN users u ON p.user_id = u.id
           WHERE u.id != ?
           ORDER BY u.username ASC''',
        (current_user_id, current_user_id)
    ).fetchall()
    conn.close()

    return render_template('browse_profiles.html', profiles=profiles_data)

# --- VIEW OTHER USER'S PROFILE ROUTE (MODIFIED for likes) ---
@app.route('/user_profile/<int:user_id>')
@login_required
def view_user_profile(user_id):
    conn = get_db_connection()
    current_user_id = g.user['id']

    if user_id == current_user_id:
        conn.close()
        return redirect(url_for('profile'))

    target_user = conn.execute(
        'SELECT id, username FROM users WHERE id = ?', (user_id,)
    ).fetchone()

    if target_user is None:
        conn.close()
        flash('User not found.', 'error')
        return redirect(url_for('browse_profiles'))

    target_profile = conn.execute(
        '''SELECT age, bio, observance_level, kosher_level, shabbat_observance, synagogue_affiliation
           FROM profiles WHERE user_id = ?''', (user_id,)
    ).fetchone()

    is_liked_by_me = conn.execute(
        'SELECT 1 FROM likes WHERE liker_id = ? AND liked_id = ?',
        (current_user_id, user_id)
    ).fetchone() is not None

    conn.close()

    return render_template('view_profile.html',
                           target_user=target_user,
                           target_profile=target_profile,
                           is_liked_by_me=is_liked_by_me)

# --- SEARCH PROFILES ROUTE (ENHANCED) ---
@app.route('/search')
@login_required
def search_profiles():
    conn = get_db_connection()
    current_user_id = g.user['id']

    min_age = request.args.get('min_age', type=int)
    max_age = request.args.get('max_age', type=int)
    observance_level = request.args.get('observance_level')
    kosher_level = request.args.get('kosher_level')
    shabbat_observance = request.args.get('shabbat_observance')
    keyword_search = request.args.get('keyword_search')

    query_parts = [
        'SELECT p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation, ',
        'p.profile_picture, u.username, u.id as user_id, ',
        'EXISTS(SELECT 1 FROM likes WHERE liker_id = ? AND liked_id = u.id) AS is_liked_by_me ',
        'FROM profiles p JOIN users u ON p.user_id = u.id ',
        'WHERE u.id != ? '
    ]
    params = [current_user_id, current_user_id]

    if min_age is not None:
        query_parts.append('AND p.age >= ? ')
        params.append(min_age)
    if max_age is not None:
        query_parts.append('AND p.age <= ? ')
        params.append(max_age)

    if min_age is not None and max_age is not None and min_age > max_age:
        flash('Minimum age cannot be greater than maximum age.', 'error')

    if observance_level and observance_level != '':
        query_parts.append('AND p.observance_level = ? ')
        params.append(observance_level)
    if kosher_level and kosher_level != '':
        query_parts.append('AND p.kosher_level = ? ')
        params.append(kosher_level)
    if shabbat_observance and shabbat_observance != '':
        query_parts.append('AND p.shabbat_observance = ? ')
        params.append(shabbat_observance)

    if keyword_search:
        search_term = f'%{keyword_search}%'
        query_parts.append('AND (p.bio LIKE ? OR p.synagogue_affiliation LIKE ? OR u.username LIKE ?) ')
        params.append(search_term)
        params.append(search_term)
        params.append(search_term)

    query_str = ''.join(query_parts)
    query_str += ' ORDER BY u.username ASC'

    profiles = conn.execute(query_str, tuple(params)).fetchall()
    conn.close()

    return render_template('search_profiles.html', profiles=profiles)

# NEW ROUTES FOR LIKING/UNLIKING
@app.route('/like/<int:user_id>', methods=['POST'])
@login_required
def like_profile(user_id):
    conn = get_db_connection()
    liker_id = g.user['id']
    liked_id = user_id

    if liker_id == liked_id:
        flash('You cannot like your own profile.', 'error')
        conn.close()
        return redirect(url_for('view_user_profile', user_id=user_id))

    target_user = conn.execute('SELECT username FROM users WHERE id = ?', (liked_id,)).fetchone() # Get username for flash
    if not target_user:
        flash('Profile not found.', 'error')
        conn.close()
        return redirect(request.referrer or url_for('browse_profiles')) # Redirect to browse if profile not found

    try:
        conn.execute('INSERT INTO likes (liker_id, liked_id) VALUES (?, ?)',
                     (liker_id, liked_id))
        conn.commit()
        flash(f'You liked {target_user["username"]}!', 'success')
    except sqlite3.IntegrityError:
        flash(f'You have already liked {target_user["username"]}.', 'info') # More specific message
    finally:
        conn.close()
    return redirect(request.referrer or url_for('browse_profiles'))

@app.route('/unlike/<int:user_id>', methods=['POST'])
@login_required
def unlike_profile(user_id):
    conn = get_db_connection()
    liker_id = g.user['id']
    liked_id = user_id

    if liker_id == liked_id:
        flash('You cannot unlike your own profile.', 'error')
        conn.close()
        return redirect(url_for('view_user_profile', user_id=user_id))

    target_user = conn.execute('SELECT username FROM users WHERE id = ?', (liked_id,)).fetchone() # Get username for flash
    if not target_user:
        flash('Profile not found.', 'error')
        conn.close()
        return redirect(request.referrer or url_for('browse_profiles'))

    conn.execute('DELETE FROM likes WHERE liker_id = ? AND liked_id = ?',
                 (liker_id, liked_id))
    conn.commit()
    flash(f'You unliked {target_user["username"]}.', 'info')
    conn.close()
    return redirect(request.referrer or url_for('browse_profiles'))

# --- NEW: My Likes / Who Liked Me Route ---
@app.route('/my_likes')
@login_required
def my_likes():
    conn = get_db_connection()
    current_user_id = g.user['id']

    # Profiles I (current_user) have liked
    liked_by_me = conn.execute(
        '''SELECT u.id AS user_id, u.username, p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation, p.profile_picture
           FROM likes l
           JOIN users u ON l.liked_id = u.id
           JOIN profiles p ON u.id = p.user_id
           WHERE l.liker_id = ?
           ORDER BY u.username ASC''',
        (current_user_id,)
    ).fetchall()

    # Profiles that have liked me (current_user)
    liked_me = conn.execute(
        '''SELECT u.id AS user_id, u.username, p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation, p.profile_picture
           FROM likes l
           JOIN users u ON l.liker_id = u.id
           JOIN profiles p ON u.id = p.user_id
           WHERE l.liked_id = ?
           ORDER BY u.username ASC''',
        (current_user_id,)
    ).fetchall()
    
    # Check for mutual likes (matches!)
    mutual_likes = conn.execute(
        '''SELECT u.id AS user_id, u.username, p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation, p.profile_picture
           FROM likes l1
           JOIN likes l2 ON l1.liker_id = l2.liked_id AND l1.liked_id = l2.liker_id
           JOIN users u ON l1.liked_id = u.id
           JOIN profiles p ON u.id = p.user_id
           WHERE l1.liker_id = ?
           ORDER BY u.username ASC''',
        (current_user_id,)
    ).fetchall()

    conn.close()

    return render_template('my_likes.html',
                           liked_by_me=liked_by_me,
                           liked_me=liked_me,
                           mutual_likes=mutual_likes)

# --- MESSAGES OVERVIEW ROUTE ---
@app.route('/messages')
@login_required
def messages():
    conn = get_db_connection()
    current_user_id = g.user['id']

    conversations_raw = conn.execute(
        '''
        SELECT DISTINCT
            CASE
                WHEN sender_id = ? THEN receiver_id
                ELSE sender_id
            END as other_user_id,
            MAX(timestamp) as last_message_timestamp
        FROM messages
        WHERE sender_id = ? OR receiver_id = ?
        GROUP BY other_user_id
        ORDER BY last_message_timestamp DESC
        ''',
        (current_user_id, current_user_id, current_user_id)
    ).fetchall()

    conversations_display = []
    for convo in conversations_raw:
        other_user_id = convo['other_user_id']
        other_user = conn.execute(
            'SELECT username FROM users WHERE id = ?', (other_user_id,)
        ).fetchone()
        if other_user:
            conversations_display.append({
                'other_user_id': other_user_id,
                'other_username': other_user['username'],
                'last_message_timestamp': convo['last_message_timestamp']
            })
    conn.close()

    return render_template('messages_overview.html', conversations=conversations_display)

# --- INDIVIDUAL CONVERSATION ROUTE ---
@app.route('/messages/<int:user_id>', methods=('GET', 'POST'))
@login_required
def conversation(user_id):
    conn = get_db_connection()
    current_user_id = g.user['id']

    other_user = conn.execute(
        'SELECT id, username FROM users WHERE id = ?', (user_id,)
    ).fetchone()

    if not other_user:
        conn.close()
        flash('User not found.', 'error')
        return redirect(url_for('messages'))

    if other_user['id'] == current_user_id:
        conn.close()
        flash('You cannot message yourself.', 'warning')
        return redirect(url_for('messages'))

    if request.method == 'POST':
        message_content = request.form['message_content'].strip()

        if not message_content:
            flash('Message cannot be empty.', 'error')
        else:
            conn.execute(
                'INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)',
                (current_user_id, other_user['id'], message_content)
            )
            conn.commit()
            return redirect(url_for('conversation', user_id=other_user['id']))

    messages = conn.execute(
        '''
        SELECT sender_id, receiver_id, content, timestamp
        FROM messages
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY timestamp ASC
        ''',
        (current_user_id, other_user['id'], other_user['id'], current_user_id)
    ).fetchall()
    conn.close()

    return render_template('conversation.html', messages=messages, other_user=other_user)

# Review submission route
@app.route('/submit_review', methods=['POST'])
def submit_review():
    name = request.form['name']
    location = request.form.get('location', '')
    review_text = request.form['review_text']
    photo = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"review_{int(datetime.datetime.now().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            photo = filename
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO reviews (name, location, review_text, photo, status) VALUES (?, ?, ?, ?, ?)',
        (name, location, review_text, photo, 'pending')
    )
    conn.commit()
    conn.close()
    flash('Thank you for your review! It will appear after admin approval.', 'success')
    return redirect(url_for('index'))

# Helper: Ensure user-specific upload folder exists
def get_user_upload_folder(user_id):
    folder = os.path.join(app.config['UPLOAD_FOLDER'], f'user_{user_id}')
    os.makedirs(folder, exist_ok=True)
    return folder

# Upload gallery photo
@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    user_id = g.user['id']
    if 'photo' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('profile'))
    file = request.files['photo']
    if file and file.filename and allowed_file(file.filename):
        folder = get_user_upload_folder(user_id)
        filename = secure_filename(f"{user_id}_{int(datetime.datetime.now().timestamp())}_{file.filename}")
        file.save(os.path.join(folder, filename))
        conn = get_db_connection()
        conn.execute('INSERT INTO user_photos (user_id, filename) VALUES (?, ?)', (user_id, f'user_{user_id}/{filename}'))
        conn.commit()
        conn.close()
        flash('Photo uploaded!', 'success')
    else:
        flash('Invalid file type.', 'error')
    return redirect(url_for('profile'))

# Delete gallery photo
@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    user_id = g.user['id']
    conn = get_db_connection()
    photo = conn.execute('SELECT filename FROM user_photos WHERE id = ? AND user_id = ?', (photo_id, user_id)).fetchone()
    if photo:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        conn.execute('DELETE FROM user_photos WHERE id = ?', (photo_id,))
        conn.commit()
        flash('Photo deleted.', 'success')
    else:
        flash('Photo not found.', 'error')
    conn.close()
    return redirect(url_for('profile'))

def get_love_agent_response(user_message, user_context=None):
    """Get a response from the DeepSeek-powered love agent."""
    if not app.config['DEEPSEEK_API_KEY']:
        return "I'm currently offline. Please try again later or contact support."
    
    try:
        headers = {
            'Authorization': f'Bearer {app.config["DEEPSEEK_API_KEY"]}',
            'Content-Type': 'application/json'
        }
        
        # Construct the system message for the love agent persona
        system_message = """You are a warm, empathetic Jewish dating coach and love agent. Your role is to:
1. Provide thoughtful dating advice while respecting Jewish values and traditions
2. Help users navigate the dating process with wisdom and sensitivity
3. Offer support and encouragement in their journey to find meaningful connections
4. Share insights about Jewish dating customs and practices when relevant
5. Maintain a professional yet friendly tone
6. Never provide medical, legal, or financial advice
7. Always prioritize user safety and well-being

Remember to:
- Be supportive and non-judgmental
- Respect different levels of religious observance
- Encourage healthy dating practices
- Focus on building meaningful connections
- Maintain appropriate boundaries

Crucially, respond in a natural, conversational tone and **avoid using any markdown formatting** (like bolding with *, italics with _, or code blocks with ```)."""
        
        # Prepare the conversation history
        messages = [
            {"role": "system", "content": system_message}
        ]
        
        # Add user context if available
        if user_context:
            messages.append({
                "role": "system",
                "content": f"User context: {user_context}"
            })
        
        # Add the user's message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Make the API request
        response = requests.post(
            app.config['DEEPSEEK_API_URL'],
            headers=headers,
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            app.logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
            return "I'm having trouble connecting right now. Please try again later."
            
    except Exception as e:
        app.logger.error(f"Error in love agent: {str(e)}")
        return "I encountered an error. Please try again later."

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'reply': "Please type a message."})
    
    # Get user context if available
    user_context = None
    if g.user:
        conn = get_db_connection()
        try:
            profile = conn.execute(
                'SELECT * FROM profiles WHERE user_id = ?', (g.user['id'],)
            ).fetchone()
            if profile:
                user_context = f"User is {profile['age']} years old, {profile['observance_level']} observance level, {profile['kosher_level']} kosher level, {profile['shabbat_observance']} shabbat observance, affiliated with {profile['synagogue_affiliation']}."
        finally:
            conn.close()
    
    # Get AI response from love agent
    reply = get_love_agent_response(user_message, user_context)
    return jsonify({'reply': reply})

@app.route('/adverts')
def adverts():
    adverts = [
        {
            'image': url_for('static', filename='adverts/jewish_event.jpg'),
            'title': 'Jewish Singles Event',
            'description': 'Join our upcoming singles mixer in NYC! Meet new people and enjoy a fun evening.',
            'link': '#'
        },
        {
            'image': url_for('static', filename='adverts/premium_membership.jpg'),
            'title': 'Upgrade to Premium',
            'description': 'Unlock unlimited likes, see who viewed your profile, and more with Premium Membership.',
            'link': '#'
        },
        {
            'image': url_for('static', filename='adverts/app_promo.jpg'),
            'title': 'Download Our App',
            'description': 'Get the Jewish Dating App on your phone for the best experience, anytime, anywhere.',
            'link': '#'
        },
        {
            'image': url_for('static', filename='adverts/success_story.jpg'),
            'title': 'Success Stories',
            'description': 'Read how real couples found love on our platform. Your story could be next!',
            'link': '#'
        }
    ]
    return render_template('adverts.html', adverts=adverts)

@app.route('/submit_advert', methods=['GET', 'POST'])
@login_required
def submit_advert():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        link = request.form['link']
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"ad_{g.user['id']}_{int(datetime.datetime.now().timestamp())}_{file.filename}")
                image_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'adverts')
                os.makedirs(image_folder, exist_ok=True)
                file.save(os.path.join(image_folder, filename))
                image = f"adverts/{filename}"
        if not title or not description or not link:
            flash('All fields are required.', 'error')
            return redirect(url_for('submit_advert'))
        conn = get_db_connection()
        conn.execute('''INSERT INTO adverts (user_id, title, description, image, link, status) VALUES (?, ?, ?, ?, ?, ?)''',
                     (g.user['id'], title, description, image, link, 'pending'))
        conn.commit()
        conn.close()
        flash('Your advert has been submitted for review!', 'success')
        return redirect(url_for('adverts'))
    return render_template('submit_advert.html')

@app.route('/admin/adverts')
@admin_required
def admin_adverts():
    conn = get_db_connection()
    adverts = conn.execute('''
        SELECT a.*, u.username FROM adverts a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_adverts.html', adverts=adverts)

@app.route('/admin/adverts/approve/<int:advert_id>', methods=['POST'])
@admin_required
def approve_advert(advert_id):
    conn = get_db_connection()
    conn.execute('''UPDATE adverts SET status = 'approved', approved_at = CURRENT_TIMESTAMP WHERE id = ?''', (advert_id,))
    conn.commit()
    conn.close()
    flash('Advert approved!', 'success')
    return redirect(url_for('admin_adverts'))

@app.route('/admin/adverts/reject/<int:advert_id>', methods=['POST'])
@admin_required
def reject_advert(advert_id):
    conn = get_db_connection()
    conn.execute('''UPDATE adverts SET status = 'rejected' WHERE id = ?''', (advert_id,))
    conn.commit()
    conn.close()
    flash('Advert rejected.', 'info')
    return redirect(url_for('admin_adverts'))

@app.route('/my_adverts')
@login_required
def my_adverts():
    conn = get_db_connection()
    adverts = conn.execute('''
        SELECT * FROM adverts WHERE user_id = ? ORDER BY created_at DESC
    ''', (g.user['id'],)).fetchall()
    conn.close()
    return render_template('my_adverts.html', adverts=adverts)

@app.route('/buy_credits')
@login_required
def buy_credits():
    return render_template('buy_credits.html')

@app.route('/paypal_webhook', methods=['POST'])
@login_required
def paypal_webhook():
    data = request.get_json()
    order_id = data.get('orderID')
    credits = int(data.get('credits', 0))
    amount = int(data.get('amount', 0))
    if not order_id or not credits or not amount:
        return jsonify({'success': False, 'error': 'Missing data'}), 400
    # Add credits to user balance and log payment
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (credits, g.user['id']))
        conn.execute('INSERT INTO payments (user_id, amount, payment_id, status) VALUES (?, ?, ?, ?)',
                     (g.user['id'], amount, order_id, 'completed'))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/subscribe_newsletter', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email', '').strip().lower()
    
    if not email or '@' not in email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    try:
        # Check if email already exists
        existing = conn.execute(
            'SELECT id, status FROM newsletter_subscribers WHERE email = ?',
            (email,)
        ).fetchone()
        
        if existing:
            if existing['status'] == 'active':
                flash('You are already subscribed to our newsletter!', 'info')
            else:
                # Reactivate subscription
                conn.execute(
                    '''UPDATE newsletter_subscribers 
                    SET status = 'active', unsubscribed_at = NULL 
                    WHERE email = ?''',
                    (email,)
                )
                flash('Welcome back! Your newsletter subscription has been reactivated.', 'success')
        else:
            # Add new subscriber
            conn.execute(
                'INSERT INTO newsletter_subscribers (email) VALUES (?)',
                (email,)
            )
            flash('Thank you for subscribing to our newsletter!', 'success')
        
        conn.commit()
    except sqlite3.IntegrityError:
        flash('An error occurred. Please try again later.', 'error')
    except Exception as e:
        flash('An unexpected error occurred. Please try again later.', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/unsubscribe_newsletter/<email>')
def unsubscribe_newsletter(email):
    conn = get_db_connection()
    try:
        conn.execute(
            '''UPDATE newsletter_subscribers 
            SET status = 'unsubscribed', unsubscribed_at = CURRENT_TIMESTAMP 
            WHERE email = ?''',
            (email,)
        )
        conn.commit()
        flash('You have been unsubscribed from our newsletter.', 'info')
    except Exception as e:
        flash('An error occurred while processing your request.', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/admin/newsletter')
@admin_required
def admin_newsletter():
    conn = get_db_connection()
    
    # Get filter parameters
    status = request.args.get('status', 'all')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'subscribed_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query_parts = ['SELECT * FROM newsletter_subscribers WHERE 1=1']
    params = []
    
    if status != 'all':
        query_parts.append('AND status = ?')
        params.append(status)
    
    if search:
        query_parts.append('AND (email LIKE ? OR subscribed_at LIKE ? OR unsubscribed_at LIKE ?)')
        search_term = f'%{search}%'
        params.extend([search_term, search_term, search_term])
    
    # Add sorting
    valid_sort_columns = ['email', 'status', 'subscribed_at', 'unsubscribed_at', 'last_email_sent']
    if sort_by not in valid_sort_columns:
        sort_by = 'subscribed_at'
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    query_parts.append(f'ORDER BY {sort_by} {sort_order}')
    
    # Execute query
    subscribers = conn.execute(' '.join(query_parts), params).fetchall()
    
    # Get statistics
    stats = {
        'total': conn.execute('SELECT COUNT(*) as count FROM newsletter_subscribers').fetchone()['count'],
        'active': conn.execute('SELECT COUNT(*) as count FROM newsletter_subscribers WHERE status = "active"').fetchone()['count'],
        'unsubscribed': conn.execute('SELECT COUNT(*) as count FROM newsletter_subscribers WHERE status = "unsubscribed"').fetchone()['count']
    }
    
    conn.close()
    
    return render_template('admin_newsletter.html',
                         subscribers=subscribers,
                         stats=stats,
                         current_status=status,
                         current_search=search,
                         current_sort=sort_by,
                         current_order=sort_order)

@app.route('/admin/newsletter/export')
@admin_required
def export_newsletter_subscribers():
    conn = get_db_connection()
    subscribers = conn.execute('''
        SELECT email, status, subscribed_at, unsubscribed_at, last_email_sent
        FROM newsletter_subscribers
        ORDER BY subscribed_at DESC
    ''').fetchall()
    conn.close()
    
    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Email', 'Status', 'Subscribed At', 'Unsubscribed At', 'Last Email Sent'])
    
    for sub in subscribers:
        writer.writerow([
            sub['email'],
            sub['status'],
            sub['subscribed_at'],
            sub['unsubscribed_at'],
            sub['last_email_sent']
        ])
    
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=newsletter_subscribers.csv'
        }
    )

@app.route('/admin/newsletter/delete/<int:subscriber_id>', methods=['POST'])
@admin_required
def delete_newsletter_subscriber(subscriber_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM newsletter_subscribers WHERE id = ?', (subscriber_id,))
        conn.commit()
        flash('Subscriber deleted successfully.', 'success')
    except Exception as e:
        flash('Error deleting subscriber.', 'error')
    finally:
        conn.close()
    return redirect(url_for('admin_newsletter'))

def send_newsletter_email(recipient_email, subject, content, is_preview=False):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = recipient_email
        msg['Date'] = formatdate(localtime=True)
        
        # Add unsubscribe link
        unsubscribe_url = url_for('unsubscribe_newsletter', email=recipient_email, _external=True)
        footer = f"\n\n---\nTo unsubscribe, click here: {unsubscribe_url}"
        
        # Create both plain text and HTML versions
        text_content = content + footer
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    {content.replace('\n', '<br>')}
                    <hr style="border: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #666; font-size: 12px;">
                        To unsubscribe, <a href="{unsubscribe_url}">click here</a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        if not is_preview:
            # Connect to SMTP server and send
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)
            
            # Update last_email_sent in database
            conn = get_db_connection()
            conn.execute(
                'UPDATE newsletter_subscribers SET last_email_sent = CURRENT_TIMESTAMP WHERE email = ?',
                (recipient_email,)
            )
            conn.commit()
            conn.close()
            
            return True, "Email sent successfully"
        else:
            return True, "Preview generated successfully"
            
    except Exception as e:
        return False, str(e)

@app.route('/admin/newsletter/bulk_action', methods=['POST'])
@admin_required
def bulk_newsletter_action():
    action = request.form.get('action')
    subscriber_ids = request.form.getlist('subscriber_ids[]')
    
    if not subscriber_ids:
        flash('No subscribers selected.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    conn = get_db_connection()
    try:
        if action == 'delete':
            placeholders = ','.join('?' * len(subscriber_ids))
            conn.execute(f'DELETE FROM newsletter_subscribers WHERE id IN ({placeholders})', subscriber_ids)
            flash(f'Successfully deleted {len(subscriber_ids)} subscribers.', 'success')
        elif action == 'unsubscribe':
            placeholders = ','.join('?' * len(subscriber_ids))
            conn.execute(
                f'''UPDATE newsletter_subscribers 
                SET status = 'unsubscribed', unsubscribed_at = CURRENT_TIMESTAMP 
                WHERE id IN ({placeholders})''',
                subscriber_ids
            )
            flash(f'Successfully unsubscribed {len(subscriber_ids)} subscribers.', 'success')
        elif action == 'resubscribe':
            placeholders = ','.join('?' * len(subscriber_ids))
            conn.execute(
                f'''UPDATE newsletter_subscribers 
                SET status = 'active', unsubscribed_at = NULL 
                WHERE id IN ({placeholders})''',
                subscriber_ids
            )
            flash(f'Successfully reactivated {len(subscriber_ids)} subscribers.', 'success')
        
        conn.commit()
    except Exception as e:
        flash(f'Error performing bulk action: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_newsletter'))

@app.route('/admin/newsletter/preview_email', methods=['POST'])
@admin_required
def preview_newsletter_email():
    subject = request.form.get('subject', '').strip()
    content = request.form.get('content', '').strip()
    test_email = request.form.get('test_email', '').strip()
    
    if not subject or not content:
        return jsonify({'success': False, 'error': 'Subject and content are required'})
    
    if not test_email or '@' not in test_email:
        return jsonify({'success': False, 'error': 'Valid test email is required'})
    
    success, message = send_newsletter_email(test_email, subject, content, is_preview=True)
    return jsonify({'success': success, 'message': message})

@app.route('/admin/newsletter/send', methods=['POST'])
@admin_required
def send_newsletter():
    subject = request.form.get('subject', '').strip()
    content = request.form.get('content', '').strip()
    subscriber_ids = request.form.getlist('subscriber_ids[]')
    
    if not subject or not content:
        flash('Subject and content are required.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    if not subscriber_ids:
        flash('No subscribers selected.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    conn = get_db_connection()
    try:
        # Get active subscribers
        placeholders = ','.join('?' * len(subscriber_ids))
        subscribers = conn.execute(
            f'''SELECT email FROM newsletter_subscribers 
            WHERE id IN ({placeholders}) AND status = 'active' ''',
            subscriber_ids
        ).fetchall()
        
        success_count = 0
        error_count = 0
        error_messages = []
        
        for subscriber in subscribers:
            success, message = send_newsletter_email(subscriber['email'], subject, content)
            if success:
                success_count += 1
            else:
                error_count += 1
                error_messages.append(f"{subscriber['email']}: {message}")
        
        if success_count > 0:
            flash(f'Successfully sent newsletter to {success_count} subscribers.', 'success')
        if error_count > 0:
            flash(f'Failed to send to {error_count} subscribers. Check logs for details.', 'error')
            app.logger.error(f'Newsletter sending errors: {json.dumps(error_messages)}')
            
    except Exception as e:
        flash(f'Error sending newsletter: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_newsletter'))

@app.route('/admin/newsletter/templates')
@admin_required
def newsletter_templates():
    conn = get_db_connection()
    templates = conn.execute('SELECT * FROM newsletter_templates ORDER BY name').fetchall()
    conn.close()
    return render_template('newsletter_templates.html', templates=templates)

@app.route('/admin/newsletter/templates/add', methods=['POST'])
@admin_required
def add_newsletter_template():
    name = request.form.get('name', '').strip()
    subject = request.form.get('subject', '').strip()
    content = request.form.get('content', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not subject or not content:
        flash('Name, subject, and content are required.', 'error')
        return redirect(url_for('newsletter_templates'))
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO newsletter_templates (name, subject, content, description)
            VALUES (?, ?, ?, ?)
        ''', (name, subject, content, description))
        conn.commit()
        flash('Template added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('A template with this name already exists.', 'error')
    except Exception as e:
        flash(f'Error adding template: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('newsletter_templates'))

@app.route('/admin/newsletter/templates/<int:template_id>/edit', methods=['POST'])
@admin_required
def edit_newsletter_template(template_id):
    name = request.form.get('name', '').strip()
    subject = request.form.get('subject', '').strip()
    content = request.form.get('content', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not subject or not content:
        flash('Name, subject, and content are required.', 'error')
        return redirect(url_for('newsletter_templates'))
    
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE newsletter_templates 
            SET name = ?, subject = ?, content = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, subject, content, description, template_id))
        conn.commit()
        flash('Template updated successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('A template with this name already exists.', 'error')
    except Exception as e:
        flash(f'Error updating template: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('newsletter_templates'))

@app.route('/admin/newsletter/templates/<int:template_id>/delete', methods=['POST'])
@admin_required
def delete_newsletter_template(template_id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM newsletter_templates WHERE id = ?', (template_id,))
        conn.commit()
        flash('Template deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting template: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('newsletter_templates'))

@app.route('/admin/newsletter/import', methods=['POST'])
@admin_required
def import_subscribers():
    if 'file' not in request.files:
        flash('No file uploaded.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    file = request.files['file']
    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    try:
        # Read CSV file
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Validate required columns
        required_columns = {'email'}
        if not required_columns.issubset(csv_reader.fieldnames):
            flash('CSV must contain an "email" column.', 'error')
            return redirect(url_for('admin_newsletter'))
        
        conn = get_db_connection()
        success_count = 0
        error_count = 0
        error_messages = []
        
        for row in csv_reader:
            email = row['email'].strip().lower()
            if not email or '@' not in email:
                error_count += 1
                error_messages.append(f"Invalid email: {email}")
                continue
            
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO newsletter_subscribers (email)
                    VALUES (?)
                ''', (email,))
                success_count += 1
            except Exception as e:
                error_count += 1
                error_messages.append(f"{email}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        if success_count > 0:
            flash(f'Successfully imported {success_count} subscribers.', 'success')
        if error_count > 0:
            flash(f'Failed to import {error_count} subscribers. Check logs for details.', 'error')
            app.logger.error(f'Subscriber import errors: {json.dumps(error_messages)}')
            
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
    
    return redirect(url_for('admin_newsletter'))

@app.route('/admin/newsletter/templates/<int:template_id>')
@admin_required
def get_template(template_id):
    conn = get_db_connection()
    template = conn.execute('SELECT * FROM newsletter_templates WHERE id = ?', (template_id,)).fetchone()
    conn.close()
    
    if template:
        return jsonify({
            'success': True,
            'template': {
                'name': template['name'],
                'subject': template['subject'],
                'content': template['content']
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Template not found'}), 404

@app.route('/admin/newsletter/schedule', methods=['POST'])
@admin_required
def schedule_newsletter():
    subject = request.form.get('subject', '').strip()
    content = request.form.get('content', '').strip()
    scheduled_for = request.form.get('scheduled_for', '').strip()
    template_id = request.form.get('template_id')
    subscriber_ids = request.form.getlist('subscriber_ids[]')
    
    if not subject or not content or not scheduled_for or not subscriber_ids:
        flash('All fields are required.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    try:
        scheduled_datetime = datetime.datetime.strptime(scheduled_for, '%Y-%m-%dT%H:%M')
        if scheduled_datetime < datetime.datetime.now():
            flash('Scheduled time must be in the future.', 'error')
            return redirect(url_for('admin_newsletter'))
    except ValueError:
        flash('Invalid date/time format.', 'error')
        return redirect(url_for('admin_newsletter'))
    
    conn = get_db_connection()
    try:
        # Create scheduled newsletter
        cursor = conn.execute('''
            INSERT INTO scheduled_newsletters 
            (subject, content, scheduled_for, created_by, template_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (subject, content, scheduled_datetime, g.user['id'], template_id))
        scheduled_id = cursor.lastrowid
        
        # Add recipients
        for subscriber_id in subscriber_ids:
            conn.execute('''
                INSERT INTO scheduled_newsletter_recipients 
                (scheduled_newsletter_id, subscriber_id)
                VALUES (?, ?)
            ''', (scheduled_id, subscriber_id))
        
        conn.commit()
        flash('Newsletter scheduled successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error scheduling newsletter: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin_newsletter'))

@app.route('/admin/newsletter/scheduled')
@admin_required
def scheduled_newsletters():
    conn = get_db_connection()
    scheduled = conn.execute('''
        SELECT sn.*, 
               COUNT(snr.id) as total_recipients,
               COUNT(CASE WHEN snr.status = 'sent' THEN 1 END) as sent_count,
               COUNT(CASE WHEN snr.status = 'failed' THEN 1 END) as failed_count,
               u.username as creator
        FROM scheduled_newsletters sn
        LEFT JOIN scheduled_newsletter_recipients snr ON sn.id = snr.scheduled_newsletter_id
        LEFT JOIN users u ON sn.created_by = u.id
        GROUP BY sn.id
        ORDER BY sn.scheduled_for DESC
    ''').fetchall()
    conn.close()
    return render_template('scheduled_newsletters.html', scheduled=scheduled)

@app.route('/admin/newsletter/scheduled/<int:scheduled_id>/cancel', methods=['POST'])
@admin_required
def cancel_scheduled_newsletter(scheduled_id):
    conn = get_db_connection()
    try:
        # Only allow cancellation of pending newsletters
        conn.execute('''
            UPDATE scheduled_newsletters 
            SET status = 'cancelled' 
            WHERE id = ? AND status = 'pending' AND scheduled_for > CURRENT_TIMESTAMP
        ''', (scheduled_id,))
        conn.commit()
        flash('Newsletter cancelled successfully.', 'success')
    except Exception as e:
        flash(f'Error cancelling newsletter: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('scheduled_newsletters'))

@app.route('/admin/newsletter/scheduled/<int:scheduled_id>')
@admin_required
def view_scheduled_newsletter(scheduled_id):
    conn = get_db_connection()
    newsletter = conn.execute('''
        SELECT sn.*, u.username as creator,
               t.name as template_name
        FROM scheduled_newsletters sn
        LEFT JOIN users u ON sn.created_by = u.id
        LEFT JOIN newsletter_templates t ON sn.template_id = t.id
        WHERE sn.id = ?
    ''', (scheduled_id,)).fetchone()
    
    if not newsletter:
        conn.close()
        flash('Scheduled newsletter not found.', 'error')
        return redirect(url_for('scheduled_newsletters'))
    
    recipients = conn.execute('''
        SELECT snr.*, ns.email
        FROM scheduled_newsletter_recipients snr
        JOIN newsletter_subscribers ns ON snr.subscriber_id = ns.id
        WHERE snr.scheduled_newsletter_id = ?
        ORDER BY snr.status, ns.email
    ''', (scheduled_id,)).fetchall()
    
    conn.close()
    return render_template('view_scheduled_newsletter.html', 
                         newsletter=newsletter, 
                         recipients=recipients)

def send_scheduled_newsletters():
    """Background task to send scheduled newsletters"""
    conn = get_db_connection()
    try:
        # Get pending newsletters that are due
        newsletters = conn.execute('''
            SELECT id, subject, content
            FROM scheduled_newsletters
            WHERE status = 'pending' 
            AND scheduled_for <= CURRENT_TIMESTAMP
        ''').fetchall()
        
        for newsletter in newsletters:
            # Get recipients
            recipients = conn.execute('''
                SELECT snr.id, ns.email
                FROM scheduled_newsletter_recipients snr
                JOIN newsletter_subscribers ns ON snr.subscriber_id = ns.id
                WHERE snr.scheduled_newsletter_id = ?
                AND snr.status = 'pending'
            ''', (newsletter['id'],)).fetchall()
            
            success_count = 0
            error_count = 0
            
            for recipient in recipients:
                try:
                    success, message = send_newsletter_email(
                        recipient['email'],
                        newsletter['subject'],
                        newsletter['content']
                    )
                    
                    if success:
                        conn.execute('''
                            UPDATE scheduled_newsletter_recipients
                            SET status = 'sent', sent_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (recipient['id'],))
                        success_count += 1
                    else:
                        conn.execute('''
                            UPDATE scheduled_newsletter_recipients
                            SET status = 'failed', error_message = ?
                            WHERE id = ?
                        ''', (message, recipient['id']))
                        error_count += 1
                        
                except Exception as e:
                    conn.execute('''
                        UPDATE scheduled_newsletter_recipients
                        SET status = 'failed', error_message = ?
                        WHERE id = ?
                    ''', (str(e), recipient['id']))
                    error_count += 1
            
            # Update newsletter status
            if error_count == 0:
                status = 'completed'
            elif success_count == 0:
                status = 'failed'
            else:
                status = 'partial'
                
            conn.execute('''
                UPDATE scheduled_newsletters
                SET status = ?, sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, newsletter['id']))
            
            conn.commit()
            
    except Exception as e:
        app.logger.error(f'Error in send_scheduled_newsletters: {str(e)}')
    finally:
        conn.close()

# Add a scheduled task to run every minute
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=send_scheduled_newsletters, trigger="interval", minutes=1)
scheduler.start()

# Ensure scheduler shuts down with the app
import atexit
atexit.register(lambda: scheduler.shutdown())

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/success_stories')
def success_stories():
    conn = get_db_connection()
    try:
        # Get approved success stories from reviews
        stories = conn.execute('''
            SELECT name, location, review_text, photo, created_at 
            FROM reviews 
            WHERE status = 'approve' 
            ORDER BY created_at DESC
        ''').fetchall()
        return render_template('success_stories.html', stories=stories)
    finally:
        conn.close()

@app.route('/safety')
def safety():
    return render_template('safety.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        # Basic validation
        if not all([name, email, subject, message]):
            flash('All fields are required.', 'error')
            return redirect(url_for('contact'))
        
        if '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('contact'))
        
        try:
            # Here you would typically:
            # 1. Send an email to your support team
            # 2. Store the message in a database
            # 3. Send an auto-reply to the user
            
            # For now, we'll just flash a success message
            flash('Thank you for your message! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
            
        except Exception as e:
            flash('An error occurred while sending your message. Please try again later.', 'error')
            return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/dating-tips')
def dating_tips():
    return render_template('dating_tips.html')

@app.route('/community-events')
def community_events():
    conn = get_db_connection()
    try:
        # Get upcoming events from the database
        # For now, we'll use placeholder data since we haven't created the events table yet
        events = [
            {
                'title': 'Jewish Singles Mixer',
                'date': '2024-04-15',
                'time': '7:00 PM',
                'location': 'Kosher Restaurant, NYC',
                'description': 'Join us for an evening of meaningful connections in a comfortable setting.',
                'image': url_for('static', filename='events/mixer.jpg')
            },
            {
                'title': 'Shabbat Dinner for Singles',
                'date': '2024-04-20',
                'time': '6:30 PM',
                'location': 'Community Center, Brooklyn',
                'description': 'Experience a traditional Shabbat dinner while meeting other Jewish singles.',
                'image': url_for('static', filename='events/shabbat.jpg')
            },
            {
                'title': 'Speed Dating Event',
                'date': '2024-04-25',
                'time': '8:00 PM',
                'location': 'Modern Cafe, Manhattan',
                'description': 'Meet multiple potential matches in a fun, structured environment.',
                'image': url_for('static', filename='events/speed_dating.jpg')
            }
        ]
        return render_template('community_events.html', events=events)
    finally:
        conn.close()

@app.route('/faq')
def faq():
    faqs = [
        {
            'category': 'Account & Profile',
            'questions': [
                {
                    'question': 'How do I create an account?',
                    'answer': 'Click the "Register" button in the top navigation. You\'ll need to provide a username, password, and some basic information about yourself. After registration, you can complete your profile with more details.'
                },
                {
                    'question': 'Can I change my profile information later?',
                    'answer': 'Yes! You can edit your profile at any time by clicking on your profile picture in the top navigation and selecting "Edit Profile".'
                },
                {
                    'question': 'How do I upload photos?',
                    'answer': 'You can upload photos from your profile page. Click "Edit Profile" and use the photo upload section. We accept JPG, PNG, and GIF files up to 16MB.'
                }
            ]
        },
        {
            'category': 'Matching & Messaging',
            'questions': [
                {
                    'question': 'How does the matching system work?',
                    'answer': 'Our matching system considers your preferences, observance level, and interests to suggest compatible matches. You can also browse profiles and use our search filters to find potential matches.'
                },
                {
                    'question': 'When can I message someone?',
                    'answer': 'You can message any user after you\'ve both liked each other\'s profiles. This mutual match system helps ensure meaningful connections.'
                },
                {
                    'question': 'Is there a limit to how many people I can message?',
                    'answer': 'Free users can message up to 5 matches per day. Premium members enjoy unlimited messaging.'
                }
            ]
        },
        {
            'category': 'Safety & Privacy',
            'questions': [
                {
                    'question': 'How do you protect my privacy?',
                    'answer': 'We take privacy seriously. Your personal information is never shared with other users. You control what information is visible on your profile, and you can block or report any user who makes you uncomfortable.'
                },
                {
                    'question': 'What should I do if I encounter inappropriate behavior?',
                    'answer': 'Use the "Report" button on any profile or message to alert our team. We review all reports promptly and take appropriate action to maintain a safe community.'
                },
                {
                    'question': 'Are the profiles verified?',
                    'answer': 'We encourage users to verify their profiles with a photo ID. Verified profiles are marked with a badge to help you identify authentic users.'
                }
            ]
        },
        {
            'category': 'Events & Community',
            'questions': [
                {
                    'question': 'How do I find local events?',
                    'answer': 'Visit our Community Events page to see upcoming events in your area. You can filter by location, date, and event type.'
                },
                {
                    'question': 'Can I host an event?',
                    'answer': 'Yes! We welcome community members to host events. Contact us through the Community Events page to learn more about hosting opportunities.'
                },
                {
                    'question': 'Are the events kosher?',
                    'answer': 'Yes, all our events are either held at kosher venues or provide kosher food options. We clearly indicate the kosher certification level for each event.'
                }
            ]
        },
        {
            'category': 'Technical Support',
            'questions': [
                {
                    'question': 'I forgot my password. How do I reset it?',
                    'answer': 'Click the "Forgot Password" link on the login page. We\'ll send a password reset link to your registered email address.'
                },
                {
                    'question': 'How do I delete my account?',
                    'answer': 'Go to your profile settings and click "Delete Account". Please note that this action is permanent and cannot be undone.'
                },
                {
                    'question': 'What if I encounter technical issues?',
                    'answer': 'Contact our support team through the Contact page. We typically respond within 24 hours to help resolve any technical problems.'
                }
            ]
        }
    ]
    return render_template('faq.html', faqs=faqs)

@app.route('/blog')
def blog():
    # For now, we'll use placeholder blog posts
    # Later we can create a blog_posts table in the database
    posts = [
        {
            'title': 'Finding Love in the Digital Age: A Jewish Perspective',
            'date': '2024-03-15',
            'author': 'Rabbi Sarah Cohen',
            'excerpt': 'How technology is changing the way Jewish singles connect while maintaining traditional values...',
            'image': url_for('static', filename='blog/digital_love.jpg'),
            'category': 'Dating Tips'
        },
        {
            'title': 'The Importance of Shared Values in Jewish Dating',
            'date': '2024-03-10',
            'author': 'Dr. David Levy',
            'excerpt': 'Why aligning on core Jewish values is crucial for building lasting relationships...',
            'image': url_for('static', filename='blog/shared_values.jpg'),
            'category': 'Relationships'
        },
        {
            'title': 'Navigating Modern Dating as an Observant Jew',
            'date': '2024-03-05',
            'author': 'Miriam Goldstein',
            'excerpt': 'Practical advice for maintaining religious observance while dating in today\'s world...',
            'image': url_for('static', filename='blog/modern_dating.jpg'),
            'category': 'Lifestyle'
        }
    ]
    return render_template('blog.html', posts=posts)

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/cookies')
def cookies():
    return render_template('cookies.html')

@app.route('/accessibility')
def accessibility():
    return render_template('accessibility.html')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)