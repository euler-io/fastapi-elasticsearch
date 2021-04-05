# Query Utility for Elasticsearch

[![Pypi](https://img.shields.io/pypi/v/fastapi-elasticsearch.svg)](https://pypi.org/project/fastapi-elasticsearch/)

Utility library for creating elasticsearch query proxies using [FastAPI](https://fastapi.tiangolo.com/).

```python

from fastapi_elasticsearch import ElasticsearchAPIQueryBuilder

query_builder = ElasticsearchAPIQueryBuilder()

# Decorate a function as a filter.
# The filter can declare parameters.
@query_builder.filter()
def filter_category(c: Optional[str] = Query(None)):
    return {
        "term": {
            "category": c
        }
    } if c is not None else None

# Decorate a function as a matcher
# (will contribute to the query scoring).
# Parameters can also be used.
@query_builder.matcher()
def match_fields(q: Optional[str] = Query(None)):
    return {
        "multi_match": {
            "query": q,
            "fuzziness": "AUTO",
            "fields": [
                "name^2",
                "description"
            ]
        }
    } if q is not None else None

# Decorate a function as a sorter.
# Parameters can be declared.
@query_builder.sorter()
def sort_by(direction: Optional[str] = Query(None)):
    return {
        "name": direction
    } if direction is not None else None

# Decorate a function as a highlighter.
# Parameters can also be declared.
@query_builder.highlighter()
def highlight(q: Optional[str] = Query(None),
              h: bool = Query(False):
    return {
        "name": {}
    } if q is not None and h else None

app = FastAPI()

# Create a route using the query builder as dependency.
@app.get("/search")
async def search(query_body: Dict = Depends(query_builder.build())) -> JSONResponse:
    # Search using the Elasticsearch client.
    return es.search(
        body=query_body,
        index=index_name
    )
```

It is possible to customize the generated query body using the decorator @search_builder.

```python
from typing import List, Dict

@query_builder.search_builder()
def build_search_body(size: int = 10,
                      start_from: int = 0,
                      source: Union[List, Dict, str] = None,
                      minimum_should_match: int = 1,
                      filters: List[Dict] = [],
                      matchers: List[Dict] = [],
                      highlighters: List[Dict] = [],
                      sorters: List[Dict] = []) -> Dict:
    return {
        "query": {
            ...
        },
        ...
    }

```
