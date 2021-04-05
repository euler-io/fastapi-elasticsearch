from typing import Dict, Optional

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from starlette.responses import JSONResponse

from development.loaddata import create_sample_index, load_sample_data
from fastapi_elasticsearch import (ElasticsearchAPIQueryBuilder,
                                   ElasticsearchAPIRouteBuilder)
from fastapi_elasticsearch.utils import wait_elasticsearch

es = Elasticsearch(
    ["elastic-dev"],
    use_ssl=True,
    ca_certs="/euler/root-ca.pem",
    ssl_show_warn=False,
    http_auth=("admin", "admin")
)

wait_elasticsearch(es)

index_name = "sample-data"
if not es.indices.exists(index_name):
    create_sample_index(es, index_name)
    load_sample_data(es, index_name)

app = FastAPI()

route_builder = ElasticsearchAPIRouteBuilder(
    es_client=es,
    index_name="sample-data"
)

query_builder = ElasticsearchAPIQueryBuilder()


@query_builder.filter()
def filter_items():
    return {
        "term": {
            "join_field": "item"
        }
    }


@query_builder.filter()
def filter_category(c: Optional[str] = Query(None,
                                             description="Category name to filter results.")):
    return {
        "term": {
            "category": c
        }
    } if c is not None else None


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


@query_builder.sorter()
def sort_by(so: Optional[str] = Query(None,
                                      description="Sort fields (uses format:'\\<field\\>,\\<direction\\>")):
    if so is not None:
        values = so.split(",")
        field = values[0]
        direction = values[1] if len(values) > 1 else "asc"
        sorter = {}
        sorter[field] = direction
        return sorter
    else:
        return None


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


@app.get("/search/debug")
async def search_debug(query_body: Dict = Depends(query_builder.build())) -> JSONResponse:
    return query_body


doc_query_builder = ElasticsearchAPIQueryBuilder(size=1, start_from=0)


@doc_query_builder.filter()
def filter_document(doc_id: str = Path(None, title="The id of the document.")):
    return {
        "ids": {"values": [doc_id]}
    }


doc_query_builder.add_matcher(match_fragments)


@app.get("/document/{doc_id}")
async def get_document(query_body: Dict = Depends(doc_query_builder.build())):
    resp = es.search(
        body=query_body,
        index=index_name
    )
    if resp["hits"]["total"]["value"] == 1:
        return resp["hits"]["hits"][0]
    else:
        raise HTTPException(status_code=404, detail="Document not found")
