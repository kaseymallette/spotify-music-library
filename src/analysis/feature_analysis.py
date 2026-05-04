import sqlite3
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Get the root directory (two levels up from src/analysis/)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
db_path = os.path.join(root_dir, 'spotify_music_library.db')

# Connect to the database
conn = sqlite3.connect(db_path)

# Query tracks table for features
df = pd.read_sql("""
    SELECT 
        Track_Key,
        BPM,
        Valence,
        Dance,
        Energy,
        Acoustic,
        `Loud (Db)` as Loud_Db,
        Album_Year,
        Popularity
    FROM tracks
""", conn)

conn.close()

# Define metadata and feature columns
METADATA = ['Track_Key']
FEATURES = ['BPM', 'Valence', 'Dance', 'Energy', 'Acoustic', 'Loud_Db', 'Album_Year', 'Popularity']

# Separate metadata and features
df_metadata = df[METADATA]
df_features = df[FEATURES]

# Convert features to numeric in the original dataframe
for col in FEATURES:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Update df_features after conversion
df_features = df[FEATURES]

print("=== Feature Analysis ===\n")
print(f"Total records: {len(df)}")
print(f"Metadata columns: {len(METADATA)}")
print(f"Feature columns: {len(FEATURES)}\n")

print("=== Feature Statistics ===")
print(df_features.describe())

def plot_feature_distributions(df_features, figsize=(14, 10)):
    """
    Plot histogram + KDE for each feature in the dataframe.
    
    Args:
        df_features: DataFrame with numeric features to plot
        figsize: Tuple for figure size (width, height)
    """
    features = df_features.columns.tolist()
    n_features = len(features)
    
    # Calculate grid dimensions
    n_cols = 3
    n_rows = (n_features + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
    axes = axes.flatten()
    
    for i, feature in enumerate(features):
        ax = axes[i]
        
        # Histogram with KDE overlay
        sns.histplot(df_features[feature], kde=True, ax=ax, color='steelblue', 
                     edgecolor='white', alpha=0.7)
        
        # Add summary stats as text
        mean = df_features[feature].mean()
        median = df_features[feature].median()
        std = df_features[feature].std()
        
        stats_text = f'μ={mean:.1f}  med={median:.1f}  σ={std:.1f}'
        ax.set_title(f'{feature}\n{stats_text}', fontsize=10)
        ax.set_xlabel('')
        ax.set_ylabel('')
    
    # Turn off unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')
    
    plt.suptitle('Feature Distributions', fontsize=14, y=1.02)
    plt.tight_layout()
    
    # Save the plot
    images_dir = os.path.join(root_dir, 'images')
    os.makedirs(images_dir, exist_ok=True)
    plot_path = os.path.join(images_dir, 'feature_distributions.png')
    plt.savefig(plot_path, dpi=150)
    print(f"\nFeature distribution plot saved as feature_distributions.png")
    
    plt.show()

# Plot feature distributions
plot_feature_distributions(df_features)

# Calculate and plot correlation matrix for features
df_features_corr = df_features.corr()
plt.figure(figsize=(8, 6))
sns.heatmap(df_features_corr, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
plt.title('Correlation Matrix of Audio Features')
plt.tight_layout()

# Save the correlation matrix plot
images_dir = os.path.join(root_dir, 'images')
os.makedirs(images_dir, exist_ok=True)
plot_path = os.path.join(images_dir, 'correlation_matrix.png')
plt.savefig(plot_path, dpi=150)
print(f"\nCorrelation matrix plot saved as correlation_matrix.png")

plt.show()
