import os
import subprocess
import sys

print("=== Spotify Music Library Database Setup ===\n")

scripts = [
    ("create_playlists.py", "Create playlists table from CSV files"),
    ("create_tracks.py", "Deduplicate tracks and create tracks table"),
    ("create_song_playlist_count.py", "Create song playlist count table"),
    ("create_artist_playlist_count.py", "Create artist playlist count table"),
    ("create_custom_playlists.py", "Create custom playlists table"),
    ("create_mixing_rules.py", "Create harmonic mixing rules table"),
]

for script, description in scripts:
    print(f"\n--- {description} ---")
    print(f"Running {script}...")
    script_path = os.path.join(os.path.dirname(__file__), script)
    result = subprocess.run([sys.executable, script_path], cwd=os.path.dirname(__file__))
    if result.returncode != 0:
        print(f"Error: {script} failed with exit code {result.returncode}")
        sys.exit(1)
    print(f"✓ {script} completed successfully")

print("\n=== Database Setup Complete ===")
print("All database tables have been created successfully.")
