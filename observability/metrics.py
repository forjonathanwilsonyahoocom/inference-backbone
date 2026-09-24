"""
Metrics abstraction currently making Prometheus scraped endpoint data
"""
from prometheus_client import Counter, Gauge
import time
from typing import Dict

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
        self.gauge_avg = {}
        
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
                a = self.gauge_avg.get(msg['name'], {"total" : 0, "n" : 0})
                if c == "missing":
                    c = Gauge(f"{self.service_name}_{ msg['name']}", msg['description'])

                a["total"] = a["total"] + msg.get('value', 1)
                a["n"] = a["n"] + 1
                
                c.set(a["total"]/a["n"])

                if a["total"] > 60:
                    a["total"] = a["total"] / 2
                    a["n"] = a["n"] / 2

                self.gauges[msg['name']] = c
                self.gauge_avg[msg['name']] = a
        except Exception as e:
            print(e)
        

    def get_counter_message(name, description):
        return {"type": "counter",
                "name": name,
                "description": description}


    def get_gauge_func(name, description):
        def gauge_takes_value(value):
            return {"type": "gauge",
                    "name": name,
                    "description": description,
                    "value" : value}
        return gauge_takes_value


    def get_counter_message_labeler(name, description):
        # call the function with a map of labels.
        # the labels NAMES must be the same for all calls to the same counter
        def labeler(labels):
            return {"type": "counter",
                    "name": name,
                    "description": description,
                    "labels": labels}

        return labeler


    def get_metric_label(self, location=None, exception=None):
      
        reported_exception = "none"

        if location is None:
            location = self.service_name

        if exception != None:
            reported_exception = f"{repr(exception)}{getattr(exception, 'message', 'no_message')}"

        return {"location" : location, "exception": reported_exception}

