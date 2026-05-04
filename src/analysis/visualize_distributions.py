import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')
images_dir = os.path.join(root_dir, 'images')

# Connect to the database
conn = sqlite3.connect(db_path)

# Query raw artist playlist count
df_artist_playlist_raw = pd.read_sql("SELECT Artist, playlist_count FROM artist_playlist_count", conn)

# Query raw song playlist count
df_song_playlist_raw = pd.read_sql("SELECT Track_ID, playlist_count FROM song_playlist_count", conn)

# Query unique artists per playlist distribution (grouped ranges)
df_artists_per_playlist = pd.read_sql("""
    SELECT CASE
             WHEN artist_count <= 50 THEN '0-50'
             WHEN artist_count <= 100 THEN '51-100'
             WHEN artist_count <= 200 THEN '101-200'
             WHEN artist_count <= 300 THEN '201-300'
             ELSE '300+'
           END as artist_count_range,
           COUNT(*) as playlist_count
    FROM (SELECT playlist_name, COUNT(DISTINCT Artist) as artist_count
         FROM playlists
         GROUP BY playlist_name)
    GROUP BY artist_count_range
    ORDER BY MIN(artist_count);
""", conn)

# Query song count by playlist (grouped ranges)
df_playlist_song = pd.read_sql("""
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
""", conn)

conn.close()

# Create a helper to bucket the counts
def bucket_counts(series, cap=5):
    counts = series.value_counts().sort_index()
    # Pull everything above the cap into a single "X+" string
    main_part = counts[counts.index < cap]
    plus_part = counts[counts.index >= cap].sum()
    
    # Reconstruct the index for plotting
    labels = [str(i) for i in main_part.index] + [f"{cap}+"]
    values = list(main_part.values) + [plus_part]
    return labels, values

# Get bucketed data for artist and song playlist counts
art_labels, art_vals = bucket_counts(df_artist_playlist_raw['playlist_count'])
song_labels, song_vals = bucket_counts(df_song_playlist_raw['playlist_count'])

# Create figure with 2x2 subplots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

# Artist playlist count distribution (bucketed)
ax1.bar(art_labels, art_vals, color='steelblue')
ax1.set_xlabel('Playlist Count')
ax1.set_ylabel('Number of Artists')
ax1.set_title('Artist Playlist Count Distribution')
ax1.grid(axis='y', alpha=0.3)

# Song playlist count distribution (bucketed)
ax2.bar(song_labels, song_vals, color='coral')
ax2.set_xlabel('Playlist Count')
ax2.set_ylabel('Number of Songs')
ax2.set_title('Song Playlist Count Distribution')
ax2.grid(axis='y', alpha=0.3)

# Unique artists per playlist distribution (grouped ranges)
ax3.bar(df_artists_per_playlist['artist_count_range'], df_artists_per_playlist['playlist_count'], color='mediumseagreen')
ax3.set_xlabel('Artist Count Range')
ax3.set_ylabel('Number of Playlists')
ax3.set_title('Unique Artists per Playlist Distribution')
ax3.grid(axis='y', alpha=0.3)

# Playlist song count distribution (grouped ranges)
ax4.bar(df_playlist_song['song_count_range'], df_playlist_song['playlist_count'], color='orchid')
ax4.set_xlabel('Song Count Range')
ax4.set_ylabel('Number of Playlists')
ax4.set_title('Playlist Song Count Distribution')
ax4.grid(axis='y', alpha=0.3)

plt.tight_layout()
chart_path = os.path.join(images_dir, 'distributions.png')
plt.savefig(chart_path, dpi=150)
print("Chart saved as distributions.png")

# Show statistics
print("\n=== Artist Playlist Count Statistics ===")
print(f"Total artists: {len(df_artist_playlist_raw)}")
print(f"Artists in 1 playlist: {(df_artist_playlist_raw['playlist_count'] == 1).sum()}")
print(f"Artists in 2+ playlists: {(df_artist_playlist_raw['playlist_count'] >= 2).sum()}")
print(f"Artists in 5+ playlists: {(df_artist_playlist_raw['playlist_count'] >= 5).sum()}")
print(f"Max playlists per artist: {df_artist_playlist_raw['playlist_count'].max()}")

print("\n=== Song Playlist Count Statistics ===")
print(f"Total songs: {len(df_song_playlist_raw)}")
print(f"Songs in 1 playlist: {(df_song_playlist_raw['playlist_count'] == 1).sum()}")
print(f"Songs in 2+ playlists: {(df_song_playlist_raw['playlist_count'] >= 2).sum()}")
print(f"Songs in 5+ playlists: {(df_song_playlist_raw['playlist_count'] >= 5).sum()}")
print(f"Max playlists per song: {df_song_playlist_raw['playlist_count'].max()}")
