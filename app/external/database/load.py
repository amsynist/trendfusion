import json
from dataclasses import dataclass
from typing import List

from haystack import Document, Pipeline
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack_integrations.document_stores.opensearch import \
    OpenSearchDocumentStore


def sync_get_open_search_db() -> OpenSearchDocumentStore:
    document_store = OpenSearchDocumentStore(
        hosts=["http://localhost:9200"],  # Local OpenSearch instance
        use_ssl=True,  # SSL is typically not used for local development
        verify_certs=False,  # Certificate verification is typically not needed for local development
        http_auth=(
            "admin",
            "admin",
        ),  # Authentication is typically not needed for local development
    )
    return document_store


with open("/Users/zero/Downloads/merged_data.json", "r") as data_file:
    data = json.load(data_file)


@dataclass
class Product:
    itemid: str
    brand: str
    name: str
    description: str
    category: str
    tags: List[str]
    colors: List[str]
    sizes: List[str]
    images: List[str]


def parse_tags(tags: str) -> List[str]:
    # Split the input string by newline character
    tags_list = tags.split("\n")

    colors = []
    other_tags = []

    for tag in tags_list:
        if tag.startswith("Color:"):
            # Extract colors from the Color tag
            colors.extend(tag.split("#")[1:])
        elif tag.startswith("Other:"):
            # Extract other tags from the Other tag
            other_tags.extend(tag.split("#")[1:])

    return colors, other_tags


_clean_value = lambda x: str(x or "").strip()

import pandas as pd

x_products = []
count = 0
for item_id, data in data.items():
    name = _clean_value(data.get("description"))
    description = _clean_value(data.get("desc2"))
    sizes = data.get("sizes") or []
    category = _clean_value(data.get("product_type"))
    colors, tags = parse_tags(data["tags"])
    brand = _clean_value(data.get("brand"))
    images = [data.get("img1") + data.get("img2")]
    x_product = Product(
        item_id, brand, name, description, category, tags, colors, sizes, images
    )

    x_products.append(x_product.__dict__)
    if len(x_products) > 500:
        break
products = pd.DataFrame(x_products)
print(products)
docs = []

for _, row in products.iterrows():
    metadata = {
        "tags": ",".join(row["tags"]),
        "colors": ",".join(row["colors"]),
        "category": row["category"],
        "brand": row["brand"],
    }

    docs.append(Document(id=row["itemid"], content=row["description"], meta=metadata))

print(docs)

document_embedder = SentenceTransformersDocumentEmbedder(
    model="sentence-transformers/all-mpnet-base-v2"
)

# document_embedder= OpenAIDocumentEmbedder()
document_writer = DocumentWriter(sync_get_open_search_db())

indexing_pipeline = Pipeline()
document_splitter = DocumentSplitter(
    split_by="word", split_length=256, split_overlap=32
)
indexing_pipeline.add_component("document_splitter", document_splitter)

indexing_pipeline.add_component("document_embedder", document_embedder)
indexing_pipeline.add_component("document_writer", document_writer)

indexing_pipeline.connect("document_splitter", "document_embedder")
indexing_pipeline.connect("document_embedder", "document_writer")

indexing_pipeline.run({"document_splitter": {"documents": docs}})
