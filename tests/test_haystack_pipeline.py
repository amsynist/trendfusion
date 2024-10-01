from haystack import Pipeline
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.rankers import SentenceTransformersDiversityRanker
from haystack_integrations.document_stores.opensearch import OpenSearchDocumentStore

text_embedder = SentenceTransformersTextEmbedder(
    model="sentence-transformers/all-mpnet-base-v2"
)
import logging

from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack_integrations.components.retrievers.opensearch.bm25_retriever import (
    OpenSearchBM25Retriever,
)
from haystack_integrations.components.retrievers.opensearch.embedding_retriever import (
    OpenSearchEmbeddingRetriever,
)

logging.basicConfig(
    format="%(levelname)s - %(name)s -  %(message)s", level=logging.WARNING
)
logging.getLogger("haystack").setLevel(logging.INFO)

OPEN_SEARCH_HOST = "https://search-krakenops-products-i2db6hx4fdyavi5aw7cgzxjn5u.ap-south-1.es.amazonaws.com"
OPEN_SEARCH_USER = "krakenops"
OPEN_SEARCH_PASSWORD = "@Krakenops007"


def get_open_search_db() -> OpenSearchDocumentStore:
    document_store = OpenSearchDocumentStore(
        hosts=[OPEN_SEARCH_HOST],  # Local OpenSearch instance
        use_ssl=True,  # SSL is typically not used for local development
        verify_certs=True,  # Certificate verification is typically not needed for local development
        http_auth=(OPEN_SEARCH_USER, OPEN_SEARCH_PASSWORD),
    )
    return document_store


def get_open_search_retriver(db) -> Pipeline:
    embedding_retriever = OpenSearchEmbeddingRetriever(document_store=db)

    bm25_retriever = OpenSearchBM25Retriever(document_store=db)

    document_joiner = DocumentJoiner()
    hybrid_retrieval = Pipeline()

    ranker = SentenceTransformersDiversityRanker(
        model="sentence-transformers/all-MiniLM-L6-v2", similarity="cosine"
    )
    ranker.warm_up()

    hybrid_retrieval.add_component("text_embedder", text_embedder)
    hybrid_retrieval.add_component("embedding_retriever", embedding_retriever)
    hybrid_retrieval.add_component("bm25_retriever", bm25_retriever)
    hybrid_retrieval.add_component("document_joiner", document_joiner)
    hybrid_retrieval.add_component("ranker", ranker)

    hybrid_retrieval.connect("text_embedder", "embedding_retriever")
    hybrid_retrieval.connect("bm25_retriever", "document_joiner")
    hybrid_retrieval.connect("embedding_retriever", "document_joiner")
    hybrid_retrieval.connect("document_joiner", "ranker")
    return hybrid_retrieval


open_search_retriever = get_open_search_retriver(get_open_search_db())


import time  # Import the time module


def run() -> None:
    start_time = time.time()  # Record the start time

    result = open_search_retriever.run(
        {
            "text_embedder": {"text": "shirts for wedding for bride"},
            "bm25_retriever": {
                "query": "shirts for wedding for bride",
                "scale_score": 0 - 1,
                "top_k": 200,
                "filters": {
                    "field": "meta.category",
                    "operator": "in",
                    "value": ["shirts", "pants"],
                },
            },
            "ranker": {
                "query": "shirts",
                "top_k": 500,
            },
        }
    )

    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time  # Calculate the elapsed time

    print(result)
    print(f"Time taken: {elapsed_time:.2f} seconds")  # Print the elapsed time


run()
