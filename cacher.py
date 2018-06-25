import json
import os
from time import time
from DNS_packet import ResourceRecord


class Cache:
    def __init__(self):
        self.storage = {}

    def add(self, answer):
        key_for_answer = json.dumps([answer.name, answer.type, answer.rr_class])
        if key_for_answer in self.storage:
            self.storage[key_for_answer].append(json.dumps({
                'deadline': time() + answer.ttl,
                'type': answer.type,
                'class': answer.rr_class,
                'rdata': answer.rdata
            }))
        else:
            self.storage[key_for_answer] = [json.dumps({
                'deadline': time() + answer.ttl,
                'type': answer.type,
                'class': answer.rr_class,
                'rdata': answer.rdata
            })]

    def find(self, name, rr_type, rr_class):
        key = json.dumps([name, rr_type, rr_class])
        value = self.storage.get(key)
        if value is None:
            return
        else:
            rrs = []
            for element in value:
                loaded = json.loads(element)
                resource_record = ResourceRecord()
                resource_record.name = name
                resource_record.type = int(loaded['type'])
                resource_record.rr_class = int(loaded['class'])
                resource_record.ttl = int(int(loaded['deadline']) - time())
                resource_record.rdata = loaded['rdata']
                rrs.append(resource_record)
            return rrs

    def save(self):
        with open('cache.json', 'w') as f:
            json.dump(self.storage, f)

    def load(self):
        if not os.path.exists('cache.json'):
            return None
        with open('cache.json', 'r') as f:
            self.storage = json.load(f)

    def clear(self):
        for key in self.storage:
            rrs = self.storage[key]
            for rr in rrs:
                loaded = json.loads(rr)
                if int(loaded['deadline']) < time():
                    rrs.remove(rr)
        self.storage = {
            k: v for k, v in self.storage.items() if len(v) != 0
        }
