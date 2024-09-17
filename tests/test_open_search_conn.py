import os

from haystack_integrations.document_stores.opensearch import \
    OpenSearchDocumentStore

OPEN_SEARCH_USER = os.environ["OPEN_SEARCH_USER"]
OPEN_SEARCH_PASS = os.environ["OPEN_SEARCH_PASSWORD"]
OPEN_SEARCH_HOST = os.environ["OPEN_SEARCH_HOST"]
document_store = OpenSearchDocumentStore(
    hosts=[OPEN_SEARCH_HOST],  # Local OpenSearch instance
    use_ssl=True,  # SSL is typically not used for local development
    verify_certs=True,  # Certificate verification is typically not needed for local development
    http_auth=(OPEN_SEARCH_USER, OPEN_SEARCH_PASS),
)


x = document_store.client.ping()
print("OPEN SEARCH CONNECTED :", x)
