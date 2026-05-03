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
Database created with 50 playlists and 9544 total rows.
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
Unique Track_Keys: 5229
Removed: 528 duplicate tracks (same song, different Track_ID)
Tracks table created with unique tracks sorted by Artist, Song.
```

### Sample Queries

**Get the number of unique playlists:**
```bash
sqlite3 spotify_music_library.db \
  "SELECT COUNT(DISTINCT playlist_name) FROM playlists;"
```
Result: `50`

**Get number of unique artists from tracks table:**
```bash
sqlite3 spotify_music_library.db \
  "SELECT COUNT(DISTINCT Artist) FROM tracks;"
```
Result: `2025`

**Get distribution of artists by song count (grouped ranges):**
```bash
sqlite3 spotify_music_library.db \
  "SELECT CASE \
           WHEN song_count = 1 THEN '1' \
           WHEN song_count BETWEEN 2 AND 3 THEN '2-3' \
           ELSE '4+' \
         END as song_count_range, \
         COUNT(*) as artist_count \
   FROM (SELECT Artist, COUNT(*) as song_count \
        FROM tracks \
        GROUP BY Artist) \
   GROUP BY song_count_range \
   ORDER BY MIN(song_count);"
```
Result:
```
1411 artists have 1 song (69.7%)
334 artists have 2-3 songs (16.5%)
280 artists have 4+ songs (13.8%)
```

**Get top five artists with song count:**
```bash
sqlite3 spotify_music_library.db \
  "SELECT Artist, COUNT(*) as song_count \
   FROM tracks \
   GROUP BY Artist \
   ORDER BY song_count DESC \
   LIMIT 5;"
```
Result:
```
Backstreet Boys|107
OneRepublic|88
Maroon 5|70
Matt Maeson|64
The Fray|58
```

**Get songs from playlist 01:**
```bash
sqlite3 spotify_music_library.db \
  "SELECT Song_Number, Song, Artist, Album_Year \
   FROM playlists \
   WHERE playlist_number = '01';"
```
Result:
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

