import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, State
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
    
    html.Div(id='knn-results'),
    
    html.Hr(),
    html.H2("Playlist Builder"),
    
    html.Div([
        html.Label("Select Seed Song:"),
        dcc.Dropdown(
            id='pb-song-dropdown',
            options=song_options,
            value=None,
            placeholder="Search for a song...",
            searchable=True
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Div([
        html.Label("Year Range (years from seed song):"),
        dcc.Input(
            id='pb-year-range',
            type='number',
            value=10,
            min=0,
            step=5,
            style={'width': '150px'}
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Div([
        html.Label("Target Playlist Size:"),
        dcc.Input(
            id='pb-target-size',
            type='number',
            value=50,
            min=2,
            max=200,
            step=1,
            style={'width': '150px'}
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Button('Start Playlist Builder', id='pb-start-button', n_clicks=0, style={'marginBottom': '20px'}),
    
    html.Div(id='pb-current-song', style={'marginBottom': '20px'}),
    
    html.Div([
        html.Button('Accept Song', id='pb-accept-button', n_clicks=0, disabled=True, style={'marginRight': '10px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
        html.Button('Reject Song', id='pb-reject-button', n_clicks=0, disabled=True, style={'backgroundColor': '#f44336', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
    ], style={'marginBottom': '20px'}),
    
    html.Div(id='pb-progress', style={'marginBottom': '20px', 'fontSize': '18px'}),
    
    html.Button('Export Playlist to CSV', id='pb-export-button', n_clicks=0, disabled=True, style={'marginBottom': '20px', 'backgroundColor': '#2196F3', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
    dcc.Download(id='pb-download'),
    
    html.Div(id='pb-playlist'),
    
    dcc.Store(id='pb-knn-results'),
    dcc.Store(id='pb-current-index'),
    dcc.Store(id='pb-accepted-songs'),
    dcc.Store(id='pb-rejected-songs')
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
            SELECT Track_Key, Track_ID, Song, Artist, Album, Album_Year, Popularity
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

@app.callback(
    Output('pb-knn-results', 'data'),
    Output('pb-current-index', 'data'),
    Output('pb-accepted-songs', 'data'),
    Output('pb-rejected-songs', 'data'),
    Input('pb-start-button', 'n_clicks'),
    State('pb-song-dropdown', 'value'),
    State('pb-year-range', 'value')
)
def start_playlist_builder(n_clicks, selected_song_artist, year_range):
    if n_clicks == 0 or not selected_song_artist:
        return None, 0, [], []
    
    try:
        selected_song, selected_artist = selected_song_artist.split('|')
        
        conn = sqlite3.connect(db_path)
        df_metadata = pd.read_sql("""
            SELECT Track_Key, Track_ID, Song, Artist, Album, Album_Year, Popularity
            FROM tracks
            WHERE Album_Year IS NOT NULL
        """, conn)
        
        df_features = pd.read_sql("""
            SELECT Track_Key, BPM, Valence, Dance, Energy, Acoustic, "Loud (DB)" as Loud_Db
            FROM tracks
            WHERE Album_Year IS NOT NULL
        """, conn)
        conn.close()
        
        df_metadata = df_metadata.set_index('Track_Key')
        df_features = df_features.set_index('Track_Key')
        
        seed_key = f"{selected_artist}|{selected_song}"
        if seed_key not in df_metadata.index:
            return None, 0, [], []
        
        seed_row = df_metadata.loc[seed_key]
        seed_year = seed_row['Album_Year']
        
        FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db']
        scaler = StandardScaler()
        df_features_scaled = scaler.fit_transform(df_features[FEATURES])
        
        valence_idx = FEATURES.index('Valence')
        df_features_scaled[:, valence_idx] *= 1.5
        
        seed_idx = df_features.index.get_loc(seed_key)
        seed_features = df_features_scaled[seed_idx]
        
        distances = euclidean_distances([seed_features], df_features_scaled)[0]
        df_metadata['distance'] = distances
        df_metadata = df_metadata.sort_values('distance')
        df_metadata = df_metadata[df_metadata.index != seed_key]
        
        if year_range and year_range > 0:
            df_metadata = df_metadata[
                (df_metadata['Album_Year'] >= seed_year - year_range) & 
                (df_metadata['Album_Year'] <= seed_year + year_range)
            ]
        
        # Convert to dict for storage
        knn_results = df_metadata.to_dict('records')
        
        return knn_results, 0, [], []
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, 0, [], []

@app.callback(
    Output('pb-current-song', 'children'),
    Output('pb-accept-button', 'disabled'),
    Output('pb-reject-button', 'disabled'),
    Input('pb-knn-results', 'data'),
    Input('pb-current-index', 'data'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-rejected-songs', 'data'),
    Input('pb-target-size', 'value'),
    State('pb-song-dropdown', 'value')
)
def update_current_song(knn_results, current_index, accepted_songs, rejected_songs, target_size, seed_song_artist):
    if not knn_results or not seed_song_artist:
        return html.Div("Select a seed song and click 'Start Playlist Builder' to begin."), True, True
    
    current_count = 1 + len(accepted_songs) if accepted_songs else 1
    if current_count >= target_size:
        return html.H3("Playlist Complete!"), True, True
    
    if current_index >= len(knn_results):
        return html.H3("No more songs available!"), True, True
    
    current_song = knn_results[current_index]
    
    return html.Div([
        html.H3(f"Song {current_index + 1}:"),
        html.P(f"{current_song['Song']} — {current_song['Artist']} ({current_song['Album_Year']})", style={'fontSize': '20px', 'fontWeight': 'bold'}),
        html.P(f"Distance: {current_song['distance']:.4f}"),
        html.P(f"Popularity: {current_song['Popularity']}")
    ]), False, False

@app.callback(
    Output('pb-current-index', 'data', allow_duplicate=True),
    Output('pb-accepted-songs', 'data', allow_duplicate=True),
    Input('pb-accept-button', 'n_clicks'),
    State('pb-knn-results', 'data'),
    State('pb-current-index', 'data'),
    State('pb-accepted-songs', 'data'),
    prevent_initial_call=True
)
def accept_song(n_clicks, knn_results, current_index, accepted_songs):
    if not knn_results or current_index >= len(knn_results):
        return current_index, accepted_songs
    
    new_accepted = accepted_songs.copy()
    new_accepted.append(knn_results[current_index])
    
    return current_index + 1, new_accepted

@app.callback(
    Output('pb-current-index', 'data', allow_duplicate=True),
    Output('pb-rejected-songs', 'data', allow_duplicate=True),
    Input('pb-reject-button', 'n_clicks'),
    State('pb-knn-results', 'data'),
    State('pb-current-index', 'data'),
    State('pb-rejected-songs', 'data'),
    prevent_initial_call=True
)
def reject_song(n_clicks, knn_results, current_index, rejected_songs):
    if not knn_results or current_index >= len(knn_results):
        return current_index, rejected_songs
    
    new_rejected = rejected_songs.copy()
    new_rejected.append(knn_results[current_index])
    
    return current_index + 1, new_rejected

@app.callback(
    Output('pb-progress', 'children'),
    Output('pb-playlist', 'children'),
    Output('pb-export-button', 'disabled'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-target-size', 'value'),
    State('pb-song-dropdown', 'value')
)
def update_progress_playlist(accepted_songs, target_size, seed_song_artist):
    if not accepted_songs:
        if seed_song_artist:
            return html.Div(f"Progress: 1/{target_size} songs (Seed song selected)"), html.Div(), True
        return html.Div(f"Progress: 0/{target_size} songs"), html.Div(), True
    
    current_count = 1 + len(accepted_songs)  # Seed song + accepted songs
    progress_text = f"Progress: {current_count}/{target_size} songs"
    
    is_complete = current_count >= target_size
    if is_complete:
        progress_text += " - Playlist Complete!"
    
    # Build playlist display
    playlist_html = [
        html.H3("Current Playlist:"),
        html.Hr()
    ]
    
    # Add seed song
    if seed_song_artist:
        seed_song, seed_artist = seed_song_artist.split('|')
        playlist_html.append(html.Div([
            html.P(f"1. {seed_song} — {seed_artist} [SEED]", style={'fontWeight': 'bold', 'color': '#4CAF50'}),
            html.Hr()
        ]))
    
    # Add accepted songs
    for i, song in enumerate(accepted_songs, 2):
        playlist_html.append(html.Div([
            html.P(f"{i}. {song['Song']} — {song['Artist']} ({song['Album_Year']})", style={'fontWeight': 'bold'}),
            html.P(f"   Distance: {song['distance']:.4f}, Popularity: {song['Popularity']}"),
            html.Hr()
        ]))
    
    return html.Div(progress_text, style={'fontWeight': 'bold'}), html.Div(playlist_html), not is_complete

@app.callback(
    Output('pb-download', 'data'),
    Input('pb-export-button', 'n_clicks'),
    State('pb-accepted-songs', 'data'),
    State('pb-song-dropdown', 'value'),
    prevent_initial_call=True
)
def export_playlist(n_clicks, accepted_songs, seed_song_artist):
    if not accepted_songs or not seed_song_artist:
        return None
    
    import io
    import csv
    
    seed_song, seed_artist = seed_song_artist.split('|')
    
    # Get seed song data from database
    conn = sqlite3.connect(db_path)
    seed_data = pd.read_sql(
        "SELECT Track_ID, Song, Artist, Album, Album_Year FROM tracks WHERE Track_Key = ?",
        conn,
        params=(f"{seed_artist}|{seed_song}",)
    )
    conn.close()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Track_ID', 'Song', 'Artist', 'Album', 'Year'])
    
    # Write seed song
    if not seed_data.empty:
        row = seed_data.iloc[0]
        writer.writerow([row['Track_ID'], row['Song'], row['Artist'], row['Album'], row['Album_Year']])
    
    # Write accepted songs
    for song in accepted_songs:
        writer.writerow([song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year']])
    
    output.seek(0)
    
    return dict(content=output.getvalue(), filename='playlist.csv', type='text/csv')

if __name__ == '__main__':
    app.run(debug=True)
