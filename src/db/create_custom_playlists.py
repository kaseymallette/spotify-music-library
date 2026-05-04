import sqlite3
import os
from datetime import datetime

# Get the root directory (two levels up from src/db/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create custom_playlists table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_name TEXT NOT NULL,
        seed_song TEXT NOT NULL,
        seed_artist TEXT NOT NULL,
        year_range INTEGER,
        target_size INTEGER NOT NULL,
        created_date TEXT NOT NULL,
        csv_path TEXT
    )
''')

# Create custom_playlist_songs table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_playlist_songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL,
        track_number INTEGER NOT NULL,
        track_key TEXT NOT NULL,
        track_id TEXT NOT NULL,
        song TEXT NOT NULL,
        artist TEXT NOT NULL,
        album TEXT,
        year INTEGER,
        bpm REAL,
        valence REAL,
        dance REAL,
        energy REAL,
        acoustic REAL,
        loud_db REAL,
        distance REAL,
        popularity INTEGER,
        FOREIGN KEY (playlist_id) REFERENCES custom_playlists(id) ON DELETE CASCADE
    )
''')

# Create index for faster queries
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_custom_playlist_songs_playlist_id 
    ON custom_playlist_songs(playlist_id)
''')

conn.commit()
conn.close()

print("Custom playlists tables created successfully.")
