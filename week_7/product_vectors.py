from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

product_descriptions = [
    "Wireless Noise-Cancelling Headphones with 30-hour battery life and fast charging.",
    "Ergonomic mesh office chair with adjustable armrests and lumbar support.",
    "Smart LED light bulb, multicolor, compatible with Alexa and Google Assistant.",
    "Stainless steel insulated water bottle, 32 oz, keeps drinks cold for 24 hours."
]

embeddings = model.encode(product_descriptions)

print(f"Number of descriptions embedded: {len(embeddings)}")
print(f"Vector dimensions (size of each embedding): {embeddings[0].shape[0]}\n")
print("-" * 50)

for description, embedding in zip(product_descriptions, embeddings):
    print(f"Product: {description}")
    print(f"Vector (first 5 values): {embedding[:5]}") 
    print("-" * 50)