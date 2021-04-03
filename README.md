# Query Utility for Elasticsearch

[![Pypi](https://img.shields.io/pypi/v/fastapi-elasticsearch.svg)](https://pypi.org/project/fastapi-elasticsearch/)

Utility library for creating elasticsearch query proxies using [FastAPI](https://fastapi.tiangolo.com/).

```python

from fastapi_elasticsearch import ElasticsearchAPIRouteBuilder

route_builder = ElasticsearchAPIRouteBuilder(
    # The elasticsearch client
    es_client=elasticsearch_client,
    # The index or indices that your query will run.
    index_name=index_name
)

# Decorate a function as a filter.
# The filter can declare parameters.
@route_builder.filter()
def filter_category(c: Optional[str] = Query(None)):
    return {
        "term": {
            "category": c
        }
    } if c is not None else None

# Decorate a function as a matcher
# (will contribute to the query scoring).
# Parameters can also be used.
@route_builder.matcher()
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
@route_builder.sorter()
def sort_by(direction: Optional[str] = Query(None)):
    return {
        "name": direction
    } if direction is not None else None

# Decorate a function as a highlighter.
# Parameters can also be declared.
@route_builder.highlighter()
def highlight(q: Optional[str] = Query(None),
              h: bool = Query(False):
    return {
        "name": {}
    } if q is not None and h else None

app = FastAPI()

# Add the route to the app using the default endpoint.
es_route = route_builder.build("/search")
app.routes.append(es_route)

# It is possible to customize the route endpoint.
@route_builder.endpoint("/search")
async def search(query_body = Depends(route_builder.query_builder)) -> JSONResponse:
    response = es_client.search(
        body=query_body,
        index=index_name
    )
    modified_response = modify_response(response)
    return modified_response

# And use different parameters
@route_builder.endpoint("/search-more")
async def get_document(
            req: Request,
            size: Optional[int] = Query(100,
                                        le=1000,
                                        alias="s",
                                        description="Defines the number of hits to return."),
            start_from: Optional[int] = Query(0,
                                              alias="f",
                                              description="Starting document offset.")) -> JSONResponse:
    query_body = route_builder.query_builder.build_body(
        request=req,
        size=size,
        start_from=start_from,
    )
    return es_client.search(
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
