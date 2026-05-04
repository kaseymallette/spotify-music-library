import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import numpy as np

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Query playlist names for dropdown
df_playlists = pd.read_sql("SELECT DISTINCT playlist_name FROM playlists ORDER BY playlist_name", conn)
playlist_options = df_playlists['playlist_name'].tolist()

# Query tracks table for audio features
df_all = pd.read_sql("""
    SELECT t.Track_Key, p.playlist_name, t.Album_Year, t.Artist, t.Song,
           t.BPM, t.Valence, t.Dance, t.Energy, t.Acoustic, t."Loud (DB)" as Loud_Db,
           t.Speech, t.Live, t.Popularity
    FROM tracks t
    JOIN playlists p ON t.Track_Key = p.Track_Key
    WHERE t.Album_Year IS NOT NULL
""", conn)
df_all['Decade'] = (df_all['Album_Year'] // 10) * 10
df_all['Decade'] = df_all['Decade'].astype(str) + 's'

# Convert features to numeric
FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Speech', 'Live', 'Album_Year', 'Popularity']
for col in FEATURES:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

conn.close()

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Spotify Music Library Dashboard"),
    
    html.H2("Playlist Statistics"),
    
    html.Div([
        html.Label("Select Playlist:"),
        dcc.Dropdown(
            id='playlist-dropdown',
            options=[{'label': 'All Playlists', 'value': 'all'}] + 
                    [{'label': playlist, 'value': playlist} for playlist in playlist_options],
            value='all'
        ),
    ], style={'marginBottom': '20px'}),
    
    html.Div(id='playlist-stats', style={'marginBottom': '20px', 'fontSize': '18px'}),
    
    html.H2("Song Count Distribution by Artist"),
    dcc.Graph(id='artist-song-chart'),
    
    html.H2("Decade Distribution"),
    dcc.Graph(id='decade-chart'),
    
    html.H2("Clustering Analysis"),
    dcc.Graph(id='elbow-chart'),
    
    html.H2("Cluster Visualization"),
    dcc.Graph(id='cluster-chart')
])

@app.callback(
    Output('playlist-stats', 'children'),
    Input('playlist-dropdown', 'value')
)
def update_stats(selected_playlist):
    if selected_playlist == 'all':
        df_filtered = df_all
    else:
        df_filtered = df_all[df_all['playlist_name'] == selected_playlist]
    
    song_count = len(df_filtered)
    unique_artists = df_filtered['Artist'].nunique()
    
    return html.Div([
        html.P(f"Total Songs: {song_count}"),
        html.P(f"Unique Artists: {unique_artists}")
    ])

@app.callback(
    Output('decade-chart', 'figure'),
    Input('playlist-dropdown', 'value')
)
def update_decade_chart(selected_playlist):
    if selected_playlist == 'all':
        df_filtered = df_all
    else:
        df_filtered = df_all[df_all['playlist_name'] == selected_playlist]
    
    decade_counts = df_filtered['Decade'].value_counts().sort_index()
    # Filter to start from 1950s
    decade_counts = decade_counts[decade_counts.index >= '1950s']
    
    fig = px.bar(
        x=decade_counts.index,
        y=decade_counts.values,
        labels={'x': 'Decade', 'y': 'Number of Songs'},
        title=f"Decade Distribution: {selected_playlist}"
    )
    
    return fig

@app.callback(
    Output('artist-song-chart', 'figure'),
    Input('playlist-dropdown', 'value')
)
def update_artist_chart(selected_playlist):
    if selected_playlist == 'all':
        df_filtered = df_all
    else:
        df_filtered = df_all[df_all['playlist_name'] == selected_playlist]
    
    artist_song_counts = df_filtered['Artist'].value_counts().head(10)
    
    fig = px.bar(
        x=artist_song_counts.values,
        y=artist_song_counts.index,
        orientation='h',
        labels={'x': 'Song Count', 'y': 'Artist'},
        title=f"Top 10 Artists by Song Count: {selected_playlist}"
    )
    
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    return fig

