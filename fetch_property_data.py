import googlemaps
import json
from geopy.distance import geodesic
from enum import Enum
from config import config

class CacheType(Enum):
    TRANSIT_INFO = 1
    TRANSIT_LOCATION = 2
    
class TransitCache:
    def __init__(self, cache_dir):
        self.dir = cache_dir
        self.info_cache = dict()
        self.locations_cache = dict()
        
    def load(self):
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
    
    def dump(self):
        with open(self.dir + '/info_cache.json', 'w') as json_file:
            json.dump(self.info_cache, json_file)
        
        with open(self.dir + '/locations_cache.json', 'w') as json_file:
            json.dump(self.locations_cache, json_file)
    
    def store(self, data, cache_type):
        code = data['code']
        if cache_type == CacheType.TRANSIT_INFO:
            if code not in self.info_cache:
                self.info_cache[code] = data
        elif cache_type == CacheType.TRANSIT_LOCATION:
            if code not in self.locations_cache:
                self.locations_cache[code] = data
        #Consider dumping less often
        self.dump()
    
    def fetch(self, property_data, cache_type):
        code = property_data['code']
        if cache_type == CacheType.TRANSIT_INFO:
            if code in self.info_cache:
                print('Found in cache...')
                return self.info_cache[code]
        elif cache_type == CacheType.TRANSIT_LOCATION:
            if code in self.locations_cache:
                print('Found in cache...')
                return self.locations_cache[code]
        return None

cache = TransitCache(config['cache']['cache_dir'])

def get_data_from_cache(cache_type, property_data):
    global cache
    return cache.fetch(property_data, cache_type)

def store_data_in_cache(cache_type, data):
    global cache
    cache.store(data, cache_type)
    
def cached(cache_type):
    def cached_function(func):
        def helper(*args, **kwargs):
            result = get_data_from_cache(cache_type, args[0])
            if result is None:
                result = func(*args, **kwargs)
                store_data_in_cache(cache_type, result)
                
            return result
        return helper
    return cached_function

def get_total_duration(destination):
    return destination[0]['legs'][0]['duration']['value']
    
def get_first_transit_point(steps):
    first_point = dict()
    
    time_to_point = 0
    for step in steps:
        print('Step ...')
        if step['travel_mode'] == 'WALKING':
            time_to_point = time_to_point + step['duration']['value']
        if step['travel_mode'] == 'TRANSIT':
            print('Transit step found')
            first_point['location'] = step['transit_details']['departure_stop']['location']
            first_point['name'] = step['transit_details']['departure_stop']['name']
            try:
                if 'name' in  step['transit_details']['line']:
                    first_point['name'] = first_point['name'] + " - " + step['transit_details']['line']['name']
                elif 'short_name' in  step['transit_details']['line']:
                    first_point['name'] = first_point['name'] + " - " + step['transit_details']['line']['short_name']
            except:
                print('You give the stop a bad name!')
            first_point['type'] = step['transit_details']['line']['vehicle']['type']
            first_point['walking_time'] = time_to_point
            return first_point
    
    return None
    
def get_transit_points(destination):
    steps = destination[0]['legs'][0]['steps']
    
    points = []
    point = get_first_transit_point(steps)
    print(point)
    if point is not None:
        print('Point added...')
        points.append(point)
    
    return points
            

def extract_transit_info(destination):
    info = dict()
    info['time'] = get_total_duration(destination)
    info['transit_types'] = ["WALKING"]
    info['transit_locations'] = get_transit_points(destination)
    for transit_location in info['transit_locations']:
        info['transit_types'].append(transit_location['type'])
    
    return info

def get_transit_info(origin, destination):
    gmaps = googlemaps.Client(key=config['gmaps']['api_key'])
    directions_result = gmaps.directions(origin, destination, mode="transit")
    #print(directions_result)
    return extract_transit_info(directions_result)
    #data = dict()
    #with open('test.json', 'r') as json_file:
    #    data = json.load(json_file)
    #return extract_info(data)

