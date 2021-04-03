from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union

from elasticsearch import Elasticsearch
from fastapi import Depends, FastAPI, Query, Request, params
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.dependencies.utils import get_dependant, request_params_to_args
from fastapi.encoders import DictIntStrAny, SetIntStr
from fastapi.routing import APIRoute, APIRouter
from fastapi.types import DecoratedCallable
from starlette import routing
from starlette.responses import JSONResponse, Response
from starlette.routing import BaseRoute
from starlette.types import ASGIApp


class ElasticsearchAPIQueryBuilder():
    def __init__(self,
                 *,
                 filters: List[Callable] = [],
                 matchers: List[Callable] = [],
                 highlighters: List[Callable] = [],
                 sorters: List[Callable] = []):
        self.build_search_body = self.default_build_search_body
        self.filters = filters.copy()
        self.matchers = matchers.copy()
        self.highlighters = highlighters.copy()
        self.sorters = sorters.copy()
        self.path = None

    def copy(self):
        c = ElasticsearchAPIQueryBuilder()
        c.build_search_body = self.build_search_body
        c.filters = self.filters.copy()
        c.matchers = self.matchers.copy()
        c.highlighters = self.highlighters.copy()
        c.sorters = self.sorters.copy()
        return c

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

    def default_build_search_body(self,
                                  size: int = 10,
                                  start_from: int = 0,
                                  source: Union[List, Dict, str] = None,
                                  scroll: str = None,
                                  minimum_should_match: int = 1,
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
                bool_query["minimum_should_match"] = minimum_should_match

        body = {
            "query": query,
            "size": size,
            "from": start_from,
        }
        if (source is not None):
            body["source"] = source

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

    def get_dependencies(self):
        dependencies = []
        [dependencies.append(Depends(f)) for f in self.filters]
        [dependencies.append(Depends(f)) for f in self.matchers]
        [dependencies.append(Depends(f)) for f in self.highlighters]
        [dependencies.append(Depends(f)) for f in self.sorters]
        return dependencies

    def call_builders(self, request: Request, funcs: List[Callable]):
        builders = []
        for f in funcs:
            dependant = get_dependant(path=self.path, call=f)
            path_values, path_errors = request_params_to_args(
                dependant.path_params, request.path_params
            )
            query_values, query_errors = request_params_to_args(
                dependant.query_params, request.query_params
            )
            header_values, header_errors = request_params_to_args(
                dependant.header_params, request.headers
            )
            cookie_values, cookie_errors = request_params_to_args(
                dependant.cookie_params, request.cookies
            )
            values: Dict[str, Any] = {}
            values.update(path_values)
            values.update(query_values)
            values.update(header_values)
            values.update(cookie_values)
            result = dependant.call(**values)
            if result is not None:
                builders.append(result)
        return builders

    def build_body(self,
                   request: Request,
                   size: int = 10,
                   start_from: int = 0,
                   source: Union[List, Dict, str] = None,
                   scroll: str = None,
                   minimum_should_match: int = 1) -> Dict:
        (
            filter_queries,
            matchers_queries,
            highlight_fields,
            sort_fields,
        ) = self.call_query_builders(request)

        body = self.build_search_body(
            size=size,
            start_from=start_from,
            source=source,
            scroll=scroll,
            minimum_should_match=minimum_should_match,
            filters=filter_queries,
            matchers=matchers_queries,
            highlighters=highlight_fields,
            sorters=sort_fields,
        )

        return body

    def __call__(self, req: Request) -> Dict:
        return self.build_body(req)

    def build(self,
              size: int = 10,
              start_from: int = 0,
              source: Union[List, Dict, str] = None,
              scroll: str = None,
              minimum_should_match: int = 1) -> Callable:
        def builder(req: Request):
            return self.build_body(
                req,
                size=size,
                start_from=start_from,
                source=source,
                scroll=scroll,
                minimum_should_match=minimum_should_match
            )
        return builder


class ElasticsearchAPIRouteBuilder():
    def __init__(self,
                 query_builder: ElasticsearchAPIQueryBuilder = None,
                 *,
                 es_client: Elasticsearch = None,
                 index_name: str = None,
                 doc_type: str = None,
                 params: Dict = None,
                 headers: Dict = None,
                 route_class: Type[APIRoute] = APIRoute,):
        self.query_builder = query_builder or ElasticsearchAPIQueryBuilder()
        self.es_client = es_client
        self.index_name = index_name
        self.doc_type = doc_type
        self.params = params.copy() if params != None else None
        self.headers = headers.copy() if headers != None else None
        self.route_class = route_class

        self.set_endpoint(self.default_endpoint(), None)

    def copy(self):
        c = ElasticsearchAPIRouteBuilder()

        c.query_builder = self.query_builder.copy()
        c.es_client = self.es_client
        c.index_name = self.index_name
        c.doc_type = self.doc_type
        c.params = self.params.copy() if self.params != None else None
        c.headers = self.headers.copy() if self.headers != None else None
        self.route_class = self.route_class

        return c

    def use_client(self, es_client: Elasticsearch):
        self.es_client = es_client

    def search_builder(self) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: Callable) -> DecoratedCallable:
            self.query_builder.build_search_body = func
            return func
        return decorator

    def add_filter(self, func: Callable):
        self.query_builder.add_filter(func)

    def filter(self) -> Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_filter(func)
            return func
        return decorator

    def add_matcher(self, func: Callable):
        self.query_builder.add_matcher(func)

    def matcher(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_matcher(func)
            return func
        return decorator

    def add_highlighter(self, func: Callable):
        self.query_builder.add_highlighter(func)

    def highlighter(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_highlighter(func)
            return func
        return decorator

    def add_sorter(self, func: Callable):
        self.query_builder.add_sorter(func)

    def sorter(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.add_sorter(func)
            return func
        return decorator

    def set_endpoint(self,
                     func: Callable,
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
                     name: Optional[str] = None,
                     callbacks: Optional[List[BaseRoute]] = None):
        responses = responses or {}
        self.callable = func
        self.path = path
        self.response_model = response_model
        self.status_code = status_code
        self.tags = tags
        self.summary = summary
        self.description = description
        self.response_description = response_description
        self.responses = responses
        self.deprecated = deprecated
        self.methods = methods
        self.operation_id = operation_id
        self.response_model_include = response_model_include
        self.response_model_exclude = response_model_exclude
        self.response_model_by_alias = response_model_by_alias
        self.response_model_exclude_unset = response_model_exclude_unset
        self.response_model_exclude_defaults = response_model_exclude_defaults
        self.response_model_exclude_none = response_model_exclude_none
        self.include_in_schema = include_in_schema
        self.response_class = response_class
        self.name = name
        self.callbacks = callbacks

        self.query_builder.path = path

    def endpoint(self,
                 path: str,
                 **kwargs):
        def decorator(func: Callable) -> DecoratedCallable:
            self.set_endpoint(func,
                              path,
                              **kwargs)
            return func
        return decorator

    def default_endpoint(self):
        async def endpoint(
            req: Request,
            size: Optional[int] = Query(10,
                                        le=100,
                                        alias="s",
                                        description="Defines the number of hits to return."),
            start_from: Optional[int] = Query(0,
                                              alias="f",
                                              description="Starting document offset.")
        ) -> JSONResponse:
            query_body = self.query_builder.build_body(
                request=req,
                size=size,
                start_from=start_from,
            )
            return self.es_client.search(
                body=query_body,
                index=self.index_name,
                doc_type=self.doc_type,
                params=self.params,
                headers=self.headers
            )
        return endpoint

    def build(self, path: str = None, query_builder: ElasticsearchAPIQueryBuilder = None):
        current_query_builder = query_builder or self.query_builder
        current_dependencies = current_query_builder.get_dependencies()
        current_path = path or self.path
        current_endpoint = self.callable or self.default_endpoint()
        current_query_builder.path = current_path
        route = self.route_class(
            current_path,
            endpoint=current_endpoint,
            response_model=self.response_model,
            status_code=self.status_code,
            tags=self.tags,
            dependencies=current_dependencies,
            summary=self.summary,
            description=self.description,
            response_description=self.response_description,
            responses=self.responses,
            deprecated=self.deprecated,
            methods=self.methods,
            operation_id=self.operation_id,
            response_model_include=self.response_model_include,
            response_model_exclude=self.response_model_exclude,
            response_model_by_alias=self.response_model_by_alias,
            response_model_exclude_unset=self.response_model_exclude_unset,
            response_model_exclude_defaults=self.response_model_exclude_defaults,
            response_model_exclude_none=self.response_model_exclude_none,
            include_in_schema=self.include_in_schema,
            response_class=self.response_class,
            name=self.name,
            callbacks=self.callbacks,
        )
        return route
