# spotify-music-library
A Spotify-powered music recommendation system using clustering analysis and automated playlist generation to help discover new music and avoid repetition.

## Database Setup

The `database.py` file was created to ingest CSV files from 50 Spotify playlists into a SQLite database. The script:

- Reads all CSV files from the `data/` folder
- Extracts playlist number and name from filenames (format: `number_name.csv`)
- Adds metadata columns: `playlist_number`, `playlist_name`, and `Album_Year`
- Renames the `#` column to `Song_Number` for SQL compatibility
- Appends all data to a `playlists` table in `spotify_music_library.db`

### Setup Commands

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database creation script
python database.py
```

### Sample Queries

**Get the number of unique playlists:**
```bash
sqlite3 spotify_music_library.db \
  "SELECT COUNT(DISTINCT playlist_name) FROM playlists;"
```
Result: `50`

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
