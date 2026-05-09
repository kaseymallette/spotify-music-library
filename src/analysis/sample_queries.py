import sqlite3
import os

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

print("=== Sample Queries ===\n")

# Get number of unique playlists
print("Get number of unique playlists:")
cursor = conn.execute("SELECT COUNT(DISTINCT playlist_name) FROM playlists;")
print(f"{cursor.fetchone()[0]}\n")

# Get number of unique artists
print("Get number of unique artists:")
cursor = conn.execute("SELECT COUNT(DISTINCT Artist) FROM playlists;")
print(f"{cursor.fetchone()[0]}\n")

# Get number of unique songs
print("Get number of unique songs:")
cursor = conn.execute("SELECT COUNT(*) FROM tracks;")
print(f"{cursor.fetchone()[0]}\n")

# Get top five artists with song count
print("Get top five artists with song count:")
cursor = conn.execute("""
    SELECT Artist, COUNT(*) as song_count
    FROM tracks
    GROUP BY Artist
    ORDER BY song_count DESC
    LIMIT 5;
""")
results = cursor.fetchall()
for row in results:
    print(f"{row[0]}|{row[1]}")
print()

# Get top 5 songs by playlist count
print("Get top 5 songs by playlist count:")
cursor = conn.execute("""
    SELECT Track_Key, playlist_count
    FROM song_playlist_count
    ORDER BY playlist_count DESC
    LIMIT 5;
""")
results = cursor.fetchall()
for row in results:
    # Extract artist and song from Track_Key
    parts = row[0].split('|')
    artist = parts[0] if len(parts) > 0 else 'Unknown'
    song = parts[1] if len(parts) > 1 else 'Unknown'
    print(f"{artist} - {song}: {row[1]} playlists")
print()

# Get top 5 artists by playlist count
print("Get top 5 artists by playlist count:")
cursor = conn.execute("""
    SELECT Artist, playlist_count
    FROM artist_playlist_count
    ORDER BY playlist_count DESC
    LIMIT 5;
""")
results = cursor.fetchall()
for row in results:
    print(f"{row[0]}: {row[1]} playlists")
print()

# Get songs from playlist 01
print("Get songs from playlist 01:")
cursor = conn.execute("""
    SELECT Song_Number, Song, Artist, Album_Year
    FROM playlists
    WHERE playlist_number = '01'
    ORDER BY Song_Number;
""")
results = cursor.fetchall()
for row in results:
    print(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}")
print()

# Get harmonic mixing transitions for key 1A
print("Get harmonic mixing transitions for key 1A:")
cursor = conn.execute("""
    SELECT target_key, mix_type
    FROM mixing_rules
    WHERE starting_key = '1A';
""")
results = cursor.fetchall()
for row in results:
    print(f"{row[0]} ({row[1]})")
print()

conn.close()
print("=== End of Sample Queries ===")
