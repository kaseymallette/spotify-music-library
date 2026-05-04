# spotify-music-library
A Spotify-powered music recommendation system using clustering analysis and automated playlist generation to help discover new music and avoid repetition.

## Project Structure

```
.
├── README.md
├── data/
├── images/
├── requirements.txt
├── spotify_music_library.db
└── src/
    ├── analysis/
    │   ├── sample_queries.py
    │   └── visualize_distributions.py
    └── db/
        ├── create_artist_playlist_count.py
        ├── create_playlists.py
        ├── create_song_playlist_count.py
        ├── create_tracks.py
        └── setup_database.py
```

## Database Setup

The `src/db/create_playlists.py` script ingests CSV files from 50 Spotify playlists into a SQLite database. The script:

- Reads all CSV files from the `data/` folder
- Extracts playlist number and name from filenames (format: `number_name.csv`)
- Adds metadata columns: `playlist_number`, `playlist_name`, `Album_Year`, and `Track_Key`
- Renames columns for SQL compatibility: `#` → `Song_Number`, `Spotify Track Id` → `Track_ID`
- Appends all data to a `playlists` table in `spotify_music_library.db`

### Setup Commands

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

Run the `src/db/setup_database.py` script to run all database setup steps in sequence:

```bash
python src/db/setup_database.py
```

This will:
1. Create the playlists table from CSV files
2. Deduplicate tracks and create the tracks table
3. Create the song playlist count table
4. Create the artist playlist count table

If you've added new CSV files to the `data/` folder, remove the existing database first:

```bash
rm spotify_music_library.db
```

**Output:**
```
=== Spotify Music Library Database Setup ===


--- Create playlists table from CSV files ---
Running create_playlists.py...
Database created: spotify_music_library.db
Playlists table created successfully.
Number of playlists: 50
Row count: 9543
✓ create_playlists.py completed successfully

--- Deduplicate tracks and create tracks table ---
Running create_tracks.py...
Unique Track_IDs: 5757
Unique Track_Keys: 5231
Unique Artists: 2027
Removed: 526 duplicate tracks (same song, different Track_ID)
Tracks table created with unique tracks sorted by Artist, Song.
✓ create_tracks.py completed successfully

--- Create song playlist count table ---
Running create_song_playlist_count.py...
Total unique songs: 5231
Songs in multiple playlists: 2265
Maximum playlists per song: 11
Song playlist count table created successfully.
✓ create_song_playlist_count.py completed successfully

--- Create artist playlist count table ---
Running create_artist_playlist_count.py...
Total unique artists: 2027
Artists in multiple playlists: 1069
Maximum playlists per artist: 18
Artist playlist count table created successfully.
✓ create_artist_playlist_count.py completed successfully

=== Database Setup Complete ===
All database tables have been created successfully.
```

### Sample Queries

You can run all sample queries at once using the `src/analysis/sample_queries.py` script:

```bash
python src/analysis/sample_queries.py
```

**Get number of unique playlists:**
50

**Get number of unique artists:**
2027

**Get number of unique songs:**
5231

**Get top five artists with song count:**
```
Backstreet Boys|107
OneRepublic|88
Maroon 5|70
Matt Maeson|64
Daughter|58
```

**Get top 5 songs by playlist count:**
```
Kenny Loggins - Danger Zone - From  Top Gun  Original Soundtrack: 11 playlists
The Fray - Singing Low: 10 playlists
50 Cent,Justin Timberlake,Timbaland - Ayo Technology: 8 playlists
Arctic Monkeys - Do I Wanna Know?: 8 playlists
Blue Foundation - Eyes on Fire: 8 playlists
```

**Get top 5 artists by playlist count:**
```
Rainbow Kitten Surprise: 18 playlists
Britney Spears: 18 playlists
OneRepublic: 17 playlists
Matt Maeson: 17 playlists
The Fray: 16 playlists
```

**Get songs from playlist 01:**
```
1|Temporary Love|The Brinks|2015
2|Basic Instinct|The Acid|2014
3|Stressed Out|Twenty One Pilots|2015
4|Genghis Khan|Miike Snow|2015
5|Carl Sagan|Night Moves|2016
6|Ophelia|The Lumineers|2016
7|Nobody Dies|Thao & The Get Down Stay Down|2015
8|Little Numbers - Acoustic Version|BOY|2013
9|I'm a Mess|Ed Sheeran|2014
10|Devil Devil|MILCK|2016
11|Cliff|Låpsley|2016
12|Middle|DJ Snake,Bipolar Sunshine|2015
```

## Analysis

### Data Distribution

The `src/analysis/visualize_distributions.py` script generates charts to analyze the library's composition and identify patterns:

- **Artist Distribution:** 47.3% of artists appear in only one playlist, suggesting a wide artist range across the library rather than repeated reuse.
- **Track Distribution:** 56.7% of songs are unique to a single playlist, indicating that playlists tend to function as distinct collections rather than overlapping selections.
- **Playlist Composition:**
  - Artist density: 44% of playlists contain fewer than 50 unique artists, while 6% of playlists contain more than 200 unique artists.
  - Track volume: 18% of playlists have fewer than 50 songs and 8% of playlists exceed 500 tracks; the majority vary in size, between 50-500 songs.

**Run script:**
```bash
python src/analysis/visualize_distributions.py
```

**Output:**
![Distributions Chart](images/distributions.png)

- Prints statistics for artist and song playlist count distributions

### Interactive Dashboard

The `src/analysis/dashboard.py` script creates an interactive Plotly Dash dashboard to explore playlist statistics:

- **Playlist Statistics**: Displays total song count and unique artist count for the selected playlist.
- **Artist Distribution**: Shows the top 10 artists by song count for the selected playlist.
- **Decade Distribution**: View the distribution of songs by decade across all playlists or filter by a specific playlist.

**Run script:**
```bash
python src/analysis/dashboard.py
```

![Dashboard](images/plotly_dashboard.png)

The dashboard will start locally at `http://127.0.0.1:8050/`
