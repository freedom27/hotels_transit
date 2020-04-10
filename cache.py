import json
from enum import Enum
import threading
import time

class CacheType(Enum):
    TRANSIT_INFO = 1
    TRANSIT_LOCATION = 2
    
class TransitCache:
    def __init__(self, cache_dir):
        self.lock_info = threading.Lock()
        self.lock_locations = threading.Lock()
        self.dir = cache_dir
        self.info_cache = dict()
        self.locations_cache = dict()
        self.new_data = False
        self._load()
        
        self.persistency_thread = threading.Thread(target=self._persistency_process)
        self.persistency_thread.start()
        
    def _load(self):
        try:
            with open(self.dir + '/info_cache.json', 'r') as json_file:
                self.info_cache = json.load(json_file)
        except:
            print('Bad Info Cache File!')
            
        try:
            with open(self.dir + '/locations_cache.json', 'r') as json_file:
                self.locations_cache = json.load(json_file)
        except:
            print('Bad Location Cache File!')
    
    def _dump(self):
        print('Dumping...')
        self.lock_info.acquire()
        with open(self.dir + '/info_cache.json', 'w') as json_file:
            json.dump(self.info_cache, json_file)
        self.lock_info.release()
        
        self.lock_locations.acquire()
        with open(self.dir + '/locations_cache.json', 'w') as json_file:
            json.dump(self.locations_cache, json_file)
        self.lock_locations.release()
        self.new_data = False
        
    def _persistency_process(self):
        time_to_sleep = 240 #seconds
        
        while True:
            time.sleep(time_to_sleep)
            if self.new_data:
                self._dump()
    
    def store(self, data, cache_type):
        code = data['code']
        if cache_type == CacheType.TRANSIT_INFO:
            self.lock_info.acquire()
            if code not in self.info_cache:
                self.info_cache[code] = data
                self.new_data = True
            self.lock_info.release()
        elif cache_type == CacheType.TRANSIT_LOCATION:
            self.lock_locations.acquire()
            print('Lock acquired')
            if code not in self.locations_cache:
                self.locations_cache[code] = data
                self.new_data = True
            self.lock_locations.release()

    
    def fetch(self, property_data, cache_type):
        code = property_data['code']
        data = None
        if cache_type == CacheType.TRANSIT_INFO:
            self.lock_info.acquire()
            if code in self.info_cache:
                data = self.info_cache[code]
            self.lock_info.release()
        elif cache_type == CacheType.TRANSIT_LOCATION:
            self.lock_locations.acquire()
            if code in self.locations_cache:
                data = self.locations_cache[code]
            self.lock_locations.release()
        return data
