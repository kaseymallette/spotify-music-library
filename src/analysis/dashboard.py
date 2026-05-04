import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output
import os
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import euclidean_distances

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Query artists and songs for KNN dropdowns
df_songs = pd.read_sql("SELECT Song, Artist FROM tracks ORDER BY Song, Artist", conn)
song_options = [{'label': f"{row['Song']} - {row['Artist']}", 'value': f"{row['Song']}|{row['Artist']}"} for _, row in df_songs.iterrows()]

conn.close()

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Spotify Music Library Dashboard"),
    
    html.Hr(),
    html.H2("K-Nearest Neighbors (KNN) Seed Songs"),
    
    html.Div([
        html.Label("Select Song:"),
        dcc.Dropdown(
            id='knn-song-dropdown',
            options=song_options,
            value=None,
            placeholder="Search for a song...",
            searchable=True
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Div([
        html.Label("Year Range (years from seed song):"),
        dcc.Input(
            id='knn-year-range',
            type='number',
            value=10,
            min=0,
            step=5,
            style={'width': '150px'}
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Div([
        html.Label("Number of Songs:"),
        dcc.Input(
            id='knn-num-songs',
            type='number',
            value=10,
            min=1,
            max=100,
            step=1,
            style={'width': '150px'}
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Button('Find Similar Songs', id='knn-button', n_clicks=0, style={'marginBottom': '20px'}),
    
    html.Div(id='knn-results')
])

@app.callback(
    Output('knn-results', 'children'),
    Input('knn-button', 'n_clicks'),
    Input('knn-song-dropdown', 'value'),
    Input('knn-year-range', 'value'),
    Input('knn-num-songs', 'value')
)
def update_knn_results(n_clicks, selected_song_artist, year_range, num_songs):
    if n_clicks == 0 or not selected_song_artist:
        return html.Div("Select a song to find similar tracks.")
    
    try:
        # Parse song and artist from selected value
        selected_song, selected_artist = selected_song_artist.split('|')
        # Load data for KNN
        conn = sqlite3.connect(db_path)
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
        conn.close()
        
        # Set index
        df_metadata = df_metadata.set_index('Track_Key')
        df_features = df_features.set_index('Track_Key')
        
        # Find seed song
        seed_key = f"{selected_artist}|{selected_song}"
        if seed_key not in df_metadata.index:
            return html.Div(f"Song '{selected_song}' by '{selected_artist}' not found in database.")
        
        seed_row = df_metadata.loc[seed_key]
        seed_year = seed_row['Album_Year']
        
        # Features for KNN
        FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db']
        
        # Standardize features
        scaler = StandardScaler()
        df_features_scaled = scaler.fit_transform(df_features[FEATURES])
        
        # Apply valence weighting
        valence_idx = FEATURES.index('Valence')
        df_features_scaled[:, valence_idx] *= 1.5
        
        # Get seed features
        seed_idx = df_features.index.get_loc(seed_key)
        seed_features = df_features_scaled[seed_idx]
        
        # Calculate distances
        from sklearn.metrics.pairwise import euclidean_distances
        distances = euclidean_distances([seed_features], df_features_scaled)[0]
        
        # Add distances to metadata
        df_metadata['distance'] = distances
        
        # Sort by distance
        df_metadata = df_metadata.sort_values('distance')
        
        # Remove seed song
        df_metadata = df_metadata[df_metadata.index != seed_key]
        
        # Apply year filter if specified
        if year_range and year_range > 0:
            df_metadata = df_metadata[
                (df_metadata['Album_Year'] >= seed_year - year_range) & 
                (df_metadata['Album_Year'] <= seed_year + year_range)
            ]
        
        # Get top N results
        df_results = df_metadata.head(num_songs)
        
        # Build results display
        results_html = [
            html.H3(f"{num_songs} songs most similar to '{selected_song}' by '{selected_artist}':"),
            html.P(f"Seed song year: {seed_year}, Year filter: ±{year_range} years" if year_range else f"Seed song year: {seed_year}"),
            html.Hr(),
            html.Div([
                html.P(f"0. {seed_row['Song']} — {seed_row['Artist']} ({seed_row['Album_Year']}) [ORIGINAL]", style={'fontWeight': 'bold'}),
                html.P(f"   Distance: 0.0000"),
                html.P(f"   Popularity: {seed_row['Popularity']}"),
                html.P(f"   Features: BPM={df_features.loc[seed_key, 'BPM']}, Valence={df_features.loc[seed_key, 'Valence']}, Dance={df_features.loc[seed_key, 'Dance']}, Energy={df_features.loc[seed_key, 'Energy']}, Acoustic={df_features.loc[seed_key, 'Acoustic']}, Loud_Db={df_features.loc[seed_key, 'Loud_Db']}"),
                html.Hr()
            ])
        ]
        
        for i, (idx, row) in enumerate(df_results.iterrows(), 1):
            results_html.append(html.Div([
                html.P(f"{i}. {row['Song']} — {row['Artist']} ({row['Album_Year']})", style={'fontWeight': 'bold'}),
                html.P(f"   Distance: {row['distance']:.4f}"),
                html.P(f"   Popularity: {row['Popularity']}"),
                html.P(f"   Features: BPM={df_features.loc[idx, 'BPM']}, Valence={df_features.loc[idx, 'Valence']}, Dance={df_features.loc[idx, 'Dance']}, Energy={df_features.loc[idx, 'Energy']}, Acoustic={df_features.loc[idx, 'Acoustic']}, Loud_Db={df_features.loc[idx, 'Loud_Db']}"),
                html.Hr()
            ]))
        
        return html.Div(results_html)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return html.Div(f"Error: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)
