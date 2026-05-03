import sqlite3

# Connect to the database
conn = sqlite3.connect('spotify_music_library.db')

print("=== Sample Queries ===\n")

# Playlists Table Queries
print("#### Table: Playlists\n")

# Get number of unique playlists
print("Get number of unique playlists:")
cursor = conn.execute("SELECT COUNT(DISTINCT playlist_name) FROM playlists;")
print(f"Result: {cursor.fetchone()[0]}\n")

# Get number of unique artists
print("Get number of unique artists:")
cursor = conn.execute("SELECT COUNT(DISTINCT Artist) FROM playlists;")
print(f"Result: {cursor.fetchone()[0]}\n")

# Get song count distribution per playlist
print("Get song count distribution per playlist (grouped ranges):")
cursor = conn.execute("""
    SELECT CASE
             WHEN song_count <= 50 THEN '0-50'
             WHEN song_count <= 100 THEN '51-100'
             WHEN song_count <= 200 THEN '101-200'
             WHEN song_count <= 500 THEN '201-500'
             ELSE '500+'
           END as song_count_range,
           COUNT(*) as playlist_count
    FROM (SELECT playlist_name, COUNT(*) as song_count
         FROM playlists
         GROUP BY playlist_name)
    GROUP BY song_count_range
    ORDER BY MIN(song_count);
""")
results = cursor.fetchall()
total = sum(row[1] for row in results)
print("Result:")
for song_count_range, playlist_count in results:
    percentage = (playlist_count / total) * 100
    print(f"{playlist_count} playlists have {song_count_range} songs ({percentage:.1f}%)")
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
print("Result:")
for row in results:
    print(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}")
print()

# Tracks Table Queries
print("#### Table: Tracks\n")

# Get distribution of artists by song count
print("Get distribution of artists by song count (grouped ranges):")
cursor = conn.execute("""
    SELECT CASE 
             WHEN song_count = 1 THEN '1'
             WHEN song_count BETWEEN 2 AND 3 THEN '2-3'
             ELSE '4+'
           END as song_count_range,
           COUNT(*) as artist_count
    FROM (SELECT Artist, COUNT(*) as song_count
         FROM tracks
         GROUP BY Artist)
    GROUP BY song_count_range
    ORDER BY MIN(song_count);
""")
results = cursor.fetchall()
total = sum(row[1] for row in results)
print("Result:")
for song_count_range, artist_count in results:
    percentage = (artist_count / total) * 100
    print(f"{artist_count} artists have {song_count_range} song(s) ({percentage:.1f}%)")
print()

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
print("Result:")
for row in results:
    print(f"{row[0]}|{row[1]}")
print()

conn.close()
print("=== End of Sample Queries ===")
