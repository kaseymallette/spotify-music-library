import sqlite3
import pandas as pd
import os

# Connect and create the database file
conn = sqlite3.connect('spotify_music_library.db')
data_folder = 'data'

# Loop through all files in the data folder
for filename in os.listdir(data_folder):
    if filename.endswith('.csv'):
        file_path = os.path.join(data_folder, filename)
        
        # Load the raw track data
        df = pd.read_csv(file_path)
        
        # Rename columns for SQL compatibility
        df = df.rename(columns={'#': 'Song_Number', 'Spotify Track Id': 'Track_ID'})
        
        # Extract album year from Album Date column
        df['Album_Year'] = df['Album Date'].str[:4].astype(int)

        # Create track_key column for unique track identification
        df['Track_Key'] = df['Artist'] + '|' + df['Song']
        
        # Extract playlist number and name from filename
        # Number is everything before the first underscore
        # Name is everything after the first underscore (minus .csv)
        playlist_number = filename.split('_')[0]
        playlist_name = filename.split('_', 1)[1].replace('.csv', '')
        
        # Add playlist metadata as columns
        df['playlist_number'] = playlist_number
        df['playlist_name'] = playlist_name
        
        # Append the data to the playlists table
        df.to_sql('playlists', conn, if_exists='append', index=False)

# Close the database connection
conn.close()
print("Database created and playlists table initialized.")