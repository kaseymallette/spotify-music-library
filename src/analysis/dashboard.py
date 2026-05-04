import sqlite3
import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, Input, Output
import os

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Query playlist names for dropdown
df_playlists = pd.read_sql("SELECT DISTINCT playlist_name FROM playlists ORDER BY playlist_name", conn)
playlist_options = df_playlists['playlist_name'].tolist()

# Query all data with decade calculation
df_all = pd.read_sql("""
    SELECT playlist_name, Album_Year, Artist, Song,
           BPM, Valence, Dance, Energy, Acoustic, 'Loud (DB)' as Loud_Db,
           Speech, Live, Popularity
    FROM playlists
    WHERE Album_Year IS NOT NULL
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
    
    html.H2("Feature Statistics"),
    html.Div(id='feature-stats', style={'marginBottom': '20px'}),
    
    html.H2("Song Count Distribution by Artist"),
    dcc.Graph(id='artist-song-chart'),
    
    html.H2("Decade Distribution"),
    dcc.Graph(id='decade-chart')
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
    Output('feature-stats', 'children'),
    Input('playlist-dropdown', 'value')
)
def update_feature_stats(selected_playlist):
    if selected_playlist == 'all':
        df_filtered = df_all
    else:
        df_filtered = df_all[df_all['playlist_name'] == selected_playlist]
    
    feature_stats = df_filtered[FEATURES].describe().loc[['mean', 'std']]
    
    return html.Table([
        html.Thead([
            html.Tr([html.Th('Feature')] + [html.Th(col) for col in feature_stats.columns])
        ]),
        html.Tbody([
            html.Tr([html.Td('Mean')] + [html.Td(f"{feature_stats.loc['mean', col]:.2f}") for col in feature_stats.columns]),
            html.Tr([html.Td('Std')] + [html.Td(f"{feature_stats.loc['std', col]:.2f}") for col in feature_stats.columns])
        ])
    ], style={'border': '1px solid #ddd', 'borderCollapse': 'collapse'})

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

if __name__ == '__main__':
    app.run(debug=True)
