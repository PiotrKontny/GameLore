# GameLore – Web Application for Exploring Video Game Storylines

GameLore is a web application that allows users to explore storylines of selected video games. The system collects game metadata and story content from external sources (such as Wikipedia and MobyGames), stores them in a local database, and presents them through 
a searchable catalogue. For each supported title, users can read the full plot, generate their summaries, rate games and manage their personal library. An integrated AI module also provides a chatbot that answers user questions about a chosen game.

The application uses:
- **Django** for the backend
- **React** for the frontend
- **Django REST Framework** for communication between backend and frontend via a REST API
- **MySQL** as the database engine  
- **NLP models** for plot summarization  
- **LLM-based chatbot** for interactive exploration of game narratives

---

## Features
- **User registration and login** – Account creation, authentication, and secure session handling  
- **User profile management** – Editing personal data and uploading a profile picture  
- **Game catalogue browsing** – Searching and viewing detailed information about supported games  
- **Automated data acquisition** – Fetching game metadata and story content from external sources (e.g., Wikipedia, MobyGames)  
- **Plot processing and summarization** – Storing full plot texts and generating summaries using NLP models  
- **AI-powered chatbot** – Answering user questions about a selected game's narrative
- **User activity history** – Tracking recently viewed games for quick access  
- **Game rating system** – Allowing users to rate games and manage their personal library  
- **Administrator panel** – Managing users and games


---

## Installation and Local Setup

### 1. Clone the repository
    git clone https://github.com/PiotrKontny/GameLore.git
    cd GameLore
### 2. Create a virtual environment
    python -m venv myenv
    myenv\Scripts\activate       # Windows
    source myenv/bin/activate    # Linux/Mac 
### 3. Install backend dependencies
    pip install -r requirements.txt
### 4. Install frontend dependencies
    cd frontend
    npm install
---

## 4. Configure MySQL Database

### a) Install MySQL  
Download MySQL Server 8.0.x:  
https://dev.mysql.com/downloads/installer/

### b) Create the database
    CREATE DATABASE gamelore

### c) Create all tables
```sql
USE gamelore;

CREATE TABLE Users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    user_password VARCHAR(128) NOT NULL,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    profile_picture VARCHAR(500) DEFAULT 'profile_pictures/default_user.png',
    is_admin BOOLEAN DEFAULT FALSE
);

CREATE TABLE Games (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    release_date VARCHAR(255),
    genre VARCHAR(100),
    studio TEXT,
    score DECIMAL(3,1),
    cover_image VARCHAR(500),
    mobygames_url VARCHAR(500),
    wikipedia_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE GamePlots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    game_id BIGINT NOT NULL,
    full_plot LONGTEXT,
    summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
);

CREATE TABLE UserHistory (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_id BIGINT NOT NULL,
    viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
);

CREATE TABLE ChatBot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_id BIGINT NOT NULL,
    question LONGTEXT NOT NULL,
    answer LONGTEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
);

CREATE TABLE UserRatings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    game_id BIGINT NOT NULL,
    rating INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE,
    UNIQUE (user_id, game_id)
);
```

### c) Create all tables
Modify ```DATABASES``` in ```GameLore/settings.py``` if your MySQL credentials differ. By default the user and password are both set to "root".

### e) Apply migrations
    python manage.py makemigrations
    python manage.py migrate

### g) Run the server
    python manage.py runserver

### h) Open the app in browser:
http://localhost:8000/

---

## Technologies Used
- Python 3.12
- Django 5.x
- React 19.x
- MySQL 8.x
- HuggingFace Transformers (summarization)
- LLM-based chatbot
- BeautifulSoup (external data fetching)
- venv (virtual environment)

---

## Project Structure
- `app/` – Core backend application module  
    - `models.py` – Definitions of all database models  
    - `serializers.py` – Converters between Django models and JSON (Django REST Framework)  
    - `utils.py` – Utility functions (fetching external data, processing text, supporting NLP operations)  
    - `urls.py` – URL routing for the backend API  
    - `views.py` – API endpoints and backend logic  

- `frontend/` – React frontend application
    - `public/` – Static assets (base `index.html`)  
    - `src/` – All React components, pages, hooks, and logic  
        - `components/` – Reusable UI components (Navbar, search components, layout elements)  
        - `pages/` – Main application views (Home, Explore, Game Details, Login, Profile, Admin pages, etc.)  
        - `utils/` – Helper utilities such as global navigation handling and fetch helpers  
        - `App.js` – Main React component responsible for routing, page structure, and navigation handling  
        - `index.js` – Application entry point; mounts React app into the DOM  
    - `static/` – Static output directory used by Webpack during bundling (not edited manually)  
        - `css/` – Stylesheets generated by the frontend  
        - `frontend/` – Auto-generated build folder containing production-ready assets  
            - `index.html` – Compiled HTML template served by Django  
            - `main.js` – Bundled JavaScript output generated by Webpack (not manually modified)  
    - `package.json` – NPM package configuration, dependencies, and scripts  
    - `package-lock.json` – Dependency lockfile generated by npm  
    - `babel.config.json` – Babel configuration (transpiles JSX/modern JS into browser-compatible code)  
    - `webpack.config.js` – Webpack configuration (bundling, loaders, dev server, asset handling)

- `gamelore/` – Main Django project configuration  
    - `settings.py` – Global configuration (database settings, installed apps, middleware, static/media files)  
    - `urls.py` – Root URL routing for the backend  
    - `wsgi.py` – WSGI entry point for production servers  
    - `asgi.py` – ASGI entry point for async-capable servers  

- `media/` – Directory for uploaded or downloaded content  
    - `game_icons/` – Downloaded game cover images  
    - `icons/` – Additional icons
    - `profile_pictures/` – User profile pictures  
        - `default_user.png` – Default profile picture  
    - `results/` – Images used for search results display  
        - `default_icon.png` – Default placeholder icon if a game lacks official artwork  

- `manage.py` – Django command-line tool for migrations, server startup, and project administration  
- `requirements.txt` – List of Python backend dependencies  
- `.gitignore` – Specifies which files and directories are excluded from version control  
- `README.md` – Project documentation

---

## Development Environment
- Python 3.12
- Django 5.2.6 or newer
- React 19.2.0 or newer
- MySQL 8.0.41 or newer
- venv
- Git

---

## Authors

Piotr Kontny

