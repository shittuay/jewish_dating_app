# Jewish Dating App

Welcome to the **Jewish Dating App**! This application provides a platform for Jewish individuals to connect, create profiles, browse other users, send messages, and express interest through a "liking" system.

---

## Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [Database Schema](#database-schema)
- [File Structure](#file-structure)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **User Registration & Authentication:** Secure user registration with hashed passwords and login/logout.
- **User Profiles:** Users can create and update profiles with:
  - Age
  - Bio ("About Me")
  - Observance Level (e.g., Orthodox, Conservative, Reform, etc.)
  - Kosher Level (e.g., Glatt Kosher, Kosher, Vegetarian, etc.)
  - Shabbat Observance (e.g., Observant, Partially Observant, Not Observant)
  - Synagogue Affiliation
- **Profile Picture Upload:** Users can upload a profile picture.
- **Browse & Search Profiles:** View and filter other users’ profiles based on multiple criteria.
- **Liking System:**
  - "Like" or "Unlike" other users’ profiles.
  - "My Likes" dashboard to see who you’ve liked, who liked you, and mutual matches.
- **Direct Messaging:** Private conversations between users.
- **Flash Messages:** User feedback for actions (e.g., registration success, profile updated).
- **Login Required Decorator:** Ensures certain routes are only accessible to logged-in users.

---

## Technologies Used

- **Flask:** Python web framework
- **SQLite3:** Lightweight SQL database
- **HTML/CSS:** Web page structure and styling
- **Python:** Main programming language
- **Werkzeug:** WSGI utility library (for secure_filename)
- **Hashlib:** Secure password hashing
- **os:** For file and directory operations

---

## Setup Instructions

### Prerequisites

- **Python 3.x:** [Download here](https://www.python.org/downloads/)
- **pip:** Usually comes with Python

### Installation

1. **Clone the Repository**
   ```bash
   git clone <repository_url>
   cd jewish_dating_app
   ```
   If you don’t use git, simply navigate to the directory where you’ve saved the project files.

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the Virtual Environment**

   - On Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install Dependencies**
   ```bash
   pip install Flask Werkzeug
   ```
   > Note: `sqlite3`, `hashlib`, `functools`, `datetime`, and `os` are standard Python libraries and don’t need separate installation.

---

### Running the Application

1. **Set the Flask App Environment Variable**

   - On Windows:
     ```bash
     set FLASK_APP=app.py
     ```
   - On macOS/Linux:
     ```bash
     export FLASK_APP=app.py
     ```

2. **Run the Flask Application**
   ```bash
   flask run
   ```

   You should see output similar to:
   ```
    * Serving Flask app 'app.py'
    * Debug mode: on
    * Running on http://127.0.0.1:5000
   ```

3. **Access the Application**

   Open your browser and go to [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## Database Schema

The app uses an SQLite database with these tables:

### users
| Column    | Type    | Description                        |
|-----------|---------|------------------------------------|
| id        | INTEGER | PRIMARY KEY AUTOINCREMENT          |
| username  | TEXT    | UNIQUE, NOT NULL                   |
| password  | TEXT    | NOT NULL (SHA256 hash)             |

### profiles
| Column                | Type    | Description                                  |
|-----------------------|---------|----------------------------------------------|
| id                    | INTEGER | PRIMARY KEY AUTOINCREMENT                    |
| user_id               | INTEGER | UNIQUE, NOT NULL, FOREIGN KEY to users.id    |
| age                   | INTEGER |                                              |
| bio                   | TEXT    |                                              |
| observance_level      | TEXT    |                                              |
| kosher_level          | TEXT    |                                              |
| shabbat_observance    | TEXT    |                                              |
| synagogue_affiliation | TEXT    |                                              |
| profile_picture       | TEXT    | Filename of uploaded picture                 |

### messages
| Column     | Type    | Description                                  |
|------------|---------|----------------------------------------------|
| id         | INTEGER | PRIMARY KEY AUTOINCREMENT                    |
| sender_id  | INTEGER | NOT NULL, FOREIGN KEY to users.id            |
| receiver_id| INTEGER | NOT NULL, FOREIGN KEY to users.id            |
| content    | TEXT    | NOT NULL                                     |
| timestamp  | DATETIME| DEFAULT CURRENT_TIMESTAMP                    |

### likes
| Column    | Type    | Description                                  |
|-----------|---------|----------------------------------------------|
| id        | INTEGER | PRIMARY KEY AUTOINCREMENT                    |
| liker_id  | INTEGER | NOT NULL, FOREIGN KEY to users.id            |
| liked_id  | INTEGER | NOT NULL, FOREIGN KEY to users.id            |
| timestamp | DATETIME| DEFAULT CURRENT_TIMESTAMP                    |
| UNIQUE(liker_id, liked_id) |        | Ensures user can only like another once  |

---

## File Structure

```
jewish_dating_app/
├── venv/                       # Python virtual environment
├── static/                     # Static files (CSS, JS, images)
│   └── profile_pics/           # Uploaded user profile pictures
│       └── <user_id>_<timestamp>.<ext>
├── templates/                  # Jinja2 HTML templates
│   ├── base.html
│   ├── register.html
│   ├── login.html
│   ├── profile.html
│   ├── view_profile.html
│   ├── browse_profiles.html
│   ├── search_profiles.html
│   ├── messages_overview.html
│   ├── conversation.html
│   └── my_likes.html
├── app.py                      # Main Flask app
├── database.db                 # SQLite database (created on first run)
├── README.md                   # This file
└── .flaskenv                   # (Optional) Flask env variables
```

---

## Usage

- **Register:** Create a new account with a unique username and password.
- **Login:** Access your account.
- **My Profile:** Go to `/profile` to create or update your dating profile.
- **Browse Profiles:** Visit `/browse` to see other users’ profiles.
- **Search Profiles:** Use `/search` to find profiles based on criteria.
- **Like/Unlike:** Like or unlike users from their profile or in browse/search results.
- **My Likes:** Visit `/my_likes` to manage likes and see your matches.
- **Messages:** Start a conversation from a user’s profile or view chats at `/messages`.

---

## Contributing

Contributions are welcome! If you have suggestions or new features, feel free to fork the repository and submit a pull request, or open an issue.

---

## License

This project is open-source and available under the [MIT License](LICENSE).

---

Let me know if you want further customizations!
