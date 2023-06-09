from typing import Any, Callable, Dict, List, Optional, Union

import forge
from fastapi import Depends, Query
from fastapi.dependencies.utils import analyze_param, get_typed_signature
from fastapi.types import DecoratedCallable


def combine(functions: List[Callable]):
    args_list = []
    funcs = []
    combined_args = {}
    for func in functions:
        if not callable(func):
            raise TypeError("Arguments must be callable")
        signature = get_typed_signature(func)
        signature_params = signature.parameters
        func_arg_names = set({})
        for param_name, param in signature_params.items():
            type_annotation, depends, param_field = analyze_param(
                param_name=param_name,
                annotation=param.annotation,
                value=param.default,
                is_path_param=False,
            )
            arg = forge.arg(
                name=param_field.name,
                type=param_field.outer_type_,
                default=param.default
            )
            if param_name in combined_args:
                current_arg = combined_args[param_name]
                if str(arg) != str(current_arg):
                    raise TypeError(
                        f"{arg} and {current_arg} are incompatible.")
            else:
                combined_args[param_name] = arg
            func_arg_names.add(param_name)
            args_list.append(arg)
        funcs.append((func, func_arg_names))

    def combined_functions(*args, **kwargs):
        result = []
        for (func, arg_names) in funcs:
            func_kwargs = dict((k, kwargs[k]) for k in arg_names)
            result.append(func(*args, **func_kwargs))
        return result

    new_args = tuple(combined_args.values())
    return forge.sign(*new_args)(combined_functions)


class ElasticsearchAPIQueryBuilder():
    def __init__(self,
                 *,
                 size: int = None,
                 start_from: int = None,
                 filters: List[Callable] = [],
                 matchers: List[Callable] = [],
                 highlighters: List[Callable] = [],
                 sorters: List[Callable] = []):
        self.build_search_body = self.default_build_search_body
        self.size_func = self.fixed_size(
            size) if size is not None else self.default_size
        self.start_from_func = self.fixed_start_from(
            start_from) if start_from is not None else self.default_start_from
        self.filters = filters.copy()
        self.matchers = matchers.copy()
        self.highlighters = highlighters.copy()
        self.sorters = sorters.copy()

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

    def fixed_size(self, size):
        def size_func():
            return size
        return size_func

    def default_size(self, size: Optional[int] = Query(10,
                                                       ge=0,
                                                       le=100,
                                                       alias="size",
                                                       description="Defines the number of hits to return."),
                     ):
        return size

    def size(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.size_func = func
            return func
        return decorator

    def set_size(self, new_size: Union[Callable, int]):
        if callable(new_size):
            self.size_func = new_size
        else:
            self.size_func = self.fixed_size(new_size)

    def fixed_start_from(self, start_from):
        def start_from_func():
            return start_from
        return start_from_func

    def default_start_from(self, start_from: Optional[int] = Query(0,
                                                                   ge=0,
                                                                   alias="from",
                                                                   description="Starting document offset."),

                           ):
        return start_from

    def start_from(self):
        def decorator(func: Callable) -> DecoratedCallable:
            self.start_from_func = func
            return func
        return decorator

    def set_start_from(self, new_start_from: Union[Callable, int]):
        if callable(new_start_from):
            self.start_from_func = new_start_from
        else:
            self.start_from_func = self.fixed_start_from(new_start_from)

    def default_build_search_body(self,
                                  size: int = 10,
                                  start_from: int = 0,
                                  source: Union[List, Dict, str] = None,
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
        else:
            query["match_all"] = {}

        body = {
            "query": query,
            "size": size,
            "from": start_from,
        }
        if (source is not None):
            body["_source"] = source

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

    def build(self,
              source: Union[List, Dict, str] = None,
              minimum_should_match: int = 1) -> Callable:

        filters_functions = combine(self.filters)
        matchers_functions = combine(self.matchers)
        highlighters_functions = combine(self.highlighters)
        sorters_functions = combine(self.sorters)

        def builder(
                size: int = Depends(self.size_func),
                start_from: int = Depends(self.start_from_func),
                filters=Depends(filters_functions),
                matchers=Depends(matchers_functions),
                highlighters=Depends(highlighters_functions),
                sorters=Depends(sorters_functions)):
            filters = list(filter(lambda f: f is not None, filters))
            matchers = list(filter(lambda f: f is not None, matchers))
            highlighters = list(filter(lambda f: f is not None, highlighters))
            sorters = list(filter(lambda f: f is not None, sorters))
            return self.build_search_body(
                size=size,
                start_from=start_from,
                source=source,
                minimum_should_match=minimum_should_match,
                filters=filters,
                matchers=matchers,
                highlighters=highlighters,
                sorters=sorters,
            )
        return builder
