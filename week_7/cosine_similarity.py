import numpy as np
from sentence_transformers import SentenceTransformer

# a. Define the 3 products
products = ["Lego Castle", "Wooden Blocks", "Action Figure"]

# Load the model and get embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(products)


# b. Function to manually calculate cosine similarity using numpy
def manual_cosine_similarity(vec1, vec2):
    # 1. Calculate the dot product
    dot_product = np.dot(vec1, vec2)
    # 2. Calculate the magnitude (L2 norm) of each vector
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    # 3. Divide dot product by the product of the magnitudes
    return dot_product / (norm_vec1 * norm_vec2)


# Extract individual vectors for readability
lego_vec = embeddings[0]
wood_vec = embeddings[1]
action_vec = embeddings[2]

# Calculate and print similarities
print("Cosine Similarities:")
print(f"Lego vs Wooden Blocks: {manual_cosine_similarity(lego_vec, wood_vec):.4f}")
print(f"Lego vs Action Figure: {manual_cosine_similarity(lego_vec, action_vec):.4f}")
print(f"Wooden Blocks vs Action: {manual_cosine_similarity(wood_vec, action_vec):.4f}")


# Plotting in 2D using PCA
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# c. Initialize PCA to reduce to 2 components (2D)
pca = PCA(n_components=2)
embeddings_2d = pca.fit_transform(embeddings)

# Create the plot
plt.figure(figsize=(8, 6))

# Plot the 3 points
plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], color="red", s=100)

# Add the product names as labels next to the points
for i, product in enumerate(products):
    plt.annotate(
        product,
        (embeddings_2d[i, 0], embeddings_2d[i, 1]),
        xytext=(8, 5),
        textcoords="offset points",
        fontsize=12,
        fontweight="bold",
    )

plt.title("2D PCA Plot of Toy Embeddings")
plt.xlabel("Principal Component 1")
plt.ylabel("Principal Component 2")
plt.grid(True, linestyle="--", alpha=0.6)
plt.axhline(0, color="black", linewidth=0.5)
plt.axvline(0, color="black", linewidth=0.5)
plt.show()
