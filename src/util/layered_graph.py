from __future__ import annotations

def find_all_paths_efficient(graph, 
    start: int=0, 
    layer: int=0, 
    cur_path: list=None, 
    max_layer: int=None, 
    store: list=None):
    """ Sped up version of find_all_paths that does not perform copious amounts o
        of copying.
    start: integer representing vertex index within starting layer
    layer: integer containing starting layer index.
    path: previously constructed path to be added. 
          TODO: Speedup, consider alternate to using tuples to represent paths 
          since that makes us keep reconstructing/copying. Consider DFS/BFS instead.
    max_layer: last layer (inclusive) that we will be terminating. If `None`,
          use num_layers - 1 by default.
    """
    num_layers = len(graph)
    if max_layer is None:
        max_layer = num_layers - 1
    if store is None: # Don't use immutable objects like lists as default variables 
        store = []
    if cur_path is None: # Don't use immutable objects like lists as default variables 
        cur_path = []
    
    assert max_layer >= layer

    cur_path.append(start)
    if max_layer == layer:
        store.append(tuple(cur_path))
    else:
        for node in graph[layer][start]:
            find_all_paths_efficient(graph, 
                start = node,
                layer=layer+1,
                cur_path=cur_path,
                max_layer = max_layer,
                store = store)
    cur_path.pop()
    return store

def find_all_paths(graph, start=0, layer=0, path=(), max_layer = None):
    """ NOTE: uses recursion to compute. Exceedingly slow. Use with caution.
    start: integer representing vertex index within starting layer
    layer: integer containing starting layer index.
    path: previously constructed path to be added. 
          TODO: Speedup, consider alternate to using tuples to represent paths 
          since that makes us keep reconstructing/copying. Consider DFS/BFS instead.
    max_layer: last layer (inclusive) that we will be terminating. If `None`,
          use num_layers - 1 by default.
    """
    num_layers = len(graph)
    if max_layer is None:
        max_layer = num_layers - 1
    path = path + (start,)
    paths = []
    if len(graph[layer][start]) == 0 and layer == max_layer: # num_layers-1:  # No neighbors
        paths = [path]
        # print(path)
    for node in graph[layer][start]:
        newpaths = find_all_paths(graph, node, layer+1, path)
        for newpath in newpaths:
            paths.append(newpath)
    return paths

def find_num_paths(graph, start=0, layer=0, memiomization=None):
    num_layers = len(graph)

    if memiomization is None:
        memiomization = dict()
    else:
        if (layer, start) in memiomization:
            return memiomization[(layer, start)]

    num_paths = 0

    # Technically we could do away with the second condition since 
    # by design we ensure that vertices in the last layer have not 
    # neighbors.
    if len(graph[layer][start]) == 0 and layer == num_layers -1: 
        return 1

    for next_node in graph[layer][start]:
        newpaths = find_num_paths(graph, next_node, layer+1, memiomization)
        num_paths += newpaths
    
    memiomization[(layer, start)] = num_paths

    return num_paths