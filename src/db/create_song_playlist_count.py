import sqlite3
import pandas as pd
import os

# Get the root directory (two levels up from src/db/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Load playlists and tracks
df_playlists = pd.read_sql(
    "SELECT Artist, Song, playlist_name FROM playlists",
    conn
)
df_tracks = pd.read_sql(
    "SELECT DISTINCT Track_Key FROM tracks",
    conn
)

# Normalize playlist song names the same way as create_tracks.py
df_playlists['Song_Normalized'] = df_playlists['Song'].str.replace(r'\s*\(feat\.\s*[^)]*\)', '', regex=True, case=False)
df_playlists['Song_Normalized'] = df_playlists['Song_Normalized'].str.replace(r'\s*\(with\s*[^)]*\)', '', regex=True, case=False)
df_playlists['Song_Normalized'] = df_playlists['Song_Normalized'].str.replace(r'\s*\(ft\.\s*[^)]*\)', '', regex=True, case=False)
df_playlists['Song_Normalized'] = df_playlists['Song_Normalized'].str.replace(r'[?!\.]+$', '', regex=True)
df_playlists['Song_Normalized'] = df_playlists['Song_Normalized'].str.replace(r'\s*-\s*Edit\s*$', '', regex=True, case=False)
df_playlists['Song_Normalized'] = df_playlists['Song_Normalized'].str.strip()
df_playlists['Track_Key_Normalized'] = df_playlists['Artist'] + '|' + df_playlists['Song_Normalized']

# Count playlist appearances by normalized Track_Key
df_counts = (
    df_playlists
    .groupby('Track_Key_Normalized')['playlist_name']
    .nunique()
    .reset_index(name='playlist_count')
)

# Ensure output includes every unique track from tracks table
df = df_tracks.merge(
    df_counts,
    left_on='Track_Key',
    right_on='Track_Key_Normalized',
    how='left'
)
df = df.drop(columns=['Track_Key_Normalized'])
df['playlist_count'] = df['playlist_count'].fillna(0).astype(int)
df = df.sort_values('playlist_count', ascending=False)

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
