import sqlite3
import pandas as pd
import os

# Get the root directory (two levels up from src/db/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')
csv_path = os.path.join(root_dir, 'data', 'harmonic_mixing_rules.csv')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create mixing_rules table in long format (transitions)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS mixing_rules (
        starting_key TEXT,
        target_key TEXT,
        mix_type TEXT,
        PRIMARY KEY (starting_key, target_key, mix_type)
    )
''')

# Read the CSV file
df = pd.read_csv(csv_path)

# Rename columns for SQL compatibility
df = df.rename(columns={
    'Starting Key': 'starting_key',
    'Perfect Mix': 'perfect_mix',
    '-1 Mix': 'minus_1_mix',
    '+1 Mix': 'plus_1_mix',
    'Energy Boost': 'energy_boost',
    'Scale Change': 'scale_change',
    'Diagonal Mix': 'diagonal_mix',
    "Jaw's Mix": 'jaws_mix',
    'Mood Shifter': 'mood_shifter'
})

# Convert from wide format to long format
mix_types = ['perfect_mix', 'minus_1_mix', 'plus_1_mix', 'energy_boost', 'scale_change', 'diagonal_mix', 'jaws_mix', 'mood_shifter']
transitions_data = []

for _, row in df.iterrows():
    starting_key = row['starting_key']
    for mix_type in mix_types:
        target_key = row[mix_type]
        if pd.notna(target_key):  # Skip if target_key is NaN
            transitions_data.append({
                'starting_key': starting_key,
                'target_key': target_key,
                'mix_type': mix_type
            })

# Create DataFrame from transitions data
df_transitions = pd.DataFrame(transitions_data)

# Clear existing data (if any)
cursor.execute('DELETE FROM mixing_rules')

# Insert the data
df_transitions.to_sql('mixing_rules', conn, if_exists='append', index=False)

# Display statistics
df_stats = pd.read_sql('SELECT COUNT(*) as total_transitions FROM mixing_rules', conn)
print("Mixing rules table created successfully.")
print(f"Total transitions loaded: {df_stats['total_transitions'][0]}")

# Close the database connection
conn.close()
