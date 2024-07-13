# Local Development Guide

## Setup opensearch locally

#### Pull Openstack images

```sh
docker pull opensearchproject/opensearch:latest
docker pull opensearchproject/opensearch-dashboards:latest
```

#### Run OpenSearch Server

```sh
docker run -d --name opensearch -p 9200:9200 -p 9600:9600 -e "discovery.type=single-node" opensearchproject/opensearch:latest
```

#### Run OpenSearch Dashboards

```sh
docker run -d --name opensearch-dashboards -p 5601:5601 -e "OPENSEARCH_HOSTS=http://localhost:9200" opensearchproject/opensearch-dashboards:latest
```
