import os # Import os module
from werkzeug.utils import secure_filename # Import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
import sqlite3
import hashlib
from functools import wraps
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_long_and_random_secret_key_for_production_never_share' # Change this!

DATABASE = 'database.db'

# --- NEW: File Upload Configuration ---
UPLOAD_FOLDER = 'static/profile_pics' # Where to save uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Allowed image extensions

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload size

# Create the upload folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    ''')
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
    conn.commit()
    conn.close()

# Initialize the database when the app starts
with app.app_context():
    init_db()



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

# --- ROUTES ---

@app.route('/')
def index():
    if g.user:
        # UPDATED: Added link to 'My Likes'
        return f"Hello, {g.user['username']}! Welcome to the Jewish Dating App. " \
               f"<br><a href='/profile'>My Profile</a> | <a href='/browse'>Browse Profiles</a> | <a href='/search'>Search Profiles</a> | <a href='/my_likes'>My Likes</a> | <a href='/messages'>Messages</a> | <a href='/logout'>Logout</a>"
    return "Welcome to the Jewish Dating App! <br><a href='/register'>Register Here</a> | <a href='/login'>Login Here</a>"


@app.route('/register', methods=('GET', 'POST'))
def register():
    if g.user:
        flash('You are already logged in.', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        conn = get_db_connection()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            error = f"User {username} is already registered."

        if error is None:
            hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, hashed_password))
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
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

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
                         shabbat_observance, synagogue_affiliation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (user_id, age, bio,
                     observance_level, kosher_level,
                     shabbat_observance, synagogue_affiliation)
                )
                flash('Profile created successfully!', 'success')
            conn.commit()
            conn.close()
            return redirect(url_for('profile'))

        flash(error, 'error')
        conn.close()

    profile_data = conn.execute(
        'SELECT age, bio, observance_level, kosher_level, shabbat_observance, synagogue_affiliation FROM profiles WHERE user_id = ?', (user_id,)
    ).fetchone()
    conn.close()

    return render_template('profile.html', profile=profile_data)


# --- BROWSE PROFILES ROUTE (MODIFIED for likes) ---
@app.route('/browse')
@login_required
def browse_profiles():
    conn = get_db_connection()
    current_user_id = g.user['id']

    profiles_data = conn.execute(
        '''SELECT p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation,
                  u.username, u.id as user_id,
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
        'u.username, u.id as user_id, ',
        'EXISTS(SELECT 1 FROM likes WHERE liker_id = ? AND liked_id = u.id) AS is_liked_by_me ', # Add is_liked_by_me here too
        'FROM profiles p JOIN users u ON p.user_id = u.id '
        'WHERE u.id != ? '
    ]
    params = [current_user_id, current_user_id] # current_user_id repeated for the new EXISTS subquery

    if min_age is not None:
        query_parts.append('AND p.age >= ? ')
        params.append(min_age)
    if max_age is not None:
        query_parts.append('AND p.age <= ? ')
        params.append(max_age)

    if min_age is not None and max_age is not None and min_age > max_age:
        flash('Minimum age cannot be greater than maximum age.', 'error')

    if observance_level and observance_level != '': # Changed 'Any' to '' for the search form
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
        '''SELECT u.id AS user_id, u.username, p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation
           FROM likes l
           JOIN users u ON l.liked_id = u.id
           JOIN profiles p ON u.id = p.user_id
           WHERE l.liker_id = ?
           ORDER BY u.username ASC''',
        (current_user_id,)
    ).fetchall()

    # Profiles that have liked me (current_user)
    liked_me = conn.execute(
        '''SELECT u.id AS user_id, u.username, p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation
           FROM likes l
           JOIN users u ON l.liker_id = u.id
           JOIN profiles p ON u.id = p.user_id
           WHERE l.liked_id = ?
           ORDER BY u.username ASC''',
        (current_user_id,)
    ).fetchall()
    
    # Check for mutual likes (matches!)
    # A mutual like occurs when liker_id (A) liked liked_id (B), AND liker_id (B) liked liked_id (A)
    # We can get this by finding common users between liked_by_me and liked_me lists.
    # Or, with a more direct SQL query:
    mutual_likes = conn.execute(
        '''SELECT u.id AS user_id, u.username, p.age, p.bio, p.observance_level, p.kosher_level, p.shabbat_observance, p.synagogue_affiliation
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


if __name__ == '__main__':
    app.run(debug=True)