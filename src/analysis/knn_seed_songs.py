import sqlite3
import pandas as pd
import numpy as np
import math
import os
import argparse
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from adjustText import adjust_text

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')
images_dir = os.path.join(root_dir, 'images')
os.makedirs(images_dir, exist_ok=True)

# Features for clustering
FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Album_Year', 'Popularity']

# Audio features for KNN similarity (exclude year and popularity)
AUDIO_FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db']

# Connect to the database
conn = sqlite3.connect(db_path)

# Query tracks data
df_metadata = pd.read_sql("""
    SELECT Track_Key, Song, Artist, Album_Year, Popularity
    FROM tracks
    WHERE Album_Year IS NOT NULL
""", conn)

df_features = pd.read_sql("""
    SELECT Track_Key, BPM, Valence, Dance, Energy, Acoustic, "Loud (DB)" as Loud_Db, Album_Year, Popularity
    FROM tracks
    WHERE Album_Year IS NOT NULL
""", conn)

# Convert to numeric
for col in FEATURES:
    if col in df_features.columns:
        df_features[col] = pd.to_numeric(df_features[col], errors='coerce')

# Set Track_Key as index for both dataframes
df_metadata = df_metadata.set_index('Track_Key')
df_features = df_features.set_index('Track_Key')

conn.close()

print(f"Total tracks: {len(df_metadata)}")
print(f"Features shape: {df_features.shape}")

# === HELPER FUNCTIONS: SEED SONGS ===

def collect_seeds(df_playlist_metadata, df_playlist_features, seed_songs_dict):
    """
    Collect seed song data into a DataFrame.
    
    Parameters:
    - seed_songs_dict: dict of {song_name: artist_name}
    
    Returns:
    - df_seeds: DataFrame with song, artist, popularity, year, and FEATURES
    """
    seeds = []
    for song, artist in seed_songs_dict.items():
        result = get_song_features(df_playlist_metadata, df_playlist_features, song, artist)
        if result:
            seeds.append({
                'song': song,
                'artist': artist,
                'features': result['features'],
                'popularity': result['popularity'],
                'year': result['year'],
                'index': result['index']
            })
    
    df_seeds = pd.DataFrame(seeds)
    if len(df_seeds) > 0:
        df_seeds[FEATURES] = pd.DataFrame(df_seeds['features'].tolist(), index=df_seeds.index)
        df_seeds = df_seeds.drop(columns=['features'])
    
    print("\n" + "="*50)
    print("SEED SUMMARY")
    print("="*50)
    print(df_seeds)
    
    return df_seeds

def get_song_features(df_playlist_metadata, df_playlist_features, song_name, artist_name=None):
    mask = df_playlist_metadata['Song'].str.contains(song_name, case=False, na=False)
    if artist_name:
        mask = mask & df_playlist_metadata['Artist'].str.contains(artist_name, case=False, na=False)
    
    if mask.sum() == 0:
        print(f"Couldn't find '{song_name}'" + (f" by '{artist_name}'" if artist_name else ""))
        return None
    
    idx = df_playlist_metadata[mask].index[0]
    meta = df_playlist_metadata.loc[idx]
    feats = df_playlist_features.loc[idx]

    print(f"• {meta['Song']} — {meta['Artist']} ({meta['Album_Year']})")
    print(f"  Popularity: {meta['Popularity']}")
    for feature in FEATURES:
        if feature in feats:
            print(f"  {feature}: {feats[feature]}")
    print('\n')
    
    return {
        'features': [float(feats[f]) if f in feats and pd.notna(feats[f]) else 0.0 for f in FEATURES],
        'popularity': int(meta['Popularity']),
        'year': int(meta['Album_Year']),
        'index': idx
    }

def find_k_nearest_neighbors(df_playlist_metadata, df_playlist_features, seed_features, k=10):
    """
    Find k nearest neighbors to a seed song using Euclidean distance.
    
    Parameters:
    - seed_features: list of feature values for the seed song
    - k: number of nearest neighbors to return
    
    Returns:
    - DataFrame with k nearest neighbors
    """
    # Use only audio features for similarity
    df_audio = df_playlist_features[AUDIO_FEATURES]
    seed_audio = [seed_features[i] for i, f in enumerate(FEATURES) if f in AUDIO_FEATURES]
    
    # Scale features
    scaler = StandardScaler()
    df_audio_scaled = scaler.fit_transform(df_audio)
    
    # Apply valence weighting (1.5x) to prioritize mood separation
    valence_idx = AUDIO_FEATURES.index('Valence')
    df_audio_scaled[:, valence_idx] *= 1.5
    seed_audio_scaled = scaler.transform([seed_audio])[0]
    seed_audio_scaled[valence_idx] *= 1.5
    
    # Calculate distances
    distances = []
    for i, row in enumerate(df_audio_scaled):
        dist = np.linalg.norm(row - seed_audio_scaled)
        distances.append((i, dist))
    
    # Sort by distance and get top k
    distances.sort(key=lambda x: x[1])
    top_k = distances[:k]
    
    # Get metadata for top k songs
    neighbor_indices = [df_playlist_features.index[idx] for idx, dist in top_k]
    neighbor_distances = [dist for idx, dist in top_k]
    
    neighbors = df_playlist_metadata.loc[neighbor_indices].copy()
    neighbors['distance'] = neighbor_distances
    
    return neighbors

