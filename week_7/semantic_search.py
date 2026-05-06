from sentence_transformers import SentenceTransformer, util

# 1. Load the model
model = SentenceTransformer("all-MiniLM-L6-v2")

products = [
    "Lego Castle Set",
    "Wooden Building Blocks",
    "Superhero Action Figure",
    "Remote Control Car",
    "Easy-Bake Oven",
    "1000 Piece Jigsaw Puzzle",
]

print("Encoding product database...")
product_embeddings = model.encode(products, convert_to_tensor=True)


def semantic_search(query, top_k=3):
    print(f"\nSearching for: '{query}'")

    query_embedding = model.encode(query, convert_to_tensor=True)

    cosine_scores = util.cos_sim(query_embedding, product_embeddings)[0]

    import torch

    top_results = torch.topk(cosine_scores, k=top_k)

    # Step D: Display the results
    print("--- Top Matches ---")
    for score, index in zip(top_results[0], top_results[1]):
        product_name = products[index]
        similarity = score.item()
        print(f"[{similarity:.4f}] {product_name}")


# 5. Test the search function
semantic_search("construction toys")
semantic_search("something to drive")
semantic_search("baking game")
