##Jewish Dating App
Welcome to the Jewish Dating App! This application provides a platform for Jewish individuals to connect, create profiles, browse other users, send messages, and express interest through a "liking" system.

Table of Contents

Features
Technologies Used
Setup Instructions
Prerequisites
Installation
Running the Application
Database Schema
File Structure
Usage
Contributing
License
Features
This application includes the following key features:

User Registration & Authentication: Secure user registration with hashed passwords and a robust login/logout system.
User Profiles: Users can create and update detailed profiles including:
Age
Bio ("About Me")
Observance Level (e.g., Orthodox, Conservative, Reform, etc.)
Kosher Level (e.g., Glatt Kosher, Kosher, Vegetarian, etc.)
Shabbat Observance (e.g., Observant, Partially Observant, Not Observant)
Synagogue Affiliation
Profile Picture Upload: Users can upload a profile picture.
Browse Profiles: View other users' profiles, excluding your own.
Search Profiles: Filter and search for profiles based on age range, observance level, kosher level, Shabbat observance, and keywords in bio or synagogue affiliation.
Liking System:
"Like" other users' profiles.
"Unlike" profiles you've previously liked.
"My Likes" Dashboard: See who you've liked, who has liked you, and crucially, your mutual matches!
Direct Messaging: Engage in private conversations with other users.
Flash Messages: Provides user feedback for actions (e.g., "Registration successful!", "Profile updated!").
Login Required Decorator: Ensures that certain routes are only accessible to logged-in users.
Technologies Used
Flask: A micro web framework for Python.
SQLite3: A C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine. Used for the application's database.
HTML/CSS: For structuring and styling the web pages.
Python: The primary programming language.
Werkzeug: A WSGI utility library for Python (used for secure_filename).
Hashlib: For secure password hashing.
Os: For interacting with the operating system (e.g., creating directories for uploads).
Setup Instructions
Follow these steps to get the Jewish Dating App up and running on your local machine.

Prerequisites
Python 3.x: Ensure you have Python 3 installed. You can download it from python.org.
Pip: Python's package installer, usually comes with Python.
Installation
Clone the Repository:
If this project is in a Git repository, clone it to your local machine:

Bash

git clone <repository_url>
cd jewish_dating_app
If not, simply navigate to the directory where you've saved the project files.

Create a Virtual Environment:
It's highly recommended to use a virtual environment to manage dependencies.

Bash

python -m venv venv
Activate the Virtual Environment:

On Windows:
Bash

.\venv\Scripts\activate
On macOS/Linux:
Bash

source venv/bin/activate
Install Dependencies:
With your virtual environment activated, install the required Python packages:

Bash

pip install Flask Werkzeug
(Note: sqlite3, hashlib, functools, datetime, and os are standard Python libraries and don't need separate installation via pip.)

Running the Application
Set the Flask App Environment Variable:
Tell Flask where your application file is.

On Windows:
Bash

set FLASK_APP=app.py
On macOS/Linux:
Bash

export FLASK_APP=app.py
Run the Flask Application:

Bash

flask run
You should see output similar to this:

 * Serving Flask app 'app.py'
 * Debug mode: on
INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
Access the Application:
Open your web browser and navigate to http://127.0.0.1:5000 (or the address shown in your terminal).

Database Schema
The application uses an SQLite database with the following tables:

users: Stores user authentication details.

id (INTEGER PRIMARY KEY AUTOINCREMENT)
username (TEXT UNIQUE NOT NULL)
password (TEXT NOT NULL - stores SHA256 hash)
profiles: Stores detailed user profile information.

id (INTEGER PRIMARY KEY AUTOINCREMENT)
user_id (INTEGER UNIQUE NOT NULL, FOREIGN KEY to users.id)
age (INTEGER)
bio (TEXT)
observance_level (TEXT)
kosher_level (TEXT)
shabbat_observance (TEXT)
synagogue_affiliation (TEXT)
profile_picture (TEXT - stores filename of the uploaded picture)
messages: Stores direct messages between users.

id (INTEGER PRIMARY KEY AUTOINCREMENT)
sender_id (INTEGER NOT NULL, FOREIGN KEY to users.id)
receiver_id (INTEGER NOT NULL, FOREIGN KEY to users.id)
content (TEXT NOT NULL)
timestamp (DATETIME DEFAULT CURRENT_TIMESTAMP)
likes: Records "likes" between users.

id (INTEGER PRIMARY KEY AUTOINCREMENT)
liker_id (INTEGER NOT NULL, FOREIGN KEY to users.id)
liked_id (INTEGER NOT NULL, FOREIGN KEY to users.id)
timestamp (DATETIME DEFAULT CURRENT_TIMESTAMP)
UNIQUE(liker_id, liked_id) (Ensures a user can only like another user once)
File Structure
jewish_dating_app/
├── venv/                       # Python virtual environment
├── static/                     # Static files (CSS, JS, images)
│   └── profile_pics/           # Uploaded user profile pictures will be stored here
│       └── <user_id>_<timestamp>.<ext> # Example: 1_20240521183000.jpg
├── templates/                  # HTML Jinja2 templates
│   ├── base.html               # Base template for consistent layout
│   ├── register.html
│   ├── login.html
│   ├── profile.html            # For logged-in user's own profile management
│   ├── view_profile.html       # For viewing other users' profiles
│   ├── browse_profiles.html    # Displaying profiles for Browse
│   ├── search_profiles.html    # Displaying search results
│   ├── messages_overview.html  # List of conversations
│   ├── conversation.html       # Individual message thread
│   └── my_likes.html           # My Likes, Liked Me, Mutual Matches
├── app.py                      # Main Flask application file
├── database.db                 # SQLite database file (created on first run)
├── README.md                   # This file
└── .flaskenv                   # (Optional) For setting FLASK_APP and FLASK_DEBUG
Usage
Register: Create a new account with a unique username and password.
Login: Access your account using your credentials.
My Profile: After logging in, navigate to /profile to create or update your dating profile. Fill in your age, bio, observance levels, and upload a profile picture.
Browse Profiles: Visit /browse to see other users' profiles.
Search Profiles: Use /search to find specific profiles based on criteria.
Like/Unlike: On a user's profile or in browse/search results, you can like or unlike them.
My Likes: Go to /my_likes to manage your likes and see your matches.
Messages: Start a conversation from a user's profile, or view existing chats on /messages.
Contributing
Contributions are welcome! If you have suggestions for improvements or new features, feel free to fork the repository and submit a pull request, or open an issue.

License
This project is open-source and available under the MIT License.
