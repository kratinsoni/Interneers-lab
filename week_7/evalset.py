from sentence_transformers import SentenceTransformer, util
import torch

product_database = {
    "lego_castle_001": "Lego Castle Set",
    "lego_city_002": "Lego City Police Station",
    "wooden_blocks_003": "Wooden Building Blocks",
    "soft_blocks_004": "Soft Silicone Baby Blocks",
    "plush_toy_005": "Stuffed Elephant Plush Toy",
    "baby_rattle_006": "Colorful Baby Rattle",
    "teddy_bear_010": "Giant Teddy Bear",
    "action_figure_015": "Superhero Action Figure",
    "puzzle_1000pc_020": "1000 Piece Landscape Jigsaw Puzzle",
    "teen_board_game_025": "Complex Strategy Board Game for Teens",
}

product_ids = list(product_database.keys())
product_texts = list(product_database.values())

SEARCH_TEST_CASES = [
    {
        "query": "construction toys",
        "relevant_products": ["lego_castle_001", "lego_city_002", "wooden_blocks_003"],
        "irrelevant_products": ["teddy_bear_010", "action_figure_015"],
    },
    {
        "query": "gifts for toddlers",
        "relevant_products": ["soft_blocks_004", "plush_toy_005", "baby_rattle_006"],
        "irrelevant_products": ["puzzle_1000pc_020", "teen_board_game_025"],
    },
    {
        "query": "hard puzzle for older kids",
        "relevant_products": ["puzzle_1000pc_020", "teen_board_game_025"],
        "irrelevant_products": ["soft_blocks_004", "baby_rattle_006"],
    },
]

print("Loading model and encoding database...")
model = SentenceTransformer("all-MiniLM-L6-v2")
database_embeddings = model.encode(product_texts, convert_to_tensor=True)
print("Encoding complete.\n")


def evaluate_search_performance(test_cases, top_k=3):
    total_cases = len(test_cases)
    total_recall = 0.0
    failed_cases = 0

    print(f"--- Running Evaluation (Top-{top_k} Results) ---")

    for i, test in enumerate(test_cases):
        query = test["query"]
        relevant = set(test["relevant_products"])
        irrelevant = set(test["irrelevant_products"])

        # Encode query and search
        query_embedding = model.encode(query, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, database_embeddings)[0]

        # Get Top K results
        top_results = torch.topk(cosine_scores, k=top_k)
        retrieved_ids = [product_ids[idx] for idx in top_results[1]]

        # Calculate Metrics
        retrieved_set = set(retrieved_ids)

        # Recall: How many of the expected relevant items did we find?
        # Note: We cap the denominator at top_k just in case there are more relevant items than K
        found_relevant = retrieved_set.intersection(relevant)
        possible_to_find = min(len(relevant), top_k)
        recall = len(found_relevant) / possible_to_find
        total_recall += recall

        # Irrelevance Penalty: Did we fetch something explicitly bad?
        found_irrelevant = retrieved_set.intersection(irrelevant)

        # Print Results for this specific query
        print(f"\nTest {i+1}: '{query}'")
        print(f"  Retrieved: {retrieved_ids}")
        print(
            f"  Recall: {recall * 100:.0f}% ({len(found_relevant)}/{possible_to_find} found)"
        )

        if found_irrelevant:
            print(
                f"  ⚠️ WARNING: Retrieved explicit irrelevant item(s): {found_irrelevant}"
            )
            failed_cases += 1

    avg_recall = (total_recall / total_cases) * 100

    print("\n" + "=" * 40)
    print("🏆 FINAL EVALUATION REPORT")
    print("=" * 40)
    print(f"Total Queries Tested: {total_cases}")
    print(f"Average Recall@{top_k}: {avg_recall:.1f}%")
    print(f"Queries with Irrelevant Results: {failed_cases} out of {total_cases}")

    if avg_recall > 80 and failed_cases == 0:
        print("\nStatus: PASS ✅ (Your model is performing excellently!)")
    else:
        print(
            "\nStatus: NEEDS IMPROVEMENT ❌ (Consider fine-tuning your embeddings or adjusting text data.)"
        )


# Run the evaluation
evaluate_search_performance(SEARCH_TEST_CASES, top_k=3)
