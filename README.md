# 🩳 TrendFusion

TrendFusion is a core repo that provides APIs for fashion recommendations, AI-driven product insights, and search functionalities using large language models (LLMs), Haystack, and trend knowledge.

## Project Structure

```xml
├── __init__.py
├── api
│   ├── __init__.py
│   └── ai_search.py
├── external
│   ├── __init__.py
│   ├── constants.py
│   ├── database
│   │   ├── __init__.py
│   │   ├── load.py
│   │   ├── mongo_db.py
│   │   └── open_search_db.py
│   └── llm
│       ├── __init__.py
│       ├── base_llm.py
│       └── groq_llm.py
├── main.py
└── models
    ├── __init__.py
    └── base.py
```

## Local Development Guide

### 2. Setup Environment Variables

Create a `.env` file in the root directory with the following content:

```
FA_USER_COLLECTION=users
FA_DB_NAME=ai-trends
FA_MONGO_URI=mongodb+srv://fa:<password>@ai-trends.mongodb.net/?retryWrites=true&w=majority&appName=ai-trends
GROQ_API_KEY=<your_groq_api_key>
```

### 3. Building and Running Docker Containers

#### Dockerfile

The `Dockerfile` sets up the FastAPI application

#### Docker Compose

The `docker-compose.yml` file to build and run the FastAPI application along with OpenSearch:

```yaml
version: "3.8"

services:
  fastapi-app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "80:80"
    environment:
      - FA_USER_COLLECTION=users
      - FA_DB_NAME=ai-trends
      - FA_MONGO_URI=mongodb+srv://fa:<password>@ai-trends.mongodb.net/?retryWrites=true&w=majority&appName=ai-trends
      - GROQ_API_KEY=<your_groq_api_key>
    restart: unless-stopped

  opensearch:
    image: opensearchproject/opensearch:latest
    container_name: opensearch
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"
      - "9600:9600"

  opensearch-dashboards:
    image: opensearchproject/opensearch-dashboards:latest
    container_name: opensearch-dashboards
    environment:
      - OPENSEARCH_HOSTS=http://opensearch:9200
    ports:
      - "5601:5601"
```

### 5. Run the Application

Use Docker Compose to build and run the application and OpenSearch services:

```sh
docker compose up --build
```

### 6. Development Tips

- **Rebuild Docker Containers**: If you make changes to the Dockerfile or dependencies, you can rebuild the Docker containers using:

  ```sh
  docker compose up --build
  ```

- **OpenSearch Dashboard**: Access the OpenSearch dashboard at [http://localhost:5601](http://localhost:5601).

- **FastAPI Documentation**: FastAPI automatically generates interactive API documentation, which you can access at [http://localhost:80/docs](http://localhost:80/docs).
