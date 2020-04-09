from multiprocessing.pool import ThreadPool
import math
import copy


def cached(cache, cache_type):
    def cached_function(func):
        def helper(*args, **kwargs):
            result = cache.fetch(args[0], cache_type)
            if result is None:
                result = func(*args, **kwargs)
                cache.store(result, cache_type)
                
            return result
        return helper
    return cached_function


def parallel(max_threads):
    def parallel_function(func):
        def helper(*args, **kwargs):
            base_rq = args[0]
            properties = base_rq['properties']
            properties_count = len(base_rq['properties'])
            poperties_per_thread = math.ceil(properties_count / max_threads)
            properties_sub_groups = [properties[i * poperties_per_thread:(i + 1) * poperties_per_thread] for i in range((properties_count + poperties_per_thread - 1) // poperties_per_thread )]
            
            pool = ThreadPool(processes=max_threads)
            threads = []
            for properties_list in properties_sub_groups:
                new_rq = copy.copy(base_rq)
                new_rq['properties'] = properties_list
                threads.append(pool.apply_async(func, (new_rq,)))
            
            results = []
            for thread in threads:
                for data in thread.get():
                    results.append(data)
            
            return results
        return helper
    return parallel_function