def visualize_seeds(df_playlist_features, df_seeds):
    """
    Visualize seed placement in feature space using pairwise feature plots.
    Clusters in the original 8-dimensional space, no PCA reduction.
    """
    # --- Scale features ---
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_playlist_features)
    
    # --- Find best k ---
    def get_best_k(X_scaled, k_range=(3, 11)):
        scores = {}
        for k in range(k_range[0], k_range[1]):
            km = KMeans(n_clusters=k, n_init=50, random_state=42)
            labels = km.fit_predict(X_scaled)
            scores[k] = silhouette_score(X_scaled, labels)
        best_k = max(scores, key=scores.get)
        return best_k, scores
    
    best_k, scores = get_best_k(X_scaled)
    print(f"Best k for clustering: {best_k}")
    
    # --- Cluster ---
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    # --- Transform seeds ---
    seeds_scaled = scaler.transform(df_seeds[FEATURES])
    seed_clusters = kmeans.predict(seeds_scaled)
    seed_distances = [
        np.linalg.norm(seeds_scaled[i] - kmeans.cluster_centers_[seed_clusters[i]])
        for i in range(len(seeds_scaled))
    ]
    
    print(f"Seed cluster assignments: {seed_clusters}")
    print(f"Seed distances to cluster centers: {[f'{d:.2f}' for d in seed_distances]}")
    
    # --- Plot setup ---
    feature_names = df_playlist_features.columns.tolist()
    plot_pairs = [
        ('Energy', 'Acoustic'),
        ('Valence', 'Energy'),
        ('BPM', 'Dance'),
        ('Loud_Db', 'Energy'),
        ('Valence', 'Dance'),
        ('BPM', 'Valence'),
    ]
    
    # Map feature names to our actual column names
    feature_mapping = {
        'Energy': 'Energy',
        'Acoustic': 'Acoustic',
        'Valence': 'Valence',
        'BPM': 'BPM',
        'Dance': 'Dance',
        'Loud (Db)': 'Loud_Db',
        'Loud_Db': 'Loud_Db'
    }
    
    pairs = []
    for a, b in plot_pairs:
        mapped_a = feature_mapping.get(a, a)
        mapped_b = feature_mapping.get(b, b)
        if mapped_a in feature_names and mapped_b in feature_names:
            pairs.append((feature_names.index(mapped_a), feature_names.index(mapped_b)))
    
    n_plots = len(pairs)
    n_cols = 3
    n_rows = math.ceil(n_plots / n_cols)
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(7 * n_cols, 5 * n_rows))
    axes = np.array(axes).flatten()
    
    # --- PLOTTING LOOP ---
    for ax, (i, j) in zip(axes, pairs):
        # Scatter all songs
        ax.scatter(X_scaled[:, i], X_scaled[:, j], c=clusters, cmap='viridis', alpha=0.5)
        
        # Scatter seed songs
        ax.scatter(seeds_scaled[:, i], seeds_scaled[:, j],
                   c='red', s=150, edgecolors='black', linewidths=2, label='Seeds', zorder=5)
        
        # Annotate seed songs
        texts = []
        for pos, (idx, row) in enumerate(df_seeds.iterrows()):
            t = ax.annotate(row['song'], (seeds_scaled[pos, i], seeds_scaled[pos, j]),
                            fontsize=8, ha='left', va='bottom')
            texts.append(t)
        
        # Repel overlapping labels
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='-', color='gray', lw=0.5))
        
        ax.set_xlabel(feature_names[i])
        ax.set_ylabel(feature_names[j])
        ax.set_title(f"{feature_names[i]} vs {feature_names[j]}")
    
    # Add seed legend
    seed_names = df_seeds['song'].tolist()
    legend_text = "Seeds:\n" + "\n".join(f"• {name}" for name in seed_names)
    fig.text(0.98, 0.5, legend_text, fontsize=12, va='center', ha='left',
             bbox=dict(boxstyle='round', facecolor='white', edgecolor='red', alpha=0.9),
             transform=fig.transFigure)
    
    plt.subplots_adjust(right=0.95)
    
    # Save plot
    plot_path = os.path.join(images_dir, 'seed_visualization.png')
    plt.savefig(plot_path, dpi=150)
    print(f"\nSeed visualization saved as seed_visualization.png")
    plt.show()

