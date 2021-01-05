from elasticsearch import Elasticsearch
import logging
import time


def wait_elasticsearch(es: Elasticsearch, interval=2000, max_retries=30):
    attempts = 0
    last_error = None
    while attempts < max_retries:
        try:
            resp = es.info()
            logging.info("Connected to elasticsearch.")
            return resp
        except Exception as e:
            logging.warn(
                f"Could not connect to Elasticsearch. Retry will occur in {interval}ms.")
            attempts += 1
            time.sleep(interval/1000)
            last_error = e
    raise Exception("Could not connect to Elasticsearch.", last_error)
