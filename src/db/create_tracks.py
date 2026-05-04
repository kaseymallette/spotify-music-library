import sqlite3
import pandas as pd
import os

# Get the root directory (two levels up from src/db/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Read all data from playlists table
df = pd.read_sql('SELECT * FROM playlists', conn)

# Sort by Album Date descending so latest comes first
# Use errors='coerce' to handle invalid dates like "1956-00-00"
df['Album Date'] = pd.to_datetime(df['Album Date'], errors='coerce')
# Sort by Album Date, with NaT (invalid dates) going last
df = df.sort_values('Album Date', ascending=False, na_position='last')

# Keep only the first occurrence of each Track_Key (latest release)
df_deduped = df.drop_duplicates(subset='Track_Key', keep='first')

# Display stats
unique_track_ids = df['Track_ID'].nunique()
unique_track_keys = df['Track_Key'].nunique()
unique_artists = df['Artist'].nunique()

print(f"Unique Track_IDs: {unique_track_ids}")
print(f"Unique Track_Keys: {unique_track_keys}")
print(f"Unique Artists: {unique_artists}")
print(f"Removed: {unique_track_ids - unique_track_keys} duplicate tracks (same song, different Track_ID)")

# Sort by Artist, Song for the tracks table
df_deduped = df_deduped.sort_values(['Artist', 'Song'])

# Create a tracks table with deduplicated data
df_deduped.to_sql('tracks', conn, if_exists='replace', index=False)

conn.close()
print("Tracks table created with unique tracks sorted by Artist, Song.")
