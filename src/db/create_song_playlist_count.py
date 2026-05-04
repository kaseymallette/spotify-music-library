import sqlite3
import pandas as pd
import os

# Get the root directory (two levels up from src/db/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Query to count how many playlists each song (Track_Key) appears in and get Track_ID
df = pd.read_sql("""
    SELECT p.Track_Key,
           t.Track_ID,
           COUNT(DISTINCT p.playlist_name) as playlist_count
    FROM playlists p
    JOIN tracks t ON p.Track_Key = t.Track_Key
    GROUP BY p.Track_Key, t.Track_ID
    ORDER BY playlist_count DESC
""", conn)

# Create the song_playlist_count table
df.to_sql('song_playlist_count', conn, if_exists='replace', index=False)

# Display stats
total_unique_songs = len(df)
songs_in_multiple_playlists = len(df[df['playlist_count'] > 1])
max_playlist_count = df['playlist_count'].max()

print(f"Total unique songs: {total_unique_songs}")
print(f"Songs in multiple playlists: {songs_in_multiple_playlists}")
print(f"Maximum playlists per song: {max_playlist_count}")
print("Song playlist count table created successfully.")

conn.close()
