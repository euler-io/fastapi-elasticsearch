from fastapi import FastAPI, Request, Query
from typing import Optional
from elasticsearch import Elasticsearch
from starlette.responses import JSONResponse
from development.loaddata import create_sample_index, load_sample_data
from fastapi_elasticsearch.utils import wait_elasticsearch
from fastapi_elasticsearch import ElasticsearchAPIRouter

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

es_router = ElasticsearchAPIRouter(
    index_name=index_name
)

@es_router.filter()
def filter_items():
    return {
        "term": {
            "join_field": "item"
        }
    }


@es_router.filter()
def filter_category(c: Optional[str] = Query(None,
                                             description="Category name to filter results.")):
    return {
        "term": {
            "category": c
        }
    } if c is not None else None


@es_router.matcher()
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


@es_router.matcher()
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


@es_router.sorter()
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


@es_router.highlighter()
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


@es_router.search_route("/search")
async def search(req: Request,
                 size: Optional[int] = Query(10,
                                             le=100,
                                             alias="s",
                                             description="Defines the number of hits to return."),
                 start_from: Optional[int] = Query(0,
                                                   alias="f",
                                                   description="Starting document offset."),
                 scroll: Optional[str] = Query(None,
                                               description="Period to retain the search context for scrolling."),
                 ) -> JSONResponse:
    return es_router.search(
        es_client=es,
        request=req,
        size=size,
        start_from=start_from,
        scroll=scroll,
    )


@es_router.search_route("/search/debug")
async def search_debug(req: Request,
                       size: Optional[int] = Query(10,
                                                   le=100,
                                                   alias="s",
                                                   description="Defines the number of hits to return."),
                       start_from: Optional[int] = Query(0,
                                                         alias="f",
                                                         description="Starting document offset."),
                       scroll: Optional[str] = Query(None,
                                                     description="Period to retain the search context for scrolling."),
                       ):
    return es_router.build_query(
        request=req,
        size=size,
        start_from=start_from,
        scroll=scroll,
    )


app = FastAPI()
app.include_router(es_router)