# Example usage with seed songs
if __name__ == '__main__':
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Find similar songs using K-nearest neighbors')
    parser.add_argument('--song', type=str, help='Song name')
    parser.add_argument('--artist', type=str, help='Artist name')
    parser.add_argument('--num-songs', type=int, default=10, help='Number of similar songs to find (default: 10)')
    parser.add_argument('--year-range', type=int, default=None, help='Maximum year difference from seed song (e.g., 10 for songs within 10 years)')
    args = parser.parse_args()
    
    # Define seed songs (song_name: artist_name)
    if args.song and args.artist:
        seed_songs_dict = {args.song: args.artist}
    else:
        # Default example if no arguments provided
        seed_songs_dict = {
            "Snap Out Of It": "Arctic Monkeys"
        }
        print("No arguments provided. Using default seed song: 'Snap Out Of It' by 'Arctic Monkeys'")
        print("Usage: python src/analysis/knn_seed_songs.py --song 'Song Name' --artist 'Artist Name' [--num-songs N] [--year-range N]\n")
    
    print("=== SEED SONG ANALYSIS ===")
    print(f"Seed songs: {seed_songs_dict}")
    
    # Collect seed songs
    df_seeds = collect_seeds(df_metadata, df_features, seed_songs_dict)
    
    if len(df_seeds) > 0:
        print(f"\nSeed song found successfully!")
        print(f"Cluster assignment: {df_seeds}")
        
        # Find nearest neighbors for the first seed song
        seed_row = df_seeds.iloc[0]
        seed_features = seed_row[FEATURES].tolist()
        seed_index = seed_row['index']
        seed_year = seed_row['year']
        num_songs = args.num_songs
        year_range = args.year_range
        
        print("\n" + "="*50)
        print(f"FINDING {num_songs} NEAREST NEIGHBORS")
        if year_range:
            print(f"Year filter: songs within {year_range} years of {seed_year}")
        print("="*50)
        
        # Request more neighbors to account for year filtering
        k_request = num_songs + 1
        if year_range:
            k_request = num_songs * 3 + 1  # Request more to account for filtering
        
        neighbors = find_k_nearest_neighbors(df_metadata, df_features, seed_features, k=k_request)
        
        # Remove the seed song itself if it's in the results
        neighbors = neighbors[neighbors.index != seed_index]
        
        # Apply year filter if specified
        if year_range:
            neighbors = neighbors[
                (neighbors['Album_Year'] >= seed_year - year_range) & 
                (neighbors['Album_Year'] <= seed_year + year_range)
            ]
            print(f"After year filter: {len(neighbors)} songs remaining")
        
        # Ensure we have enough songs
        if len(neighbors) < num_songs:
            print(f"Warning: Only {len(neighbors)} songs found within criteria (requested {num_songs})")
        
        # Display the nearest neighbors
        print(f"\n{min(num_songs, len(neighbors))} songs most similar to '{seed_row['song']}' by '{seed_row['artist']}':\n")
        
        # First, display the original seed song
        seed_features = df_features.loc[seed_index]
        print(f"0. {seed_row['song']} — {seed_row['artist']} ({seed_row['year']}) [ORIGINAL]")
        print(f"   Distance: 0.0000")
        print(f"   Popularity: {seed_row['popularity']}")
        print(f"   Features: BPM={seed_features['BPM']}, Valence={seed_features['Valence']}, Dance={seed_features['Dance']}, Energy={seed_features['Energy']}, Acoustic={seed_features['Acoustic']}, Loud_Db={seed_features['Loud_Db']}")
        print()
        
        # Then display the neighbors
        for i, (idx, row) in enumerate(neighbors.head(num_songs).iterrows(), 1):
            print(f"{i}. {row['Song']} — {row['Artist']} ({row['Album_Year']})")
            print(f"   Distance: {row['distance']:.4f}")
            print(f"   Popularity: {row['Popularity']}")
            # Get features for this song
            song_features = df_features.loc[idx]
            print(f"   Features: BPM={song_features['BPM']}, Valence={song_features['Valence']}, Dance={song_features['Dance']}, Energy={song_features['Energy']}, Acoustic={song_features['Acoustic']}, Loud_Db={song_features['Loud_Db']}")
            print()
    else:
        print("No seed songs found. Please check the song names and artists.")