@app.callback(
    Output('elbow-chart', 'figure'),
    Input('playlist-dropdown', 'value')
)
def update_elbow_chart(selected_playlist):
    try:
        if selected_playlist == 'all':
            df_filtered = df_all
        else:
            df_filtered = df_all[df_all['playlist_name'] == selected_playlist]
        
        # Select features for clustering
        FEATURES_CLUSTER = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Album_Year', 'Popularity']
        df_features = df_filtered[FEATURES_CLUSTER].dropna()
        
        print(f"Elbow chart - Playlist: {selected_playlist}, Records: {len(df_features)}")
        
        if len(df_features) < 10:
            # Return empty figure if not enough data
            return px.line(title=f"Elbow Method: {selected_playlist} (Insufficient data)")
        
        # Standardize features
        scaler = StandardScaler()
        df_features_scaled = scaler.fit_transform(df_features)
        
        # Apply valence weighting
        valence_idx = FEATURES_CLUSTER.index('Valence')
        df_features_scaled[:, valence_idx] *= 1.5
        
        # Calculate inertia for different cluster numbers
        n_clusters_range = range(3, 11)
        inertias = []
        
        for n_clusters in n_clusters_range:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            kmeans.fit(df_features_scaled)
            inertias.append(kmeans.inertia_)
        
        # Plot elbow method
        fig = px.line(
            x=list(n_clusters_range),
            y=inertias,
            markers=True,
            labels={'x': 'Number of Clusters', 'y': 'Inertia'},
            title=f"Elbow Method: {selected_playlist}"
        )
        
        fig.update_layout(showlegend=False)
        
        return fig
    except Exception as e:
        print(f"Error in elbow chart: {e}")
        return px.line(title=f"Elbow Method: {selected_playlist} (Error: {str(e)})")

@app.callback(
    Output('cluster-chart', 'figure'),
    Input('playlist-dropdown', 'value')
)
def update_cluster_chart(selected_playlist):
    try:
        if selected_playlist == 'all':
            df_filtered = df_all
        else:
            df_filtered = df_all[df_all['playlist_name'] == selected_playlist]
        
        # Select features for clustering
        FEATURES_CLUSTER = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Album_Year', 'Popularity']
        df_features = df_filtered[FEATURES_CLUSTER].dropna()
        
        print(f"Cluster chart - Playlist: {selected_playlist}, Records: {len(df_features)}")
        
        if len(df_features) < 10:
            # Return empty figure if not enough data
            return px.scatter(title=f"Cluster Visualization: {selected_playlist} (Insufficient data)")
        
        # Standardize features
        scaler = StandardScaler()
        df_features_scaled = scaler.fit_transform(df_features)
        
        # Apply valence weighting
        valence_idx = FEATURES_CLUSTER.index('Valence')
        df_features_scaled[:, valence_idx] *= 1.5
        
        # Find optimal number of clusters using elbow method
        n_clusters_range = range(3, 11)
        inertias = []
        
        for n_clusters in n_clusters_range:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            kmeans.fit(df_features_scaled)
            inertias.append(kmeans.inertia_)
        
        # Calculate distances to find elbow
        n_points = len(n_clusters_range)
        x = np.array(n_clusters_range)
        y = np.array(inertias)
        x1, y1 = x[0], y[0]
        x2, y2 = x[-1], y[-1]
        distances = []
        for i in range(n_points):
            # Distance from point (x[i], y[i]) to line through (x1, y1) and (x2, y2)
            numerator = abs((y2 - y1) * x[i] - (x2 - x1) * y[i] + x2 * y1 - y2 * x1)
            denominator = ((y2 - y1)**2 + (x2 - x1)**2)**0.5
            dist = numerator / denominator
            distances.append(dist)
        elbow_idx = distances.index(max(distances))
        best_n_clusters = n_clusters_range[elbow_idx]
        
        print(f"Best number of clusters: {best_n_clusters}")
        
        # Fit final model with best number of clusters
        kmeans_final = KMeans(n_clusters=best_n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans_final.fit_predict(df_features_scaled)
        
        # Add cluster labels to dataframe
        df_features['cluster'] = cluster_labels
        
        # Plot Valence vs Energy with clusters
        fig = px.scatter(
            df_features,
            x='Valence',
            y='Energy',
            color='cluster',
            labels={'Valence': 'Valence (Mood)', 'Energy': 'Energy'},
            title=f"Cluster Visualization (Valence vs Energy): {selected_playlist} - {best_n_clusters} clusters"
        )
        
        return fig
    except Exception as e:
        print(f"Error in cluster chart: {e}")
        import traceback
        traceback.print_exc()
        return px.scatter(title=f"Cluster Visualization: {selected_playlist} (Error: {str(e)})")

if __name__ == '__main__':
    app.run(debug=True)
