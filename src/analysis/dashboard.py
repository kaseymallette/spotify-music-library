import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, State
import dash.dependencies
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
song_options = [{'label': f"{row['Song']} - {row['Artist']}", 'value': f"{row['Artist']}|{row['Song']}"} for _, row in df_songs.iterrows()]

conn.close()

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Spotify Playlist Builder"),
    
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
    
    html.Div([
        html.Label("Exclude songs from last N playlists:"),
        dcc.Dropdown(
            id='pb-exclude-playlists',
            options=[
                {'label': 'None', 'value': 0},
                {'label': 'Last 5 playlists', 'value': 5},
                {'label': 'Last 10 playlists', 'value': 10},
                {'label': 'All playlists', 'value': 999},
            ],
            value=0,
            style={'width': '300px'}
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Div([
        html.Label("Playlist Name:"),
        dcc.Input(
            id='pb-playlist-name',
            type='text',
            value='',
            placeholder="Auto-generated from seed song...",
            style={'width': '300px'}
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Button('Start Playlist Builder', id='pb-start-button', n_clicks=0, style={'marginBottom': '20px'}),
    
    html.Div(id='pb-current-song', style={'marginBottom': '20px'}),
    
    html.Div([
        html.Button('Accept Song', id='pb-accept-button', n_clicks=0, disabled=True, style={'marginRight': '10px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
        html.Button('Reject Song', id='pb-reject-button', n_clicks=0, disabled=True, style={'backgroundColor': '#f44336', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
    ], style={'marginBottom': '20px'}),
    
    html.Div(id='pb-progress', style={'marginBottom': '20px', 'fontSize': '18px'}),
    
    html.Div([
        html.Button('Export Playlist to CSV', id='pb-export-button', n_clicks=0, disabled=True, style={'marginRight': '10px', 'backgroundColor': '#2196F3', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
        html.Button('Save to Database', id='pb-save-db-button', n_clicks=0, disabled=True, style={'backgroundColor': '#9C27B0', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
    ], style={'marginBottom': '20px'}),
    html.Div(id='pb-save-status', style={'marginBottom': '20px', 'fontSize': '18px', 'color': 'green'}),
    dcc.Download(id='pb-download'),
    
    html.Div(id='pb-playlist'),
    
    html.Hr(),
    html.H2("Saved Playlists"),
    
    html.Div([
        html.Label("Select Playlist to View:"),
        dcc.Dropdown(
            id='saved-playlist-dropdown',
            options=[],
            value=None,
            placeholder="Select a playlist...",
            searchable=True
        ),
    ], style={'marginBottom': '15px'}),
    
    html.Div(id='selected-playlist-songs'),
    
    dcc.Store(id='selected-playlist-id'),
    
    dcc.Store(id='pb-knn-results'),
    dcc.Store(id='pb-current-index'),
    dcc.Store(id='pb-accepted-songs'),
    dcc.Store(id='pb-rejected-songs')
])

@app.callback(
    Output('pb-knn-results', 'data'),
    Output('pb-current-index', 'data'),
    Output('pb-accepted-songs', 'data'),
    Output('pb-rejected-songs', 'data'),
    Input('pb-start-button', 'n_clicks'),
    State('pb-song-dropdown', 'value'),
    State('pb-exclude-playlists', 'value')
)
def start_playlist_builder(n_clicks, selected_song_artist, exclude_playlists):
    if n_clicks == 0 or not selected_song_artist:
        return None, 0, [], []
    
    try:
        selected_artist, selected_song = selected_song_artist.split('|')
        
        conn = sqlite3.connect(db_path)
        
        # Get Track_Keys to exclude from last N playlists
        excluded_track_keys = set()
        if exclude_playlists and exclude_playlists > 0:
            df_exclude = pd.read_sql(f"""
                SELECT DISTINCT cps.track_key
                FROM custom_playlist_songs cps
                JOIN custom_playlists cp ON cps.playlist_id = cp.id
                WHERE cp.id IN (
                    SELECT id FROM custom_playlists
                    ORDER BY created_date DESC
                    LIMIT {exclude_playlists}
                )
            """, conn)
            excluded_track_keys = set(df_exclude['track_key'].tolist())
        
        df_metadata = pd.read_sql("""
            SELECT Track_Key, Track_ID, Song, Artist, Album, Album_Year, Popularity, Camelot
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
        seed_camelot = seed_row['Camelot']
        
        FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db']
        scaler = StandardScaler()
        df_features_scaled = scaler.fit_transform(df_features[FEATURES])
        
        valence_idx = FEATURES.index('Valence')
        df_features_scaled[:, valence_idx] *= 1.5
        
        # Apply BPM weighting (2x) to prioritize tempo similarity
        bpm_idx = FEATURES.index('BPM')
        df_features_scaled[:, bpm_idx] *= 2
        
        seed_idx = df_features.index.get_loc(seed_key)
        seed_features = df_features_scaled[seed_idx]
        
        distances = euclidean_distances([seed_features], df_features_scaled)[0]
        df_metadata['distance'] = distances
        df_metadata = df_metadata.sort_values('distance')
        df_metadata = df_metadata[df_metadata.index != seed_key]
        
        # Apply harmonic filter (always enabled)
        valid_keys = None
        if pd.notna(seed_camelot):
            conn = sqlite3.connect(db_path)
            try:
                df_valid_keys = pd.read_sql(
                    "SELECT DISTINCT target_key FROM mixing_rules WHERE starting_key = ?",
                    conn,
                    params=(seed_camelot,)
                )
                valid_keys = set(df_valid_keys['target_key'].tolist())
                df_metadata = df_metadata[df_metadata['Camelot'].isin(valid_keys)]
            finally:
                conn.close()
        else:
            print("Warning: Seed song has no Camelot key, harmonic filter disabled")
        
        # Convert to dict for storage
        knn_results = df_metadata.to_dict('records')
        
        # Filter out excluded songs
        if excluded_track_keys:
            knn_results = [song for song in knn_results if song['Track_Key'] not in excluded_track_keys]
        
        return knn_results, 0, [], []
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, 0, [], []

@app.callback(
    Output('pb-playlist-name', 'value'),
    Input('pb-song-dropdown', 'value')
)
def update_playlist_name(selected_song_artist):
    if not selected_song_artist:
        return ''
    seed_artist, seed_song = selected_song_artist.split('|')
    # Generate default playlist name: "Snap Out Of It"
    return seed_song

@app.callback(
    Output('pb-current-song', 'children'),
    Output('pb-accept-button', 'disabled'),
    Output('pb-reject-button', 'disabled'),
    Input('pb-knn-results', 'data'),
    Input('pb-current-index', 'data'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-rejected-songs', 'data'),
    Input('pb-target-size', 'value')
)
def update_current_song(knn_results, current_index, accepted_songs, rejected_songs, target_size):
    if not knn_results:
        return html.Div("Select a seed song and click 'Start Playlist Builder' to begin."), True, True
    
    current_count = 1 + len(accepted_songs) if accepted_songs else 1
    if current_count >= target_size:
        return html.H3("Playlist Complete!"), True, True
    
    if current_index >= len(knn_results):
        return html.H3("No more songs available!"), True, True
    
    current_song = knn_results[current_index]
    
    return html.Div([
        html.H3(f"Song {current_index + 2}:"),
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
    Output('pb-save-db-button', 'disabled'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-target-size', 'value'),
    State('pb-song-dropdown', 'value')
)
def update_progress_playlist(accepted_songs, target_size, seed_song_artist):
    if not accepted_songs:
        if seed_song_artist:
            return html.Div(f"Progress: 1/{target_size} songs (Seed song selected)"), html.Div(), True, True
        return html.Div(f"Progress: 0/{target_size} songs"), html.Div(), True, True
    
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
        seed_artist, seed_song = seed_song_artist.split('|')
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
    
    return html.Div(progress_text, style={'fontWeight': 'bold'}), html.Div(playlist_html), not is_complete, not is_complete

@app.callback(
    Output('pb-save-status', 'children'),
    Input('pb-save-db-button', 'n_clicks'),
    State('pb-accepted-songs', 'data'),
    State('pb-song-dropdown', 'value'),
    State('pb-playlist-name', 'value'),
    State('pb-target-size', 'value'),
    prevent_initial_call=True
)
def save_playlist_to_db(n_clicks, accepted_songs, seed_song_artist, playlist_name, target_size):
    if not accepted_songs or not seed_song_artist or not playlist_name:
        return html.Div("Please enter a playlist name and complete the playlist first.", style={'color': 'red'})
    
    try:
        from datetime import datetime
        
        seed_artist, seed_song = seed_song_artist.split('|')
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Insert playlist metadata
        created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO custom_playlists (playlist_name, seed_song, seed_artist, target_size, created_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (playlist_name, seed_song, seed_artist, target_size, created_date))
        
        playlist_id = cursor.lastrowid
        
        # Get audio features for seed song
        seed_data = pd.read_sql(
            "SELECT Track_Key, Track_ID, Song, Artist, Album, Album_Year, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity FROM tracks WHERE Track_Key = ?",
            conn,
            params=(f"{seed_artist}|{seed_song}",)
        )
        
        # Insert seed song
        if not seed_data.empty:
            row = seed_data.iloc[0]
            cursor.execute('''
                INSERT INTO custom_playlist_songs (playlist_id, track_number, track_key, track_id, song, artist, album, year, bpm, valence, dance, energy, acoustic, loud_db, distance, popularity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (playlist_id, 1, f"{row['Artist']}|{row['Song']}", row['Track_ID'], row['Song'], row['Artist'], row['Album'], row['Album_Year'], row['BPM'], row['Valence'], row['Dance'], row['Energy'], row['Acoustic'], row['Loud_Db'], 0.0, row['Popularity']))
        
        # Get audio features for accepted songs
        accepted_track_keys = [f"{song['Artist']}|{song['Song']}" for song in accepted_songs]
        if accepted_track_keys:
            accepted_features = pd.read_sql(
                f"SELECT Track_Key, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity FROM tracks WHERE Track_Key IN ({','.join(['?']*len(accepted_track_keys))})",
                conn,
                params=accepted_track_keys
            )
            accepted_features = accepted_features.set_index('Track_Key')
            
            # Insert accepted songs
            for i, song in enumerate(accepted_songs, 2):
                track_key = f"{song['Artist']}|{song['Song']}"
                if track_key in accepted_features.index:
                    features = accepted_features.loc[track_key]
                    cursor.execute('''
                        INSERT INTO custom_playlist_songs (playlist_id, track_number, track_key, track_id, song, artist, album, year, bpm, valence, dance, energy, acoustic, loud_db, distance, popularity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (playlist_id, i, track_key, song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year'], features['BPM'], features['Valence'], features['Dance'], features['Energy'], features['Acoustic'], features['Loud_Db'], song['distance'], features['Popularity']))
        
        conn.commit()
        conn.close()
        
        return html.Div(f"Playlist '{playlist_name}' saved to database successfully!", style={'color': 'green', 'fontWeight': 'bold'})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return html.Div(f"Error saving playlist: {str(e)}", style={'color': 'red'})

@app.callback(
    Output('saved-playlist-dropdown', 'options'),
    Input('pb-save-db-button', 'n_clicks'),
    prevent_initial_call=False
)
def update_playlist_dropdown(n_clicks):
    try:
        conn = sqlite3.connect(db_path)
        df_playlists = pd.read_sql("""
            SELECT id, playlist_name, seed_song, seed_artist, created_date
            FROM custom_playlists
            ORDER BY created_date DESC
        """, conn)
        conn.close()
        
        if df_playlists.empty:
            return []
        
        options = [
            {'label': f"{row['playlist_name']} (Seed: {row['seed_song']} by {row['seed_artist']})", 'value': row['id']}
            for _, row in df_playlists.iterrows()
        ]
        
        return options
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

@app.callback(
    Output('selected-playlist-songs', 'children'),
    Input('saved-playlist-dropdown', 'value'),
    prevent_initial_call=False
)
def display_playlist_songs(selected_playlist_id):
    if not selected_playlist_id:
        return html.P("Select a playlist to view its songs.")
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Get playlist info
        df_playlist = pd.read_sql(
            "SELECT playlist_name, seed_song, seed_artist, created_date FROM custom_playlists WHERE id = ?",
            conn,
            params=(selected_playlist_id,)
        )
        
        # Get songs
        df_songs = pd.read_sql("""
            SELECT track_number, song, artist, album, year, distance, popularity
            FROM custom_playlist_songs
            WHERE playlist_id = ?
            ORDER BY track_number
        """, conn, params=(selected_playlist_id,))
        conn.close()
        
        if df_playlist.empty:
            return html.P("Playlist not found.")
        
        playlist_name = df_playlist.iloc[0]['playlist_name']
        created_date = df_playlist.iloc[0]['created_date']
        
        # Build display
        songs_html = [
            html.H4(f"Playlist: {playlist_name}"),
            html.P(f"Created: {created_date}"),
            html.Hr()
        ]
        
        for _, song_row in df_songs.iterrows():
            # Convert binary data to integers if needed
            year_val = int.from_bytes(song_row['year'], byteorder='little', signed=False) if isinstance(song_row['year'], bytes) else song_row['year']
            pop_val = int.from_bytes(song_row['popularity'], byteorder='little', signed=False) if isinstance(song_row['popularity'], bytes) else song_row['popularity']
            
            songs_html.append(html.P(f"{song_row['track_number']}. {song_row['song']} — {song_row['artist']} ({year_val})", style={'fontWeight': 'bold'}))
            songs_html.append(html.P(f"   Distance: {song_row['distance']:.4f}, Popularity: {pop_val}"))
            songs_html.append(html.Hr())
        
        return html.Div(songs_html)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return html.Div(f"Error loading playlist: {str(e)}", style={'color': 'red'})

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
    
    seed_artist, seed_song = seed_song_artist.split('|')
    
    # Generate filename: snap_out_of_it.csv
    seed_song_filename = seed_song.lower().replace(' ', '_').replace('?', '').replace('!', '').replace('.', '')
    filename = f"{seed_song_filename}.csv"
    
    # Get seed song data from database
    conn = sqlite3.connect(db_path)
    seed_data = pd.read_sql(
        "SELECT Track_ID, Song, Artist, Album, Album_Year, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity FROM tracks WHERE Track_Key = ?",
        conn,
        params=(f"{seed_artist}|{seed_song}",)
    )
    
    # Get audio features for accepted songs
    accepted_track_keys = [f"{song['Artist']}|{song['Song']}" for song in accepted_songs]
    if accepted_track_keys:
        accepted_features = pd.read_sql(
            f"SELECT Track_Key, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity FROM tracks WHERE Track_Key IN ({','.join(['?']*len(accepted_track_keys))})",
            conn,
            params=accepted_track_keys
        )
        accepted_features = accepted_features.set_index('Track_Key')
    else:
        accepted_features = pd.DataFrame()
    
    conn.close()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Track_Number', 'Track_Key', 'Track_ID', 'Song', 'Artist', 'Album', 'Year', 'BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Distance', 'Popularity'])
    
    # Write seed song
    if not seed_data.empty:
        row = seed_data.iloc[0]
        writer.writerow([1, f"{row['Artist']}|{row['Song']}", row['Track_ID'], row['Song'], row['Artist'], row['Album'], row['Album_Year'], row['BPM'], row['Valence'], row['Dance'], row['Energy'], row['Acoustic'], row['Loud_Db'], 0.0000, row['Popularity']])
    
    # Write accepted songs
    for i, song in enumerate(accepted_songs, 2):
        track_key = f"{song['Artist']}|{song['Song']}"
        if track_key in accepted_features.index:
            features = accepted_features.loc[track_key]
            writer.writerow([i, track_key, song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year'], features['BPM'], features['Valence'], features['Dance'], features['Energy'], features['Acoustic'], features['Loud_Db'], song['distance'], features['Popularity']])
        else:
            # Fallback if features not found
            writer.writerow([i, track_key, song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year'], 0, 0, 0, 0, 0, 0, song['distance'], song['Popularity']])
    
    output.seek(0)
    
    return dict(content=output.getvalue(), filename=filename, type='text/csv')

if __name__ == '__main__':
    app.run(debug=True)
