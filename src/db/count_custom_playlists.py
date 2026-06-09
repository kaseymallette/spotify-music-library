import sqlite3
import os

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT seed_song, seed_artist FROM custom_playlists;")
playlists = cursor.fetchall()

print(f"Number of custom playlists: {len(playlists)}")
for playlist in playlists:
    print(f'  - "{playlist[0]}" by {playlist[1]}')

conn.close()