def extract_type(types):
    for type in types:
        if type == 'subway_station':
            return 'SUBWAY'
        elif type == 'bus_station':
            return 'BUS'
        elif type == 'light_rail_station':
            return 'LIGHT_RAIL'
    return 'TRANSIT'
    
def extract_transit_locations(locations):
    print(locations)
    transit_locations = []
    for location in locations['results']:
        transit_location = dict()
        transit_location['location'] = location['geometry']['location']
        transit_location['name'] = location['name']
        transit_location['type'] = extract_type(location['types'])
        transit_locations.append(transit_location)
    return transit_locations

def get_transit_locations(location, radius=500):
    gmaps = googlemaps.Client(key=config['gmaps']['api_key'])
    transit_locations = gmaps.places_nearby(location=location, radius=radius, type='subway_station')
    if transit_locations['status'] == 'ZERO_RESULTS':
        transit_locations = gmaps.places_nearby(location=location, radius=radius, type='bus_station')
    elif transit_locations['status'] == 'ZERO_RESULTS':
        transit_locations = gmaps.places_nearby(location=location, radius=radius, type='light_rail_station')
        
    return extract_transit_locations(transit_locations)

@cached(CacheType.TRANSIT_INFO)
def get_property_transit_info(property_data, destination):
    origin_str = str(property_data['location']['lat']) + ", " + str(property_data['location']['lng'])
    destination_str = str(destination['lat']) + ", " + str(destination['lng'])
    print('Origin: ' + origin_str)
    print('Destination: ' + destination_str)
    
    transit_info = get_transit_info(origin_str, destination_str)
    transit_info['code'] = property_data['code']
    
    for location in transit_info['transit_locations']:
        origin = (property_data['location']['lat'], property_data['location']['lng'])
        dest = (location['location']['lat'], location['location']['lng'])
        location['distance'] = int(geodesic(origin, dest).meters)
    
    return transit_info
    
def get_properties_transit_info(request):
    destination = request['destination']
    
    properties_transit_info = []
    for property in request['properties']:
        transit_info = get_property_transit_info(property, destination)
        if transit_info is not None:
            properties_transit_info.append(transit_info)
        
    return properties_transit_info

@cached(CacheType.TRANSIT_LOCATION)
def get_property_transit_locations(property_data):
    origin_str = str(property_data['location']['lat']) + ", " + str(property_data['location']['lng'])
    print('Location: ' + origin_str)
    
    property_transit_locations = dict()
    property_transit_locations['code'] = property_data['code']
    property_transit_locations['transit_locations'] = get_transit_locations(origin_str)
    
    for location in property_transit_locations['transit_locations']:
        origin = (property_data['location']['lat'], property_data['location']['lng'])
        dest = (location['location']['lat'], location['location']['lng'])
        location['distance'] = int(geodesic(origin, dest).meters)
    
    return property_transit_locations
    

def get_properties_nearby_transit_locations(request):
    properties_transit_locations = []
    for property in request['properties']:
        transit_locations = get_property_transit_locations(property)
        if transit_locations is not None:
            properties_transit_locations.append(transit_locations)
            
    return properties_transit_locations
    

def get_properties_transit_info_and_locations(request):
    destination = request['destination']
    
    properties_transit_info = []
    for property in request['properties']:
        transit_info = get_property_transit_info(property, destination)
        if transit_info is not None:
            if len(transit_info['transit_locations']) == 0:
                property_transit_locations = get_property_transit_locations(property)
                transit_info['transit_locations'] = property_transit_locations['transit_locations']
                
            properties_transit_info.append(transit_info)
        
    return properties_transit_info
    
cache.load()

#request = json.loads('{"destination": {"lat": "45.464116", "lng": "9.191663"}, "properties": [{"code": "XXPAR001", "location": {"lat": "45.466171", "lng": "9.166363"}}]}')
