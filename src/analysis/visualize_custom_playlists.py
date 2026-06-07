import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os
import struct
import re


root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, "spotify_music_library.db")
images_dir = os.path.join(root_dir, "images")
os.makedirs(images_dir, exist_ok=True)

conn = sqlite3.connect(db_path)

query = """
SELECT
    cp.playlist_name,
    cps.song,
    cps.artist,
    cps.bpm,
    cps.valence,
    cps.energy,
    cps.dance,
    cps.distance,
    cps.mood_score,
    cps.key
FROM custom_playlist_songs cps
JOIN custom_playlists cp ON cp.id = cps.playlist_id
"""

df = pd.read_sql(query, conn)
conn.close()


def _coerce_numeric(value, col_name):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        if len(value) == 8:
            int_candidate = struct.unpack("<q", value)[0]
            float_candidate = struct.unpack("<d", value)[0]
            if col_name == "distance":
                if float_candidate == float_candidate and 0 <= float_candidate <= 10:
                    return float_candidate
                if 0 <= int_candidate <= 10:
                    return float(int_candidate)
                return None
            if 0 <= int_candidate <= 500:
                return float(int_candidate)
            if float_candidate == float_candidate and 0 <= float_candidate <= 500:
                return float_candidate
            return None
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _key_sort_value(key_label):
    if not isinstance(key_label, str):
        return (999, 999, "Z")
    match = re.match(r"^(\d{1,2})([AB])$", key_label.strip().upper())
    if match:
        number = int(match.group(1))
        letter_rank = 0 if match.group(2) == "A" else 1
        return (letter_rank, number, match.group(2))
    return (999, 999, key_label)


numeric_cols = ["bpm", "valence", "energy", "dance", "distance", "mood_score"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col].map(lambda value: _coerce_numeric(value, col)), errors="coerce")

if df.empty:
    print("No songs found in custom playlists. Build and save a playlist first.")
    raise SystemExit(0)

print("=== Custom Playlist Summary ===")
print(f"Total playlists: {df['playlist_name'].nunique()}")
print(f"Total songs: {len(df)}")
print("\nSongs per playlist:")
print(df.groupby("playlist_name").size().sort_values(ascending=False).to_string())

summary = (
    df.groupby("playlist_name")[["bpm", "valence", "energy", "dance", "mood_score", "distance"]]
    .mean()
    .round(2)
)
print("\nAverage features by playlist:")
print(summary.to_string())

fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

ax1.hist(df["bpm"].dropna(), bins=20, color="steelblue", edgecolor="black", alpha=0.8)
ax1.set_title("BPM Distribution (Custom Playlists)")
ax1.set_xlabel("BPM")
ax1.set_ylabel("Song Count")
ax1.grid(axis="y", alpha=0.3)

ax2.hist(df["mood_score"].dropna(), bins=20, color="mediumseagreen", edgecolor="black", alpha=0.8)
ax2.set_title("Mood Score Distribution (Custom Playlists)")
ax2.set_xlabel("Mood Score")
ax2.set_ylabel("Song Count")
ax2.grid(axis="y", alpha=0.3)

key_counts = df["key"].fillna("Unknown").astype(str).value_counts()
key_counts = key_counts.reindex(sorted(key_counts.index, key=_key_sort_value))
ax3.bar(key_counts.index, key_counts.values, color="orchid", edgecolor="black", alpha=0.8)
ax3.set_title("Key Distribution (Custom Playlists)")
ax3.set_xlabel("Key")
ax3.set_ylabel("Song Count")
ax3.grid(axis="y", alpha=0.3)
ax3.tick_params(axis="x", rotation=45)

ax4.hist(df["distance"].dropna(), bins=20, color="coral", edgecolor="black", alpha=0.8)
ax4.set_title("Distance Distribution (Custom Playlists)")
ax4.set_xlabel("Distance")
ax4.set_ylabel("Song Count")
ax4.grid(axis="y", alpha=0.3)

plt.tight_layout()
chart_path = os.path.join(images_dir, "custom_playlist_distributions.png")
plt.savefig(chart_path, dpi=150)
print(f"\nChart saved: {chart_path}")
plt.show()
