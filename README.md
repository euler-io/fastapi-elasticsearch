Query Utility for Elasticsearch
==============================

Utility library for creating elasticsearch query proxies using [FastAPI](https://fastapi.tiangolo.com/).

```python

from fastapi_elasticsearch import ElasticsearchAPI

es_api = ElasticsearchAPI(
    # The elasticsearech client
    es_client=es,
    # The index or indices that your query will run.
    index_name=index_name)

# Decorate a function as a filter.
# The filter can declare parameters.
@es_api.filter()
def filter_category(c: Optional[str] = Query(None)):
    return {
        "term": {
            "category": c
        }
    } if c is not None else None

# Decorate a function as a matcher
# (will contribute to the query scoring).
# Parameters can also be used.
@es_api.matcher()
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
@es_api.sorter()
def sort_by(direction: Optional[str] = Query(None)):
    return {
        "name": direction
    } if direction is not None else None

# Decorate a function as a highlighter.
# Parameters can also be declared.
@es_api.highlighter()
def highlight(q: Optional[str] = Query(None),
              h: bool = Query(False):
    return {
        "name": {}
    } if q is not None and h else None

# Decorate a function as a search_route. 
# It creates a new route using the declared filters (and matchers, etc.)
# as the endpoint parameters but combined with the route's parameters.
@es_api.search_route(app, "/search")
async def search(req: Request,
                 size: Optional[int] = Query(10,
                                             le=100,
                                             alias="s"),
                 start_from: Optional[int] = Query(0,
                                                   alias="f"),
                 scroll: Optional[str] = Query(None),
                ) -> JSONResponse:
    return es_api.search(
        request=req,
        size=size,
        start_from=start_from,
        scroll=scroll,
    )

```

It is possible to customize the generated query body using the decorator @search_builder.

```python
from typing import List, Dict

@es_api.search_builder()
def build_search_body(size: int = 10,
                                start_from: int = 0,
                                scroll: str = None,
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
