from haystack import Pipeline
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.rankers import SentenceTransformersDiversityRanker
from haystack_integrations.document_stores.opensearch import \
    OpenSearchDocumentStore

text_embedder = SentenceTransformersTextEmbedder(
    model="sentence-transformers/all-mpnet-base-v2"
)
from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack_integrations.components.retrievers.opensearch.bm25_retriever import \
    OpenSearchBM25Retriever
from haystack_integrations.components.retrievers.opensearch.embedding_retriever import \
    OpenSearchEmbeddingRetriever


async def get_open_search_db() -> OpenSearchDocumentStore:
    document_store = OpenSearchDocumentStore(
        hosts=["http://localhost:9200"],  # Local OpenSearch instance
        use_ssl=True,  # SSL is typically not used for local development
        verify_certs=False,  # Certificate verification is typically not needed for local development
        http_auth=("admin", "admin"),
    )
    return document_store


async def get_open_search_retriver(db) -> Pipeline:
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
