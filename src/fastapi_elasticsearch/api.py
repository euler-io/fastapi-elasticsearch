from typing import (
    Callable,
    List,
    Optional,
    Type,
    Any,
    Dict,
    Union,
    Sequence)
from fastapi.dependencies.utils import (
    get_dependant, request_params_to_args
)
from fastapi import Request, FastAPI, Depends
from fastapi.routing import APIRoute
from fastapi.types import DecoratedCallable
from starlette.responses import JSONResponse, Response
from elasticsearch import Elasticsearch
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.encoders import DictIntStrAny, SetIntStr


class ElasticsearchAPI:
    def __init__(self,
                 es_client: Elasticsearch,
                 index_name: str,
                 source=None,
                 filters: List[Callable] = [],
                 matchers: List[Callable] = [],
                 highlighters: List[Callable] = [],
                 sorters: List[Callable] = []):
        self.es_client = es_client
        self.index_name = index_name
        self.source = source
        self.filters = filters.copy()
        self.matchers = matchers.copy()
        self.highlighters = highlighters.copy()
        self.sorters = sorters.copy()
        self.build_search_body = self.default_build_search_body

    def search_builder(self) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: Callable) -> DecoratedCallable:
            self.build_search_body = func
            return func
        return decorator

    def add_filter(self, func: Callable):
        self.filters.append(func)

    def filter(self) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_filter(func)
            return func
        return decorator

    def add_matcher(self, func: Callable):
        self.matchers.append(func)

    def matcher(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_matcher(func)
            return func
        return decorator

    def add_highlighter(self, func: Callable):
        self.highlighters.append(func)

    def highlighter(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_highlighter(func)
            return func
        return decorator

    def add_sorter(self, func: Callable):
        self.sorters.append(func)

    def sorter(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_sorter(func)
            return func
        return decorator

    def search_route(self,
                     app: FastAPI,
                     path: str,
                     *,
                     response_model: Optional[Type[Any]] = None,
                     status_code: int = 200,
                     tags: Optional[List[str]] = None,
                     dependencies: Optional[Sequence[Depends]] = None,
                     summary: Optional[str] = None,
                     description: Optional[str] = None,
                     response_description: str = "Successful Response",
                     responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
                     deprecated: Optional[bool] = None,
                     methods: Optional[List[str]] = None,
                     operation_id: Optional[str] = None,
                     response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
                     response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
                     response_model_by_alias: bool = True,
                     response_model_exclude_unset: bool = False,
                     response_model_exclude_defaults: bool = False,
                     response_model_exclude_none: bool = False,
                     include_in_schema: bool = True,
                     response_class: Union[Type[Response], DefaultPlaceholder] = Default(
            JSONResponse
                         ),
                     name: Optional[str] = None):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_search_route(app,
                                  path,
                                  func,
                                  response_model=response_model,
                                  status_code=status_code,
                                  tags=tags,
                                  dependencies=dependencies,
                                  summary=summary,
                                  description=description,
                                  response_description=response_description,
                                  responses=responses,
                                  deprecated=deprecated,
                                  methods=methods,
                                  operation_id=operation_id,
                                  response_model_include=response_model_include,
                                  response_model_exclude=response_model_exclude,
                                  response_model_by_alias=response_model_by_alias,
                                  response_model_exclude_unset=response_model_exclude_unset,
                                  response_model_exclude_defaults=response_model_exclude_defaults,
                                  response_model_exclude_none=response_model_exclude_none,
                                  include_in_schema=include_in_schema,
                                  response_class=response_class,
                                  name=name,)
            return func
        return decorator

    def add_search_route(self,
                         app: FastAPI,
                         path: str,
                         endpoint: Callable[..., Any],
                         *,
                         response_model: Optional[Type[Any]] = None,
                         status_code: int = 200,
                         tags: Optional[List[str]] = None,
                         dependencies: Optional[Sequence[Depends]] = None,
                         summary: Optional[str] = None,
                         description: Optional[str] = None,
                         response_description: str = "Successful Response",
                         responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
                         deprecated: Optional[bool] = None,
                         methods: Optional[List[str]] = None,
                         operation_id: Optional[str] = None,
                         response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
                         response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
                         response_model_by_alias: bool = True,
                         response_model_exclude_unset: bool = False,
                         response_model_exclude_defaults: bool = False,
                         response_model_exclude_none: bool = False,
                         include_in_schema: bool = True,
                         response_class: Union[Type[Response], DefaultPlaceholder] = Default(
            JSONResponse
                         ),
                         name: Optional[str] = None):

        new_dependencies = [] if dependencies is None else dependencies.copy()
        new_dependencies.extend(self.get_dependencies())

        app.add_api_route(path,
                          endpoint,
                          response_model=response_model,
                          status_code=status_code,
                          tags=tags,
                          dependencies=new_dependencies,
                          summary=summary,
                          description=description,
                          response_description=response_description,
                          responses=responses,
                          deprecated=deprecated,
                          methods=methods,
                          operation_id=operation_id,
                          response_model_include=response_model_include,
                          response_model_exclude=response_model_exclude,
                          response_model_by_alias=response_model_by_alias,
                          response_model_exclude_unset=response_model_exclude_unset,
                          response_model_exclude_defaults=response_model_exclude_defaults,
                          response_model_exclude_none=response_model_exclude_none,
                          include_in_schema=include_in_schema,
                          response_class=response_class,
                          name=name,)

    def get_dependencies(self):
        dependencies = []
        [dependencies.append(Depends(f)) for f in self.filters]
        [dependencies.append(Depends(f)) for f in self.matchers]
        [dependencies.append(Depends(f)) for f in self.highlighters]
        [dependencies.append(Depends(f)) for f in self.sorters]
        return dependencies

    def call_query_builders(self, request: Request):
        filter_queries = self.call_builders(request, self.filters)
        matchers_queries = self.call_builders(request, self.matchers)
        highlight_fields = self.call_builders(request, self.highlighters)
        sort_fields = self.call_builders(request, self.sorters)
        return (
            filter_queries,
            matchers_queries,
            highlight_fields,
            sort_fields,
        )

    def default_build_search_body(self,
                                  size: int = 10,
                                  start_from: int = 0,
                                  scroll: str = None,
                                  filters: List[Dict] = [],
                                  matchers: List[Dict] = [],
                                  highlighters: List[Dict] = [],
                                  sorters: List[Dict] = []) -> Dict:
        query = {}
        if len(filters) > 0 or len(matchers) > 0:
            bool_query = {}
            query["bool"] = bool_query
            if len(filters) > 0:
                bool_query["filter"] = filters
            if len(matchers) > 0:
                bool_query["should"] = matchers
                bool_query["minimum_should_match"] = 1

        body = {
            "query": query,
            "size": size,
            "from": start_from,
        }
        if (self.source is not None):
            body["source"] = self.source

        if (scroll is not None):
            body["scroll"] = scroll

        if len(highlighters) > 0:
            highlight = {}
            for h in highlighters:
                highlight.update(h)
            body["highlight"] = {
                "fields": highlight
            }

        if len(sorters) > 0:
            body["sort"] = sorters

        return body

    def build_query(self,
              request: Request,
              size: int = 10,
              start_from: int = 0,
              scroll: str = None) -> JSONResponse:
        (
            filter_queries,
            matchers_queries,
            highlight_fields,
            sort_fields,
        ) = self.call_query_builders(request)

        body = self.build_search_body(
            size=size,
            start_from=start_from,
            scroll=scroll,
            filters=filter_queries,
            matchers=matchers_queries,
            highlighters=highlight_fields,
            sorters=sort_fields,
        )

        return body

    def search(self,
               request: Request,
               size: int = 10,
               start_from: int = 0,
               scroll: str = None) -> JSONResponse:

        body = self.build_query(
            request=request,
            size=size,
            start_from=start_from,
            scroll=scroll
        )

        return self.es_client.search(
            index=self.index_name,
            body=body
        )

    def call_builders(self, request: Request, funcs: List[Callable]):
        builders = []
        for f in funcs:
            dependant = get_dependant(path='', call=f)
            filter_params = request_params_to_args(
                dependant.query_params,
                request.query_params)
            (values, errors) = filter_params
            result = dependant.call(**values)
            if result is not None:
                builders.append(result)
        return builders
