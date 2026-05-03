import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# Connect to the database
conn = sqlite3.connect('spotify_music_library.db')

# Query artist playlist count
df_artists = pd.read_sql("SELECT Artist, playlist_count FROM artist_playlist_count", conn)

# Query song playlist count
df_songs = pd.read_sql("SELECT Track_Key, Track_ID, playlist_count FROM song_playlist_count", conn)

conn.close()

# Create figure with subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# Artist playlist count distribution
artist_counts = df_artists['playlist_count'].value_counts().sort_index()
ax1.bar(artist_counts.index, artist_counts.values, color='steelblue')
ax1.set_xlabel('Number of Playlists')
ax1.set_ylabel('Number of Artists')
ax1.set_title('Artist Playlist Count Distribution')
ax1.grid(axis='y', alpha=0.3)

# Song playlist count distribution
song_counts = df_songs['playlist_count'].value_counts().sort_index()
ax2.bar(song_counts.index, song_counts.values, color='coral')
ax2.set_xlabel('Number of Playlists')
ax2.set_ylabel('Number of Songs')
ax2.set_title('Song Playlist Count Distribution')
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('playlist_count_distributions.png', dpi=150)
print("Chart saved as playlist_count_distributions.png")

# Show statistics
print("\n=== Artist Playlist Count Statistics ===")
print(f"Total artists: {len(df_artists)}")
print(f"Artists in 1 playlist: {(df_artists['playlist_count'] == 1).sum()}")
print(f"Artists in 2+ playlists: {(df_artists['playlist_count'] >= 2).sum()}")
print(f"Artists in 5+ playlists: {(df_artists['playlist_count'] >= 5).sum()}")
print(f"Max playlists per artist: {df_artists['playlist_count'].max()}")

print("\n=== Song Playlist Count Statistics ===")
print(f"Total songs: {len(df_songs)}")
print(f"Songs in 1 playlist: {(df_songs['playlist_count'] == 1).sum()}")
print(f"Songs in 2+ playlists: {(df_songs['playlist_count'] >= 2).sum()}")
print(f"Songs in 5+ playlists: {(df_songs['playlist_count'] >= 5).sum()}")
print(f"Max playlists per song: {df_songs['playlist_count'].max()}")
