# Query Helper for Elasticsearch

[![Pypi](https://img.shields.io/pypi/v/fastapi-elasticsearch.svg)](https://pypi.org/project/fastapi-elasticsearch/)

This is a helper library for creating elasticsearch query proxies using [FastAPI](https://fastapi.tiangolo.com/).

```python

from fastapi_elasticsearch import ElasticsearchAPIQueryBuilder

# Create a new query_builder for the endpoint.
query_builder = ElasticsearchAPIQueryBuilder()

# Decorate a function as a filter.
# The filter can declare parameters.
@query_builder.filter()
def filter_category(c: Optional[List[str]] = Query([],
                                             description="Category name to filter results.")):
    return {
        "terms": {
            "category": c
        }
    } if len(c) > 0 else None

# Then use the query_builder in your endpoint.
@app.get("/search")
async def search(
        es: Elasticsearch = Depends(get_elasticsearch),
        query_body: Dict = Depends(query_builder.build())) -> JSONResponse:
    return es.search(
        body=query_body,
        index=index_name
    )
```
The swagger API will result in:

![Category Filter](https://github.com/euler-io/fastapi-elasticsearch/blob/main/docs/category_filter.png?raw=true)

The resulting query will be like this:
```json

{
  "query": {
    "bool": {
      "filter": [
        {
          "terms": {
            "category": [
              "the-category"
            ]
          }
        }
      ]
    }
  },
  "size": 10,
  "from": 0
}
```
```python

# Or decorate a function as a matcher
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
```
The swagger API will result in:

![Category Filter](https://github.com/euler-io/fastapi-elasticsearch/blob/main/docs/matchers.png?raw=true)

The resulting query will be like this:

```json
{
  "query": {
    "bool": {
      "should": [
        {
          "multi_match": {
            "query": "bob",
            "fuzziness": "AUTO",
            "fields": [
              "name^2"
            ]
          }
        }
      ],
      "minimum_should_match": 1
    }
  },
  "size": 10,
  "from": 0
}
```

To control the ordering, it is possible to annotate a function as sorter.

```python
class Direction(str, Enum):
    asc = "asc"
    desc = "desc"

# Decorate a function as a sorter.
# Parameters can be declared.
@query_builder.sorter()
def sort_by(direction: Optional[Direction] = Query(None)):
    return {
        "name": direction
    } if direction is not None else None

```
The swagger API will result in:

![Category Filter](https://github.com/euler-io/fastapi-elasticsearch/blob/main/docs/sorter.png?raw=true)

The resulting query will be like this:

```json
{
  "query": {
    "match_all": {}
  },
  "size": 10,
  "from": 0,
  "sort": [
    {
      "name": "asc"
    }
  ]
}
```
To add highlight functionality, it is possible to annotate a function as highlighter.

```python
# Decorate a function as a highlighter.
# Parameters can also be declared.
@query_builder.highlighter()
def highlight(q: Optional[str] = Query(None,
                                       description="Query to match the document text."),
              h: bool = Query(False,
                              description="Highlight matched text and inner hits.")):
    return {
        "name": {
            "fragment_size": 256,
            "number_of_fragments": 1
        }
    } if q is not None and h else None
```
The swagger API will result in:

![Category Filter](https://github.com/euler-io/fastapi-elasticsearch/blob/main/docs/highlighter.png?raw=true)

The resulting query will be like this:

```json
{
  "query": {
    "bool": {
      "should": [
        {
          "multi_match": {
            "query": "bob",
            "fuzziness": "AUTO",
            "fields": [
              "name^2"
            ]
          }
        }
      ],
      "minimum_should_match": 1
    }
  },
  "size": 10,
  "from": 0,
  "highlight": {
    "fields": {
      "name": {
        "fragment_size": 256,
        "number_of_fragments": 1
      }
    }
  }
}
```

Now, a complete example:

```python

app = FastAPI()

query_builder = ElasticsearchAPIQueryBuilder()


@query_builder.filter()
def filter_items():
    return {
        "term": {
            "join_field": "item"
        }
    }


@query_builder.filter()
def filter_category(c: Optional[List[str]] = Query([],
                                                   description="Category name to filter results.")):
    return {
        "terms": {
            "category": c
        }
    } if len(c) > 0 else None


@query_builder.matcher()
def match_fields(q: Optional[str] = Query(None,
                                          description="Query to match the document text.")):
    return {
        "multi_match": {
            "query": q,
            "fuzziness": "AUTO",
            "fields": [
                "name^2",
            ]
        }
    } if q is not None else None


@query_builder.matcher()
def match_fragments(q: Optional[str] = Query(None,
                                             description="Query to match the document text."),
                    h: bool = Query(False,
                                    description="Highlight matched text and inner hits.")):
    if q is not None:
        matcher = {
            "has_child": {
                "type": "fragment",
                "score_mode": "max",
                "query": {
                    "bool": {
                        "minimum_should_match": 1,
                        "should": [
                            {
                                "match": {
                                    "content": {
                                        "query": q,
                                        "fuzziness": "auto"
                                    }
                                }
                            },
                            {
                                "match_phrase": {
                                    "content": {
                                        "query": q,
                                        "slop": 3,
                                        "boost": 50
                                    }
                                }
                            },
                        ]
                    }
                }
            }
        }
        if h:
            matcher["has_child"]["inner_hits"] = {
                "size": 1,
                "_source": "false",
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 256,
                            "number_of_fragments": 1
                        }
                    }
                }
            }
        return matcher
    else:
        return None


class Direction(str, Enum):
    asc = "asc"
    desc = "desc"


@query_builder.sorter()
def sort_by(direction: Optional[Direction] = Query(None)):
    return {
        "name": direction
    } if direction is not None else None


@query_builder.highlighter()
def highlight(q: Optional[str] = Query(None,
                                       description="Query to match the document text."),
              h: bool = Query(False,
                              description="Highlight matched text and inner hits.")):
    return {
        "name": {
            "fragment_size": 256,
            "number_of_fragments": 1
        }
    } if q is not None and h else None


@app.get("/search")
async def search(query_body: Dict = Depends(query_builder.build())) -> JSONResponse:
    return es.search(
        body=query_body,
        index=index_name
    )


```

Also it is possible to customize the generated query body using the decorator search_builder.

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
