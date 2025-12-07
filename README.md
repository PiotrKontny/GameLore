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

- **User authentication system** - Registration, login, JWT-based authentication, and secure session handling  
- **User profile management** - Updating username, changing password, and uploading a custom profile picture  
- **Game catalogue browsing** - Viewing all games stored in the database, searching by title, filtering by genre, and sorting results  
- **External game search** - Finding games not present in the local database using automated web scraping (MobyGames)  
- **Automated data acquisition** - Fetching game metadata from MobyGames and Wikipedia, including support for DLCs, special editions, compilations, and games without storyline data  
- **Full plot extraction** - Parsing and cleaning storyline sections from Wikipedia or fallback descriptions from MobyGames, stored in structured markdown format  
- **Plot summarization (NLP)** - Generating concise storyline summaries using a Hugging Face Transformer model  
- **AI-powered chatbot** - Interactive Q&A module using an LLM via OpenRouter.ai, answering questions about the selected game’s narrative  
- **User activity history** - Tracking all visited game pages with search, sorting, and deletion options  
- **Chat history management** - Saving all chatbot conversations per game, with the ability to revisit or delete them at any time  
- **Game rating system** - Allowing users to rate games from 1-10 and displaying overall user rating statistics  
- **Administrator panel** - Managing users and games, editing game scores, deleting entries, and re-scraping game data with automatic summary regeneration  



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

### a) Install Node.js
Download Node.js using the link below. Make sure that npm is set to being added to PATH in the instalation.
https://nodejs.org/en/download

### b)
    cd frontend
    npm install

### 5. Install Playwright browser
    playwright install chromium
    
---

## 6. Configure MySQL Database

### a) Install MySQL  
Download MySQL Server 8.0.x:  
https://dev.mysql.com/downloads/installer/

### b) Create the database
    CREATE DATABASE gamelore CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

### c) Create all tables
```sql
USE gamelore;

CREATE TABLE Users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    user_password VARCHAR(255) NOT NULL,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    profile_picture VARCHAR(500) DEFAULT 'profile_pictures/default_user.png',
    is_admin TINYINT(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE Games (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    release_date VARCHAR(255),
    genre VARCHAR(100),
    studio TEXT,
    score DECIMAL(3,1),
    cover_image VARCHAR(500),
    mobygames_url VARCHAR(500),
    wikipedia_url VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE GamePlots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    full_plot LONGTEXT,
    summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE UserHistory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    game_id INT NOT NULL,
    viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE UserRatings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    game_id INT NOT NULL,
    rating INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE,
    UNIQUE (user_id, game_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ChatBot (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    game_id INT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES Games(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
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

### 7. OpenRouter.ai configuration

### a) Create .env file
In the main project folder create a file called ```.env```

### b) Obtain OpenRouter.ai API Key
Go to https://openrouter.ai/ and create an account. Next go to the Keys tab and Create a new API Key. Once you do that, copy the API Key which you have obtained and paste it into the created ```.env``` file.

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
- `app/` - Core backend application module  
    - `models.py` - Definitions of all database models  
    - `serializers.py` - Converters between Django models and JSON (Django REST Framework)  
    - `utils.py` - Utility functions (fetching external data, processing text, supporting NLP operations)  
    - `urls.py` - URL routing for the backend API  
    - `views.py` - API endpoints and backend logic  

- `frontend/` - React frontend application
    - `public/` - Static assets (base `index.html`)  
    - `src/` - All React components, pages, hooks, and logic  
        - `components/` - Reusable UI components (Navbar, search components, layout elements)  
        - `pages/` - Main application views (Home, Explore, Game Details, Login, Profile, Admin pages, etc.)  
        - `utils/` - Helper utilities such as global navigation handling and fetch helpers  
        - `App.js` - Main React component responsible for routing, page structure, and navigation handling  
        - `index.js` - Application entry point; mounts React app into the DOM  
    - `static/` - Static output directory used by Webpack during bundling (not edited manually)  
        - `css/` - Stylesheets generated by the frontend  
        - `frontend/` - Auto-generated build folder containing production-ready assets  
            - `index.html` - Compiled HTML template served by Django  
            - `main.js` - Bundled JavaScript output generated by Webpack (not manually modified)  
    - `package.json` - NPM package configuration, dependencies, and scripts  
    - `package-lock.json` - Dependency lockfile generated by npm  
    - `babel.config.json` - Babel configuration (transpiles JSX/modern JS into browser-compatible code)  
    - `webpack.config.js` - Webpack configuration (bundling, loaders, dev server, asset handling)

- `gamelore/` - Main Django project configuration  
    - `settings.py` - Global configuration (database settings, installed apps, middleware, static/media files)  
    - `urls.py` - Root URL routing for the backend  
    - `wsgi.py` - WSGI entry point for production servers  
    - `asgi.py` - ASGI entry point for async-capable servers  

- `media/` - Directory for uploaded or downloaded content  
    - `game_icons/` - Downloaded game cover images  
    - `icons/` - Additional icons
    - `profile_pictures/` - User profile pictures  
        - `default_user.png` - Default profile picture  
    - `results/` - Images used for search results display  
        - `default_icon.png` - Default placeholder icon if a game lacks official artwork  

- `manage.py` - Django command-line tool for migrations, server startup, and project administration  
- `requirements.txt` - List of Python backend dependencies  
- `.gitignore` - Specifies which files and directories are excluded from version control  
- `README.md` - Project documentation

---

## Development Environment
- Python 3.12
- Django 5.2.6 or newer
- React 19.2.0 or newer
- MySQL 8.0.41 or newer
- venv
- Git

---

## Additional information

The app does not have a function to make a user into admin. In order to do that one must use MySQL and type this with the chosen username:
```sql
UPDATE Users SET is_admin = 1 WHERE username = '<username>';
```

## Authors

Piotr Kontny

