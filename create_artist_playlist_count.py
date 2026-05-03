import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('spotify_music_library.db')

# Query to count how many playlists each artist appears in
df = pd.read_sql("""
    SELECT Artist,
           COUNT(DISTINCT playlist_name) as playlist_count
    FROM playlists
    GROUP BY Artist
    ORDER BY playlist_count DESC
""", conn)

# Create the artist_playlist_count table
df.to_sql('artist_playlist_count', conn, if_exists='replace', index=False)

# Display stats
total_unique_artists = len(df)
artists_in_multiple_playlists = len(df[df['playlist_count'] > 1])
max_playlist_count = df['playlist_count'].max()

print(f"Total unique artists: {total_unique_artists}")
print(f"Artists in multiple playlists: {artists_in_multiple_playlists}")
print(f"Maximum playlists per artist: {max_playlist_count}")
print("Artist playlist count table created successfully.")

conn.close()
