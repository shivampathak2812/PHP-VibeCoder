from rag.retriever import PHPRetriever


def main():

    print("=" * 60)
    print("PHP VibeCoder - Retriever Test")
    print("=" * 60)

    retriever = PHPRetriever(top_k=3)

    queries = [
        "How do PHP interfaces work?",
        "How does exception handling work in PHP?",
        "How can PHP connect to MySQL?",
    ]

    for query in queries:

        print("\n" + "=" * 60)
        print(f"QUERY: {query}")
        print("=" * 60)

        results = retriever.retrieve(query)

        for i, result in enumerate(results, start=1):

            print(f"\nResult #{i}")
            print(f"Score : {result['score']:.4f}")
            print(f"Source: {result['source']}")
            print(f"Chunk : {result['chunk_index']}")
            print(f"Text  : {result['text'][:500]}...")


if __name__ == "__main__":
    main()