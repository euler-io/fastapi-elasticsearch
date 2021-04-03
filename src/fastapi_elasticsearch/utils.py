import logging
import time

from elasticsearch import Elasticsearch


def wait_elasticsearch(es: Elasticsearch,
                       interval=2000,
                       max_retries=30,
                       params=None,
                       headers=None):
    attempts = 0
    while attempts < max_retries:
        try:
            resp = es.info(params=params, headers=headers)
            logging.info("Connected to elasticsearch.")
            return resp
        except:
            logging.warn(
                f"Could not connect to Elasticsearch. Retry will occur in {interval}ms.")
            attempts += 1
            time.sleep(interval/1000)
    raise Exception("Could not connect to Elasticsearch.")
