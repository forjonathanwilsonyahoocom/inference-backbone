"""
Metrics abstraction currently making Prometheus scraped endpoint data
"""
from prometheus_client import Counter, Gauge
import time
from typing import Dict, List

example_message = {"type": "counter",
                   "name": "example1",
                   "description": "showing with optional value of 42",
                   "value": 42}

example_message = {"type": "counter",
                   "name": "example1",
                   "description": "showing optional labels AND optional value of 42",
                   "labels": {"some_label": "87666", "other_label": "876", "another_label_etc": "some_value_etc"},
                   "value": 42}

example_message = {"type": "counter",
                   "name": "example2",
                   "description": "showing use of default inc of 1"}


class MetricsWrapper:
    def __init__(self, service_name: str):
        self.counters = {}
        self.service_name = service_name
        self.gauges = {}
        
    def clear_counters(self):
        for k, metric in self.counters.items()
            metric.reset()
            
    def emit(self, msg: Dict):
        try:
            if msg['type'] == "counter":
                c = self.counters.get(msg['name'], "missing")
                if c == "missing":
                    c = Counter(f"{self.service_name}_{msg['name']}", msg['description'], list(msg.get('labels', {}).keys()))

                if 'labels' in msg:
                    c.labels(*list(msg.get('labels', {}).values())).inc(msg.get('value', 1))
                else:
                    c.inc(msg.get('value', 1))

                self.counters[msg['name']] = c
            elif msg['type'] == "gauge":
                c = self.gauges.get(msg['name'], "missing")
                if c == "missing":
                    c = Gauge(f"{self.service_name}_{ msg['name']}", msg['description'])

                c.set(msg.get('value', 1))

                self.gauges[msg['name']] = c
        except Exception as e:
            print(e)
        

    def get_counter_message(self, name, description, value=1):
        return {"type": "counter",
                "name": name,
                "description": description,
                "value" : value}


    def get_gauge_func(self, name, description):
        def gauge_takes_value(value):
            return {"type": "gauge",
                    "name": name,
                    "description": description,
                    "value" : value}
        return gauge_takes_value


    def get_counter_message_labeler(self, name, description):
        # call the function with a map of labels.
        # the labels NAMES must be the same for all calls to the same counter
        def labeler(labels, value=1):
            return {"type": "counter",
                    "name": name,
                    "description": description,
                    "labels": labels,
                    "value" : value}

        return labeler


    def get_metric_label(self, location=None, exception=None):
      
        reported_exception = "none"

        if location is None:
            location = self.service_name

        if exception != None:
            reported_exception = f"{repr(exception)}{getattr(exception, 'message', 'no_message')}"

        return {"location" : location, "exception": reported_exception}

