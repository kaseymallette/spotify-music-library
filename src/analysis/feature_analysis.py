import sqlite3
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

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
        Energy
    FROM tracks
""", conn)

conn.close()

# Define metadata and feature columns
METADATA = ['Track_Key']
FEATURES = ['BPM', 'Valence', 'Dance', 'Energy']

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

# Standardize features
print("\n=== Clustering Analysis ===")
scaler = StandardScaler()
df_features_scaled = scaler.fit_transform(df_features)
print("Features standardized using StandardScaler")

# Run k-means clustering with different cluster numbers and evaluate using elbow method
n_clusters_range = range(3, 11)
inertias = []

for n_clusters in n_clusters_range:
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(df_features_scaled)
    inertias.append(kmeans.inertia_)
    print(f"Inertia for {n_clusters} clusters: {kmeans.inertia_:.2f}")

# Plot elbow method
plt.figure(figsize=(8, 5))
plt.plot(n_clusters_range, inertias, marker='o', color='steelblue')
plt.xlabel('Number of Clusters')
plt.ylabel('Inertia')
plt.title('Elbow Method for K-Means Clustering')
plt.grid(alpha=0.3)
plt.tight_layout()

plot_path = os.path.join(images_dir, 'elbow_method.png')
plt.savefig(plot_path, dpi=150)
print(f"\nElbow method plot saved as elbow_method.png")
plt.show()

# Find the elbow point using the "knee" detection method
# Calculate the distance from each point to the line connecting the first and last points
n_points = len(n_clusters_range)
x = n_clusters_range
y = inertias

# Line from first to last point
x1, y1 = x[0], y[0]
x2, y2 = x[-1], y[-1]

# Calculate distances from each point to the line
distances = []
for i in range(n_points):
    # Distance from point (x[i], y[i]) to line through (x1, y1) and (x2, y2)
    dist = abs((y2 - y1) * x[i] - (x2 - x1) * y[i] + x2 * y1 - y2 * x1) / ((y2 - y1)**2 + (x2 - x1)**2)**0.5
    distances.append(dist)

# Find the elbow point (maximum distance)
elbow_idx = distances.index(max(distances))
best_n_clusters = n_clusters_range[elbow_idx]
print(f"\nElbow detected at {best_n_clusters} clusters")

# Fit final model with best number of clusters
kmeans_final = KMeans(n_clusters=best_n_clusters, random_state=42, n_init=10)
cluster_labels = kmeans_final.fit_predict(df_features_scaled)

# Add cluster labels to dataframe
df['cluster'] = cluster_labels

# Print cluster statistics
print("\n=== Cluster Statistics ===")
print(f"Number of clusters: {best_n_clusters}")
print(f"Cluster distribution:")
print(df['cluster'].value_counts().sort_index())
print(f"\nValence distribution by cluster:")
print(df.groupby('cluster')['Valence'].mean())

# Visualize clusters using feature pairs
print("\n=== Cluster Visualization ===")
# Select a few key feature pairs for visualization
feature_pairs = [
    ('Valence', 'Energy'),
    ('Valence', 'Dance'),
    ('Dance', 'Energy'),
    ('Valence', 'BPM')
]

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for i, (feat1, feat2) in enumerate(feature_pairs):
    ax = axes[i]
    scatter = ax.scatter(df[feat1], df[feat2], c=df['cluster'], cmap='viridis', alpha=0.6)
    ax.set_xlabel(feat1)
    ax.set_ylabel(feat2)
    ax.set_title(f'{feat1} vs {feat2}')
    ax.grid(alpha=0.3)

plt.suptitle(f'K-Means Clustering ({best_n_clusters} clusters) - Feature Pairs', fontsize=14, y=1.02)
plt.tight_layout()

# Add a colorbar for the last plot
cbar = plt.colorbar(scatter, ax=axes.ravel().tolist(), label='Cluster')

plot_path = os.path.join(images_dir, 'cluster_visualization.png')
plt.savefig(plot_path, dpi=150)
print(f"\nCluster visualization plot saved as cluster_visualization.png")
plt.show()
