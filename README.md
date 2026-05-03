# spotify-music-library
A Spotify-powered music recommendation system using clustering analysis and automated playlist generation to help discover new music and avoid repetition.

## Database Setup

The `create_database.py` file was created to ingest CSV files from 50 Spotify playlists into a SQLite database. The script:

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

### Create Database

Run the `create_database.py` script to ingest CSV files and create the playlists table:

```bash
python create_database.py
```

**Output:**
```
Database created: spotify_music_library.db
Playlists table created successfully.
Number of playlists: 50
Row count: 9543
```

If you've added new CSV files to the `data/` folder, remove the existing database first:

```bash
rm spotify_music_library.db
```

### Track Deduplication

The `deduplicate_tracks.py` script removes duplicate tracks (same song with different Track_IDs, e.g., single vs album versions) and creates a `tracks` table with unique tracks sorted by Artist and Song.

**Run deduplication:**
```bash
python deduplicate_tracks.py
```

**Output:**
```
Unique Track_IDs: 5757
Unique Track_Keys: 5231
Unique Artists: 2027
Removed: 526 duplicate tracks (same song, different Track_ID)
Tracks table created with unique tracks sorted by Artist, Song.
```

### Sample Queries

You can run all sample queries at once using the `sample_queries.py` script:

```bash
python sample_queries.py
```

**Get number of unique playlists:**
50

**Get number of unique artists:**
2027

**Get number of rows in playlists table:**
9543

**Get song count distribution per playlist (grouped ranges):**
```
9 playlists have 0-50 songs (18.0%)
13 playlists have 51-100 songs (26.0%)
16 playlists have 101-200 songs (32.0%)
8 playlists have 201-500 songs (16.0%)
4 playlists have 500+ songs (8.0%)
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

**Get distribution of artists by song count (grouped ranges):**
```
1413 artists have 1 song(s) (69.7%)
334 artists have 2-3 song(s) (16.5%)
280 artists have 4+ song(s) (13.8%)
```

**Get top five artists with song count:**
```
Backstreet Boys|107
OneRepublic|88
Maroon 5|70
Matt Maeson|64
The Fray|58
```
