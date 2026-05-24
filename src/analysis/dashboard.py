import sqlite3
import dash
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
artist_song_counts = df_songs.groupby('Artist')['Song'].nunique().to_dict()

conn.close()

# Create Dash app
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Spotify Playlist Builder"),

    html.H2("Nearest Neighbor Stats"),
    html.Div([
        html.Label("Select Song for Stats:"),
        dcc.Dropdown(
            id='pb-nn-song-dropdown',
            options=song_options,
            value=None,
            placeholder="Search for a song...",
            searchable=True
        ),
    ], style={'marginBottom': '15px'}),
    html.Div([
        html.Button('Show Nearest Neighbor Stats', id='pb-nn-stats-button', n_clicks=0, style={'backgroundColor': '#455A64', 'color': 'white', 'border': 'none', 'padding': '8px 16px'}),
    ], style={'marginBottom': '10px'}),
    html.Div(id='pb-nn-stats', style={'marginBottom': '20px'}),
    
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
        dcc.Checklist(
            id='pb-exclude-previous-playlists',
            options=[
                {'label': 'Exclude songs from previous playlists', 'value': 'exclude_previous'}
            ],
            value=[],
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
    html.Div(id='pb-exclusion-status', style={'marginBottom': '10px', 'fontStyle': 'italic'}),
    html.Div(id='pb-seed-stats', style={'marginBottom': '15px'}),
    
    html.Div(id='pb-current-song', style={'marginBottom': '20px'}),
    
    html.Div([
        html.Button('Previous 10 Songs', id='pb-prev-batch-button', n_clicks=0, disabled=True, style={'display': 'none', 'marginRight': '10px', 'backgroundColor': '#546E7A', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
        html.Button('Next 10 Songs', id='pb-next-batch-button', n_clicks=0, disabled=True, style={'display': 'none', 'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
    ], style={'marginBottom': '20px'}),

    html.Div(id='pb-progress', style={'marginBottom': '20px', 'fontSize': '18px'}),

    html.Div([
        html.Button('Export Playlist to CSV', id='pb-export-button', n_clicks=0, disabled=True, style={'marginRight': '10px', 'backgroundColor': '#2196F3', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
        html.Button('Save to Database', id='pb-save-db-button', n_clicks=0, disabled=True, style={'backgroundColor': '#9C27B0', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}),
    ], style={'marginBottom': '20px'}),
    html.Div(id='pb-save-status', style={'marginBottom': '20px', 'fontSize': '18px', 'color': 'green'}),
    dcc.Download(id='pb-download'),

    html.Hr(),

    html.Div(id='pb-artist-songs', style={'marginBottom': '20px'}),
    
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
    dcc.Store(id='pb-rejected-songs'),
    dcc.Store(id='pb-excluded-count')
])

@app.callback(
    Output('pb-knn-results', 'data'),
    Output('pb-current-index', 'data'),
    Output('pb-accepted-songs', 'data'),
    Output('pb-rejected-songs', 'data'),
    Output('pb-excluded-count', 'data'),
    Output('pb-seed-stats', 'children'),
    Input('pb-start-button', 'n_clicks'),
    State('pb-song-dropdown', 'value'),
    State('pb-exclude-previous-playlists', 'value'),
    prevent_initial_call=True
)
def start_playlist_builder(n_clicks, selected_song_artist, exclude_previous_playlists):
    if n_clicks == 0 or not selected_song_artist:
        return None, 0, [], [], None, html.Div()
    
    try:
        selected_artist, selected_song = selected_song_artist.split('|')
        
        conn = sqlite3.connect(db_path)
        
        # Get Track_Keys to exclude from all previous custom playlists
        excluded_track_keys = set()
        excluded_count = 0
        if exclude_previous_playlists and 'exclude_previous' in exclude_previous_playlists:
            try:
                df_exclude = pd.read_sql("""
                    SELECT DISTINCT cps.track_key
                    FROM custom_playlist_songs cps
                """, conn)
                if not df_exclude.empty:
                    excluded_track_keys = set(df_exclude['track_key'].tolist())
                    # Map excluded track keys to current normalized track keys
                    # Get all track keys from tracks table
                    df_all_tracks = pd.read_sql("SELECT Track_Key FROM tracks", conn)
                    all_track_keys = set(df_all_tracks['Track_Key'].tolist())
                    # Filter to only include track keys that exist in current tracks table
                    excluded_track_keys = excluded_track_keys & all_track_keys
                    excluded_count = len(excluded_track_keys)
            except Exception as e:
                print(f"Error getting excluded playlists: {e}")
                excluded_track_keys = set()
                excluded_count = 0
        
        df_metadata = pd.read_sql("""
            SELECT Track_Key, Track_ID, Song, Artist, Album, Album_Year, Popularity, Camelot,
                   BPM, Valence, Dance, Energy, Acoustic, "Loud (DB)" as Loud_Db
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
        
        # Add Track_Key back as a column for filtering
        df_metadata['Track_Key'] = df_metadata.index
        
        seed_key = f"{selected_artist}|{selected_song}"
        if seed_key not in df_metadata.index:
            return None, 0, [], [], None, html.Div("Seed song not found in tracks table.", style={'color': '#f44336'})
        
        seed_row = df_metadata.loc[seed_key]
        seed_camelot = seed_row['Camelot']

        # Prepare seed song stats for display
        seed_stats = [
            html.H4("Seed Song Stats", style={'marginBottom': '8px'}),
            html.P(f"0. {seed_row['Song']} — {seed_row['Artist']} ({seed_row['Album_Year']}) [ORIGINAL]", style={'fontWeight': 'bold', 'fontSize': '18px'}),
            html.P(f"   Distance: 0.0000"),
            html.P(f"   Popularity: {seed_row['Popularity']}"),
            html.P(f"   Features: BPM={seed_row['BPM']}, Valence={seed_row['Valence']}, Dance={seed_row['Dance']}, Energy={seed_row['Energy']}, Acoustic={seed_row['Acoustic']}, Loud_Db={seed_row['Loud_Db']}, Key={seed_camelot}")
        ]
        
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

        # Cap candidates to distance <= 3
        df_metadata = df_metadata[df_metadata['distance'] <= 3]
        
        # Convert to dict for storage
        knn_results = df_metadata.to_dict('records')

        # Normalize Track_Key so dynamic button IDs are always stable/valid
        for song in knn_results:
            track_key = song.get('Track_Key')
            if pd.isna(track_key) or track_key is None or str(track_key).strip() == '':
                song['Track_Key'] = f"{song.get('Artist', '')}|{song.get('Song', '')}"
            else:
                song['Track_Key'] = str(track_key)
        
        # Filter out excluded songs
        if excluded_track_keys:
            knn_results = [song for song in knn_results if song.get('Track_Key') not in excluded_track_keys]
        
        return knn_results, 0, [], [], excluded_count, html.Div(seed_stats)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, 0, [], [], None, html.Div(f"Error: {e}", style={'color': '#f44336'})

@app.callback(
    Output('pb-exclusion-status', 'children'),
    Input('pb-excluded-count', 'data')
)
def update_exclusion_status(excluded_count):
    if excluded_count is None:
        return ""
    if excluded_count == 0:
        return "No songs were excluded from previous playlists."
    return f"Excluded {excluded_count} songs from previous playlists."

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
    Output('pb-nn-stats', 'children', allow_duplicate=True),
    Input('pb-nn-stats-button', 'n_clicks'),
    State('pb-nn-song-dropdown', 'value'),
    prevent_initial_call=True
)
def show_nn_stats(n_clicks, selected_song_artist):
    if not selected_song_artist:
        return html.Div("Select a seed song first.", style={'color': '#f44336'})

    try:
        selected_artist, selected_song = selected_song_artist.split('|')
        seed_key = f"{selected_artist}|{selected_song}"

        conn = sqlite3.connect(db_path)
        df_metadata = pd.read_sql("""
            SELECT Track_Key, Song, Artist, Camelot,
                   BPM, Valence, Dance, Energy, Acoustic, "Loud (DB)" as Loud_Db
            FROM tracks
            WHERE Album_Year IS NOT NULL
        """, conn)

        df_features = df_metadata[['Track_Key', 'BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db']].copy()
        df_metadata = df_metadata.set_index('Track_Key')
        df_features = df_features.set_index('Track_Key')

        if seed_key not in df_metadata.index:
            conn.close()
            return html.Div("Seed song not found in tracks table.", style={'color': '#f44336'})

        seed_camelot = df_metadata.loc[seed_key]['Camelot']

        features = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db']
        scaler = StandardScaler()
        df_features_scaled = scaler.fit_transform(df_features[features])

        valence_idx = features.index('Valence')
        bpm_idx = features.index('BPM')
        df_features_scaled[:, valence_idx] *= 1.5
        df_features_scaled[:, bpm_idx] *= 2

        seed_idx = df_features.index.get_loc(seed_key)
        seed_features = df_features_scaled[seed_idx]

        distances = euclidean_distances([seed_features], df_features_scaled)[0]
        df_metadata['distance'] = distances
        df_metadata = df_metadata[df_metadata.index != seed_key]

        # Apply harmonic filter (always enabled in builder)
        if pd.notna(seed_camelot):
            df_valid_keys = pd.read_sql(
                "SELECT DISTINCT target_key FROM mixing_rules WHERE starting_key = ?",
                conn,
                params=(seed_camelot,)
            )
            valid_keys = set(df_valid_keys['target_key'].tolist())
            df_metadata = df_metadata[df_metadata['Camelot'].isin(valid_keys)]

        conn.close()

        total_eligible_after_harmonic = int(len(df_metadata))
        df_within_3 = df_metadata[df_metadata['distance'] <= 3]
        total_eligible_within_3 = int(len(df_within_3))

        bucket_counts = {
            '0-1': int(((df_within_3['distance'] > 0) & (df_within_3['distance'] <= 1)).sum()),
            '1-2': int(((df_within_3['distance'] > 1) & (df_within_3['distance'] <= 2)).sum()),
            '2-3': int(((df_within_3['distance'] > 2) & (df_within_3['distance'] <= 3)).sum())
        }

        df_buckets = pd.DataFrame({
            'Distance Bucket': list(bucket_counts.keys()),
            'Song Count': list(bucket_counts.values())
        })
        fig_buckets = px.bar(
            df_buckets,
            x='Distance Bucket',
            y='Song Count',
            title='Eligible Songs by Distance Range',
            color='Distance Bucket',
            color_discrete_sequence=['#4CAF50', '#FFC107', '#FF9800']
        )
        fig_buckets.update_layout(showlegend=False, margin=dict(l=20, r=20, t=45, b=20), height=300)

        return html.Div([
            html.H4("Nearest Neighbor Stats"),
            html.P(f"Eligible songs after harmonic filtering: {total_eligible_after_harmonic}"),
            html.P(f"Songs with Distance <= 3.0: {total_eligible_within_3}"),
            html.P(f"Distance 0-1: {bucket_counts['0-1']}"),
            html.P(f"Distance 1-2: {bucket_counts['1-2']}"),
            html.P(f"Distance 2-3: {bucket_counts['2-3']}"),
            dcc.Graph(figure=fig_buckets, config={'displayModeBar': False}),
        ], style={'backgroundColor': '#f5f5f5', 'padding': '10px', 'borderRadius': '6px'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return html.Div(f"Error calculating nearest neighbor stats: {str(e)}", style={'color': '#f44336'})

@app.callback(
    Output('pb-current-song', 'children'),
    Output('pb-prev-batch-button', 'disabled'),
    Output('pb-next-batch-button', 'disabled'),
    Output('pb-prev-batch-button', 'style'),
    Output('pb-next-batch-button', 'style'),
    Input('pb-knn-results', 'data'),
    Input('pb-current-index', 'data'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-rejected-songs', 'data'),
    Input('pb-target-size', 'value')
)
def update_current_song(knn_results, current_index, accepted_songs, rejected_songs, target_size):
    prev_style_visible = {'marginRight': '10px', 'backgroundColor': '#546E7A', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}
    next_style_visible = {'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'padding': '10px 20px'}
    hidden_style = {'display': 'none'}

    if not knn_results:
        return html.Div("Select a seed song and click 'Start Playlist Builder' to begin."), True, True, hidden_style, hidden_style

    if accepted_songs is None:
        accepted_songs = []
    if rejected_songs is None:
        rejected_songs = []
    
    current_count = 1 + len(accepted_songs) if accepted_songs else 1
    if current_count >= target_size:
        return html.H3("Playlist Complete!"), True, True, hidden_style, hidden_style
    
    if current_index >= len(knn_results):
        prev_disabled = current_index <= 0
        prev_style = prev_style_visible if current_index > 0 else hidden_style
        return html.H3("No more songs available!"), prev_disabled, True, prev_style, hidden_style
    
    batch_end = min(current_index + 10, len(knn_results))
    current_batch = knn_results[current_index:batch_end]

    batch_html = [
        html.H3(f"Candidate Songs {current_index + 1}-{batch_end}"),
        html.P("Select songs in any order from this batch.", style={'fontStyle': 'italic'})
    ]

    accepted_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in accepted_songs)
    rejected_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in rejected_songs)
    for i, song in enumerate(current_batch, start=current_index + 1):
        track_key = song.get('Track_Key', f"{song['Artist']}|{song['Song']}")
        already_selected = track_key in accepted_keys
        already_rejected = track_key in rejected_keys

        select_disabled = already_selected or already_rejected
        reject_disabled = already_selected or already_rejected
        select_label = 'Selected' if already_selected else ('Unavailable' if already_rejected else 'Select')
        reject_label = 'Rejected' if already_rejected else 'Reject'

        batch_html.append(html.Div([
            html.P(f"{i}. {song['Song']} — {song['Artist']} ({song['Album_Year']})", style={'fontSize': '18px', 'fontWeight': 'bold', 'marginBottom': '2px'}),
            html.P(f"Distance: {song['distance']:.4f} | Popularity: {song['Popularity']}", style={'marginBottom': '8px'}),
            html.P(f"Features: BPM={song['BPM']}, Valence={song['Valence']}, Dance={song['Dance']}, Energy={song['Energy']}, Acoustic={song['Acoustic']}, Loud_Db={song['Loud_Db']}, Key={song['Camelot']}", style={'marginBottom': '8px'}),
            html.Div([
                html.Button(
                    select_label,
                    id={'type': 'pb-select-song', 'index': i - 1},
                    n_clicks=0,
                    disabled=select_disabled,
                    style={'marginRight': '8px', 'marginBottom': '10px', 'backgroundColor': '#4CAF50' if not select_disabled else '#9E9E9E', 'color': 'white', 'border': 'none', 'padding': '8px 16px'}
                ),
                html.Button(
                    reject_label,
                    id={'type': 'pb-reject-song', 'index': i - 1},
                    n_clicks=0,
                    disabled=reject_disabled,
                    style={'marginBottom': '10px', 'backgroundColor': '#f44336' if not reject_disabled else '#9E9E9E', 'color': 'white', 'border': 'none', 'padding': '8px 16px'}
                ),
            ]),
            html.Hr()
        ]))

    prev_disabled = current_index <= 0
    next_disabled = batch_end >= len(knn_results)
    prev_style = prev_style_visible if current_index > 0 else hidden_style
    next_style = next_style_visible if not next_disabled else hidden_style
    return html.Div(batch_html), prev_disabled, next_disabled, prev_style, next_style

@app.callback(
    Output('pb-accepted-songs', 'data', allow_duplicate=True),
    Input({'type': 'pb-select-song', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('pb-knn-results', 'data'),
    State('pb-current-index', 'data'),
    State('pb-accepted-songs', 'data'),
    State('pb-target-size', 'value'),
    prevent_initial_call=True
)
def select_song_from_batch(n_clicks_list, knn_results, current_index, accepted_songs, target_size):
    if not knn_results or current_index >= len(knn_results):
        return accepted_songs

    if accepted_songs is None:
        accepted_songs = []

    if not target_size:
        target_size = 50

    triggered = dash.callback_context.triggered
    if not triggered:
        return accepted_songs
    if not triggered[0].get('value'):
        return accepted_songs

    import json
    triggered_id = triggered[0]['prop_id'].split('.')[0]
    try:
        triggered_id = json.loads(triggered_id)
    except Exception:
        return accepted_songs

    selected_index = triggered_id.get('index')
    if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(knn_results):
        return accepted_songs

    if len(accepted_songs) >= (target_size - 1):
        return accepted_songs

    selected_song = knn_results[selected_index]
    selected_track_key = selected_song.get('Track_Key', f"{selected_song['Artist']}|{selected_song['Song']}")

    accepted_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in accepted_songs)
    if selected_track_key in accepted_keys:
        return accepted_songs

    new_accepted = accepted_songs.copy()
    new_accepted.append(selected_song)
    return new_accepted

@app.callback(
    Output('pb-rejected-songs', 'data', allow_duplicate=True),
    Input({'type': 'pb-reject-song', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('pb-knn-results', 'data'),
    State('pb-current-index', 'data'),
    State('pb-rejected-songs', 'data'),
    State('pb-accepted-songs', 'data'),
    prevent_initial_call=True
)
def reject_song_from_batch(n_clicks_list, knn_results, current_index, rejected_songs, accepted_songs):
    if not knn_results or current_index >= len(knn_results):
        return rejected_songs

    if rejected_songs is None:
        rejected_songs = []
    if accepted_songs is None:
        accepted_songs = []

    triggered = dash.callback_context.triggered
    if not triggered:
        return rejected_songs
    if not triggered[0].get('value'):
        return rejected_songs

    import json
    triggered_id = triggered[0]['prop_id'].split('.')[0]
    try:
        triggered_id = json.loads(triggered_id)
    except Exception:
        return rejected_songs

    rejected_index = triggered_id.get('index')
    if not isinstance(rejected_index, int) or rejected_index < 0 or rejected_index >= len(knn_results):
        return rejected_songs

    rejected_song = knn_results[rejected_index]
    rejected_track_key = rejected_song.get('Track_Key', f"{rejected_song['Artist']}|{rejected_song['Song']}")

    accepted_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in accepted_songs)
    rejected_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in rejected_songs)
    if rejected_track_key in accepted_keys or rejected_track_key in rejected_keys:
        return rejected_songs

    new_rejected = rejected_songs.copy()
    new_rejected.append(rejected_song)
    return new_rejected

@app.callback(
    Output('pb-current-index', 'data', allow_duplicate=True),
    Input('pb-next-batch-button', 'n_clicks'),
    State('pb-current-index', 'data'),
    State('pb-knn-results', 'data'),
    prevent_initial_call=True
)
def next_batch(n_clicks, current_index, knn_results):
    if not knn_results or current_index >= len(knn_results):
        return current_index

    return min(current_index + 10, len(knn_results))

@app.callback(
    Output('pb-current-index', 'data', allow_duplicate=True),
    Input('pb-prev-batch-button', 'n_clicks'),
    State('pb-current-index', 'data'),
    prevent_initial_call=True
)
def previous_batch(n_clicks, current_index):
    if current_index <= 0:
        return 0

    return max(current_index - 10, 0)

@app.callback(
    Output('pb-artist-songs', 'children'),
    Input('pb-knn-results', 'data'),
    Input('pb-song-dropdown', 'value'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-rejected-songs', 'data')
)
def update_artist_songs(knn_results, seed_song_artist, accepted_songs, rejected_songs):
    if not seed_song_artist:
        return html.Div()

    seed_artist, _ = seed_song_artist.split('|')
    accepted_songs = accepted_songs or []
    rejected_songs = rejected_songs or []

    if not knn_results:
        return html.Div()

    same_artist_candidates = [song for song in knn_results if song.get('Artist') == seed_artist]
    accepted_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in accepted_songs)
    rejected_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in rejected_songs)

    section = [
        html.H3(f"Other Songs by {seed_artist} (Eligible Keys and Distance)"),
        html.P("Use the Candidate Songs section above to Select/Reject songs.", style={'fontStyle': 'italic', 'color': '#666'})
    ]

    if same_artist_candidates:
        for i, song in enumerate(same_artist_candidates[:10], 1):
            track_key = song.get('Track_Key', f"{song['Artist']}|{song['Song']}")
            status = ""
            status_style = {}
            if track_key in accepted_keys:
                status = " [Selected]"
                status_style = {'color': '#4CAF50', 'fontWeight': 'bold'}
            elif track_key in rejected_keys:
                status = " [Rejected]"
                status_style = {'color': '#f44336', 'fontWeight': 'bold'}

            section.append(html.Div([
                html.P(f"{i}. {song['Song']} ({song['Album_Year']})", style={'fontWeight': 'bold', 'display': 'inline'}),
                html.Span(status, style=status_style),
                html.P(f"   Distance: {song['distance']:.4f}, Popularity: {song['Popularity']}"),
                html.P(f"   Features: BPM={song['BPM']}, Valence={song['Valence']}, Dance={song['Dance']}, Energy={song['Energy']}, Acoustic={song['Acoustic']}, Loud_Db={song['Loud_Db']}, Key={song['Camelot']}"),
                html.Hr()
            ]))
    else:
        artist_total = artist_song_counts.get(seed_artist, 0)
        if artist_total <= 1:
            section.append(html.P("No other songs by artist in library.", style={'fontStyle': 'italic'}))
        else:
            section.append(html.P("No other songs by this artist in the eligible harmonic keys.", style={'fontStyle': 'italic'}))

    return html.Div(section)

@app.callback(
    Output('pb-progress', 'children'),
    Output('pb-playlist', 'children'),
    Output('pb-export-button', 'disabled'),
    Output('pb-save-db-button', 'disabled'),
    Input('pb-accepted-songs', 'data'),
    Input('pb-rejected-songs', 'data'),
    Input('pb-target-size', 'value'),
    State('pb-song-dropdown', 'value')
)
def update_progress_playlist(accepted_songs, rejected_songs, target_size, seed_song_artist):
    if accepted_songs is None:
        accepted_songs = []
    if rejected_songs is None:
        rejected_songs = []

    if not target_size:
        target_size = 50

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
    for accepted_idx, song in enumerate(accepted_songs):
        display_num = accepted_idx + 2
        move_up_disabled = accepted_idx == 0
        move_down_disabled = accepted_idx == len(accepted_songs) - 1
        playlist_html.append(html.Div([
            html.P(f"{display_num}. {song['Song']} — {song['Artist']} ({song['Album_Year']})", style={'fontWeight': 'bold'}),
            html.P(f"   Distance: {song['distance']:.4f}, Popularity: {song['Popularity']}"),
            html.P(f"   Features: BPM={song['BPM']}, Valence={song['Valence']}, Dance={song['Dance']}, Energy={song['Energy']}, Acoustic={song['Acoustic']}, Loud_Db={song['Loud_Db']}, Key={song['Camelot']}"),
            html.Div([
                html.Button(
                    'Up',
                    id={'type': 'pb-move-up', 'index': accepted_idx},
                    n_clicks=0,
                    disabled=move_up_disabled,
                    style={'marginRight': '8px', 'backgroundColor': '#1E88E5', 'color': 'white', 'border': 'none', 'padding': '6px 12px'}
                ),
                html.Button(
                    'Down',
                    id={'type': 'pb-move-down', 'index': accepted_idx},
                    n_clicks=0,
                    disabled=move_down_disabled,
                    style={'backgroundColor': '#7C4DFF', 'color': 'white', 'border': 'none', 'padding': '6px 12px'}
                ),
                html.Button(
                    'Remove',
                    id={'type': 'pb-remove-accepted', 'index': accepted_idx},
                    n_clicks=0,
                    style={'marginLeft': '8px', 'backgroundColor': '#f44336', 'color': 'white', 'border': 'none', 'padding': '6px 12px'}
                )
            ], style={'marginBottom': '8px'}),
            html.Hr()
        ]))

    # Add rejected songs section
    if rejected_songs:
        playlist_html.append(html.H3("Rejected Songs:"))
        playlist_html.append(html.Hr())
        for song in rejected_songs:
            playlist_html.append(html.Div([
                html.P(f"{song['Song']} — {song['Artist']} ({song['Album_Year']})", style={'fontWeight': 'bold', 'color': '#f44336'}),
                html.P(f"   Distance: {song['distance']:.4f}, Popularity: {song['Popularity']}"),
                html.P(f"   Features: BPM={song['BPM']}, Valence={song['Valence']}, Dance={song['Dance']}, Energy={song['Energy']}, Acoustic={song['Acoustic']}, Loud_Db={song['Loud_Db']}, Key={song['Camelot']}"),
                html.Button(
                    'Add',
                    id={'type': 'pb-add-rejected', 'index': f"{song['Artist']}|{song['Song']}"},
                    n_clicks=0,
                    style={'marginBottom': '8px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'padding': '6px 12px'}
                ),
                html.Hr()
            ]))
    
    return html.Div(progress_text, style={'fontWeight': 'bold'}), html.Div(playlist_html), not is_complete, not is_complete

@app.callback(
    Output('pb-accepted-songs', 'data', allow_duplicate=True),
    Input({'type': 'pb-move-up', 'index': dash.dependencies.ALL}, 'n_clicks'),
    Input({'type': 'pb-move-down', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('pb-accepted-songs', 'data'),
    prevent_initial_call=True
)
def reorder_accepted_songs(move_up_clicks, move_down_clicks, accepted_songs):
    if not accepted_songs or len(accepted_songs) < 2:
        return accepted_songs

    triggered = dash.callback_context.triggered
    if not triggered:
        return accepted_songs
    if not triggered[0].get('value'):
        return accepted_songs

    import json
    triggered_id = triggered[0]['prop_id'].split('.')[0]
    try:
        triggered_id = json.loads(triggered_id)
    except Exception:
        return accepted_songs

    move_type = triggered_id.get('type')
    idx = triggered_id.get('index')
    if not isinstance(idx, int):
        return accepted_songs

    new_accepted = accepted_songs.copy()
    if move_type == 'pb-move-up' and idx > 0:
        new_accepted[idx - 1], new_accepted[idx] = new_accepted[idx], new_accepted[idx - 1]
    elif move_type == 'pb-move-down' and idx < len(new_accepted) - 1:
        new_accepted[idx], new_accepted[idx + 1] = new_accepted[idx + 1], new_accepted[idx]

    return new_accepted

@app.callback(
    Output('pb-accepted-songs', 'data', allow_duplicate=True),
    Output('pb-rejected-songs', 'data', allow_duplicate=True),
    Input({'type': 'pb-remove-accepted', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('pb-accepted-songs', 'data'),
    State('pb-rejected-songs', 'data'),
    prevent_initial_call=True
)
def remove_accepted_song(n_clicks_list, accepted_songs, rejected_songs):
    if not accepted_songs:
        return accepted_songs, rejected_songs

    if rejected_songs is None:
        rejected_songs = []

    triggered = dash.callback_context.triggered
    if not triggered:
        return accepted_songs, rejected_songs
    if not triggered[0].get('value'):
        return accepted_songs, rejected_songs

    import json
    triggered_id = triggered[0]['prop_id'].split('.')[0]
    try:
        triggered_id = json.loads(triggered_id)
    except Exception:
        return accepted_songs, rejected_songs

    idx = triggered_id.get('index')
    if not isinstance(idx, int) or idx < 0 or idx >= len(accepted_songs):
        return accepted_songs, rejected_songs

    new_accepted = accepted_songs.copy()
    removed_song = new_accepted.pop(idx)

    removed_key = removed_song.get('Track_Key', f"{removed_song['Artist']}|{removed_song['Song']}")
    rejected_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in rejected_songs)
    new_rejected = rejected_songs.copy()
    if removed_key not in rejected_keys:
        new_rejected.append(removed_song)

    return new_accepted, new_rejected

@app.callback(
    Output('pb-accepted-songs', 'data', allow_duplicate=True),
    Output('pb-rejected-songs', 'data', allow_duplicate=True),
    Input({'type': 'pb-add-rejected', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State('pb-accepted-songs', 'data'),
    State('pb-rejected-songs', 'data'),
    prevent_initial_call=True
)
def add_rejected_song(n_clicks_list, accepted_songs, rejected_songs):
    if rejected_songs is None or not rejected_songs:
        return accepted_songs, rejected_songs

    if accepted_songs is None:
        accepted_songs = []

    triggered = dash.callback_context.triggered
    if not triggered:
        return accepted_songs, rejected_songs
    if not triggered[0].get('value'):
        return accepted_songs, rejected_songs

    import json
    triggered_id = triggered[0]['prop_id'].split('.')[0]
    try:
        triggered_id = json.loads(triggered_id)
    except Exception:
        return accepted_songs, rejected_songs

    track_key = triggered_id.get('index')
    if not track_key:
        return accepted_songs, rejected_songs

    song_to_add = None
    new_rejected = []
    for song in rejected_songs:
        song_key = song.get('Track_Key', f"{song['Artist']}|{song['Song']}")
        if song_key == track_key and song_to_add is None:
            song_to_add = song
        else:
            new_rejected.append(song)

    if song_to_add is None:
        return accepted_songs, rejected_songs

    accepted_keys = set(song.get('Track_Key', f"{song['Artist']}|{song['Song']}") for song in accepted_songs)
    if track_key in accepted_keys:
        return accepted_songs, new_rejected

    new_accepted = accepted_songs.copy()
    new_accepted.append(song_to_add)

    return new_accepted, new_rejected

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
            "SELECT Track_Key, Track_ID, Song, Artist, Album, Album_Year, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity, Camelot FROM tracks WHERE Track_Key = ?",
            conn,
            params=(f"{seed_artist}|{seed_song}",)
        )
        
        # Insert seed song
        if not seed_data.empty:
            row = seed_data.iloc[0]
            cursor.execute('''
                INSERT INTO custom_playlist_songs (playlist_id, track_number, track_key, track_id, song, artist, album, year, bpm, valence, dance, energy, acoustic, loud_db, camelot, distance, popularity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (playlist_id, 1, f"{row['Artist']}|{row['Song']}", row['Track_ID'], row['Song'], row['Artist'], row['Album'], row['Album_Year'], row['BPM'], row['Valence'], row['Dance'], row['Energy'], row['Acoustic'], row['Loud_Db'], row['Camelot'], 0.0, row['Popularity']))
        
        # Get audio features for accepted songs
        accepted_track_keys = [f"{song['Artist']}|{song['Song']}" for song in accepted_songs]
        if accepted_track_keys:
            accepted_features = pd.read_sql(
                f"SELECT Track_Key, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity, Camelot FROM tracks WHERE Track_Key IN ({','.join(['?']*len(accepted_track_keys))})",
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
                        INSERT INTO custom_playlist_songs (playlist_id, track_number, track_key, track_id, song, artist, album, year, bpm, valence, dance, energy, acoustic, loud_db, camelot, distance, popularity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (playlist_id, i, track_key, song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year'], features['BPM'], features['Valence'], features['Dance'], features['Energy'], features['Acoustic'], features['Loud_Db'], features['Camelot'], song['distance'], features['Popularity']))
        
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
        "SELECT Track_ID, Song, Artist, Album, Album_Year, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity, Camelot FROM tracks WHERE Track_Key = ?",
        conn,
        params=(f"{seed_artist}|{seed_song}",)
    )
    
    # Get audio features for accepted songs
    accepted_track_keys = [f"{song['Artist']}|{song['Song']}" for song in accepted_songs]
    if accepted_track_keys:
        accepted_features = pd.read_sql(
            f"SELECT Track_Key, BPM, Valence, Dance, Energy, Acoustic, \"Loud (DB)\" as Loud_Db, Popularity, Camelot FROM tracks WHERE Track_Key IN ({','.join(['?']*len(accepted_track_keys))})",
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
    writer.writerow(['Track_Number', 'Track_Key', 'Track_ID', 'Song', 'Artist', 'Album', 'Year', 'BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Camelot', 'Distance', 'Popularity'])
    
    # Write seed song
    if not seed_data.empty:
        row = seed_data.iloc[0]
        writer.writerow([1, f"{row['Artist']}|{row['Song']}", row['Track_ID'], row['Song'], row['Artist'], row['Album'], row['Album_Year'], row['BPM'], row['Valence'], row['Dance'], row['Energy'], row['Acoustic'], row['Loud_Db'], row['Camelot'], 0.0000, row['Popularity']])
    
    # Write accepted songs
    for i, song in enumerate(accepted_songs, 2):
        track_key = f"{song['Artist']}|{song['Song']}"
        if track_key in accepted_features.index:
            features = accepted_features.loc[track_key]
            writer.writerow([i, track_key, song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year'], features['BPM'], features['Valence'], features['Dance'], features['Energy'], features['Acoustic'], features['Loud_Db'], features['Camelot'], song['distance'], features['Popularity']])
        else:
            # Fallback if features not found
            writer.writerow([i, track_key, song['Track_ID'], song['Song'], song['Artist'], song['Album'], song['Album_Year'], 0, 0, 0, 0, 0, 0, '', song['distance'], song['Popularity']])
    
    output.seek(0)
    
    return dict(content=output.getvalue(), filename=filename, type='text/csv')

if __name__ == '__main__':
    app.run(debug=True)
