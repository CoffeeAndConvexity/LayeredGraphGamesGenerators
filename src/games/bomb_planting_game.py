from __future__ import annotations

from numpy import number 
from src.games.layered_game import LayeredGame, ClosenessFn
import networkx as nx
from collections import deque

class BombPlantingGame(LayeredGame):
    def __init__(self,
                 nx_graph_atk: nx.MultiDiGraph,
                 nx_graph_def: nx.MultiDiGraph,
                 source_atk: list[int],
                 source_def: list[int],
                 target_vals: list[float],
                 max_depth: int,
                 time_bomb: int,
                 closeness_type: str):

        assert max_depth > 0
        assert max_depth >= time_bomb
        self.sanity_check(nx_graph_atk)
        self.sanity_check(nx_graph_def)
        assert nx_graph_atk.number_of_nodes() == nx_graph_def.number_of_nodes()
        assert len(target_vals) == nx_graph_atk.number_of_nodes()
        self.time_bomb = time_bomb

        # We introduce three dummy vertices over two layers.
        # First layer has a single source with index 0 (RESTRICTION BY DESIGN).
        # Second layer has two vertices (0 and 1), one for each player. Only one vertex
        # has outgoing edges, these lead to the possible starting nodes in the 3rd layer.
        # Third to last layer are max_depth number layers obtaned from unrolling.
        # The last layer has no outgoing vertices (RESTRICTION BY DESIGN).
        atk_connections = self.do_bfs_atk(
            nx_graph_atk, source_atk, max_depth)
        def_connections = self.do_bfs_def(
            nx_graph_def, source_def, max_depth)
        target_vals = target_vals.copy()

        if closeness_type == 'exact_edge':
            closeness_fn_atk_path, closeness_fn_def_path = self.exact_edge_closeness(
                atk_connections, def_connections, nx_graph_atk.number_of_nodes(), time_bomb)

        elif closeness_type == 'share_dst_vertex':
            closeness_fn_atk_path, closeness_fn_def_path = self.vertex_ending_closeness(
                atk_connections, def_connections, nx_graph_atk.number_of_nodes(), time_bomb)

        expanded_target_vals = self.expanded_target_vals(target_vals, nx_graph_atk.number_of_nodes(), time_bomb)

        super().__init__(atk_connections, def_connections, expanded_target_vals,
                         closeness_fn_atk_path, closeness_fn_def_path)

    def do_bfs_atk(self,
                   nx_digraph: nx.MultiDiGraph,
                   start_nodes: list[int],
                   d_max: int):

        ATK_DUMMY_NODE_ID = 0

        # Initialize connections in first two layers.
        connections = [[[0]], [[], []]] + [[[] for node_idx in range(
            nx_digraph.number_of_nodes() * (self.time_bomb + 1))] for layer_id in range(d_max)]

        # connect from the pair of dummy nodes in the second layer to starting vertics.
        connections[1][ATK_DUMMY_NODE_ID] = start_nodes.copy()

        visited = set()

        # Initialize the BFS queue, which contains elements of the form.
        #         (starting node id, depth, time spent planting bomb)
        queue = deque([(start_node, 2, 0) for start_node in start_nodes])

        while queue:
            node, depth, wait = queue.popleft()
            if (node, depth, wait) in visited:
                continue
            visited.add((node, depth, wait))

            if depth >= d_max + 1:
                continue

            if wait == 0:
                # Option 1:
                # Do *normal* move to neighbor (could be self if nx_digraph has loops)
                neighbors = nx_digraph.neighbors(node)
                for neighbor in neighbors:
                    if depth < d_max + 1:
                        connections[depth][node].append(neighbor)
                    queue.append((neighbor, depth + 1, 0))

                # Option 2:
                # Do special move to set up bomb.
                connections[depth][node].append(
                    node + nx_digraph.number_of_nodes())

                queue.append((node, depth + 1, 1))

            # Bomb is planted and is being set up. Game continues with
            # attacker staying at the same spot.
            elif wait > 0 and wait < self.time_bomb:
                connections[depth][node + nx_digraph.number_of_nodes() * wait].append(
                    node + nx_digraph.number_of_nodes() * (wait + 1))
                queue.append((node, depth + 1, wait+1))
            
            # Bomb already went off: nothing happens.
            elif wait == self.time_bomb:  
                connections[depth][node + nx_digraph.number_of_nodes() *
                                    wait].append(node + nx_digraph.number_of_nodes() * wait)
                queue.append((node, depth+1, wait))
            

        return connections

    def do_bfs_def(self,
                   nx_digraph: nx.MultiDiGraph,
                   start_nodes: list[int],
                   d_max: int):

        DEF_DUMMY_NODE_ID = 1

        # Initialize connections.
        connections = [[[1]], [[], []]] + [[[] for node_idx in range(
            nx_digraph.number_of_nodes() * (self.time_bomb + 1))] for layer_id in range(d_max)]

        # connect from pair of dummy nodes to starting vertics.
        connections[1][DEF_DUMMY_NODE_ID] = start_nodes.copy()

        visited = set()
        queue = [(start_node, 2) for start_node in start_nodes]

        while queue:
            node, depth = queue.pop(0)
            if (node, depth) in visited:
                continue
            visited.add((node, depth))
            
            if depth >= d_max + 1:
                continue

            neighbors = nx_digraph.neighbors(node)
            for neighbor in neighbors:
                connections[depth][node].append(neighbor)
                queue.append((neighbor, depth + 1))

        return connections

    def exact_edge_closeness(self, 
                     atk_connections, 
                     def_connections, 
                     num_vertices: int, 
                     time_bomb: int):
        assert len(atk_connections) == len(def_connections)
        num_layers = len(atk_connections)
        layer_sizes = [len(x) for x in atk_connections]
        # print(tuple(layer_sizes), tuple([len(x) for x in def_connections]))
        assert tuple(layer_sizes) == tuple([len(x) for x in def_connections])

        class ExactEdgeClosenessAtkPathFn(ClosenessFn):
            def __init__(self, adj_def: list[list[list[int]]]):
                self.num_layers = num_layers

                # Store all edges
                self.sto = [set() for i in range(num_layers)]
                for layer_id in range(num_layers):
                    for vertex_id in range(layer_sizes[layer_id]):
                        for neighbor in adj_def[layer_id][vertex_id]:
                            edge = (vertex_id, neighbor)
                            self.sto[layer_id].add(edge)
                super().__init__()

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.num_layers
                ret = [set() for i in range(self.num_layers)]
                for layer_id in range(2, self.num_layers-1):
                    edge = (path[layer_id], path[layer_id+1])
                    assert edge not in ret[layer_id]

                    # Compute for layers 2 onwards the vertex locations
                    # for every edge
                    duration_waited_so_far = path[layer_id] // num_vertices
                    node_id_start = path[layer_id] % num_vertices
                    node_id_end = path[layer_id+1] % num_vertices

                    # Adjacent edges from defender's perspective (ignoring 
                    # extra edges from bomb planting.)
                    basic_edge = (node_id_start, node_id_end)

                    if duration_waited_so_far < time_bomb:
                        if basic_edge in self.sto[layer_id]:
                            ret[layer_id].add(basic_edge)

                return ret

        class ExactEdgeClosenessDefPathFn(ClosenessFn):
            def __init__(self, adj_atk: list[list[list[int]]]):
                self.num_layers = num_layers
                self.sto = [set() for i in range(num_layers)]
                for layer_id in range(num_layers):
                    for vertex_id in range(layer_sizes[layer_id]):
                        for neighbor in adj_atk[layer_id][vertex_id]:
                            edge = (vertex_id, neighbor)
                            self.sto[layer_id].add(edge)
                super().__init__()

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.num_layers
                ret = [set() for i in range(self.num_layers)]
                for layer_id in range(2, self.num_layers-1):
                    edge = (path[layer_id], path[layer_id+1])
                    assert edge not in ret[layer_id]

                    if edge in self.sto[layer_id]:
                        ret[layer_id].add(edge)
                    if edge[0] == edge[1]:  # Loop may catch bomb setting
                        for t in range(time_bomb+1):
                            edge_ = (edge[0] + num_vertices * t,
                                     edge[0] + num_vertices * (t+1))
                            if edge_ in self.sto[layer_id]:
                                ret[layer_id].add(edge_)
                return ret

        # Functions for attacker first, followed by defender (so the adjacencies added are reversed)
        return ExactEdgeClosenessAtkPathFn(def_connections), ExactEdgeClosenessDefPathFn(atk_connections)

    def vertex_ending_closeness(self, 
                     atk_connections, 
                     def_connections, 
                     num_vertices: int, 
                     time_bomb: int):
        assert len(atk_connections) == len(def_connections)
        num_layers = len(atk_connections)
        layer_sizes = [len(x) for x in atk_connections]
        # print(tuple(layer_sizes), tuple([len(x) for x in def_connections]))
        assert tuple(layer_sizes) == tuple([len(x) for x in def_connections])

        class VertexEndingClosenessAtkPathFn(ClosenessFn):
            def __init__(self, adj_def: list[list[list[int]]]):
                self.num_layers = num_layers

                # Store all predecessor locations in `sto`.
                # sto[layer_id][vertex_id] gives all possible vertex_id' in layer_id - 1 
                # such that vertex_id' --> vertex_id is an edge.
                self.sto = [[set() for j in range(len(def_connections[i]))] for i in range(num_layers)]
                for start_layer_id in range(num_layers - 1):
                    for start_vertex_id in range(layer_sizes[start_layer_id]):
                        for neighbor in adj_def[start_layer_id][start_vertex_id]:
                            self.sto[start_layer_id+1][neighbor].add(start_vertex_id)
                super().__init__()

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.num_layers
                ret = [set() for i in range(self.num_layers)]
                for layer_id in range(1, self.num_layers-1): # We allow being caught at the very first non-dummy layer
                    edge = (path[layer_id], path[layer_id+1])
                    assert edge not in ret[layer_id]

                    # Compute for layers 2 onwards the vertex locations
                    # for every edge
                    if layer_id > 1:
                        duration_waited_so_far = path[layer_id] // num_vertices
                    else:
                        duration_waited_so_far = 0

                    node_id_end = path[layer_id+1] % num_vertices

                    # Adjacent edges from defender's perspective (ignoring 
                    # extra edges from bomb planting.)
                    for node_id_start in self.sto[layer_id+1][node_id_end]:
                        if duration_waited_so_far < time_bomb:
                            basic_edge = (node_id_start, node_id_end)
                            ret[layer_id].add(basic_edge)

                return ret

        class VertexEndingClosenessDefPathFn(ClosenessFn):
            def __init__(self, adj_atk: list[list[list[int]]]):
                self.num_layers = num_layers

                # Store all predecessor locations in `sto`.
                # sto[layer_id][vertex_id] gives all possible vertex_id' in layer_id - 1 
                # such that vertex_id' --> vertex_id is an edge.
                self.sto = [[set() for j in range(len(def_connections[i]))] for i in range(num_layers)]
                for start_layer_id in range(num_layers-1):
                    for start_vertex_id in range(layer_sizes[start_layer_id]):
                        for neighbor in adj_atk[start_layer_id][start_vertex_id]:
                            self.sto[start_layer_id+1][neighbor].add(start_vertex_id)
                super().__init__()

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.num_layers
                ret = [set() for i in range(self.num_layers)]
                for layer_id in range(1, self.num_layers-1): # Allow being caught at the first non-dummy layer.
                    basic_edge = (path[layer_id], path[layer_id+1])
                    node_id_end = basic_edge[1]

                    
                    for node_id_start in self.sto[layer_id+1][node_id_end]:
                        edge = (node_id_start, node_id_end)
                        # Catch while sharing the same ending vertex.
                        ret[layer_id].add(edge)

                    if layer_id > 1:
                        for t in range(1, time_bomb+1):
                            ending_expanded_id = basic_edge[1] + t * num_vertices
                            edge = (ending_expanded_id - num_vertices, ending_expanded_id)
                            if edge[0] in self.sto[layer_id+1][ending_expanded_id]:
                                ret[layer_id].add(edge)


                    """
                    for node_id_start in self.sto[layer_id+1][node_id_end]:
                        edge = (node_id_start, node_id_end)
                        # Catch while sharing the same ending vertex.
                        ret[layer_id].add(edge)

                        # Potentially catch which bomb is being set up.
                        for t in range(time_bomb):
                            edge_ = (edge[1] + num_vertices * t,
                                    edge[1] + num_vertices * (t+1))
                            if layer_id > 1 and edge_[0] in self.sto[layer_id][edge_[1]]:
                                ret[layer_id].add(edge_)
                    """
                return ret

        # Functions for attacker first, followed by defender (so the adjacencies added are reversed)
        return VertexEndingClosenessAtkPathFn(def_connections), VertexEndingClosenessDefPathFn(atk_connections)

    def expanded_target_vals(self, 
        raw_target_vals: list[float], 
        number_of_nodes: int, 
        time_bomb):
        """ Construct target values. Note that since we are duplicating locations (due to waiting time)
            we will have to return a list of size number_of_nodes * (time_bomb+1).
        """        
        # If bomb was not planted or planted for less than `time_bomb` time,
        # the payoff is 0 to the attacker.
        ret = [0.0] * (time_bomb * number_of_nodes)

        # Only when bomb was planted for `time_bomb` time will the attacker
        ret += raw_target_vals

        return ret

    def sanity_check(self, nx_graph: nx.MultiDiGraph):
        # Ensure that node labels are [0,...num_nodes)
        for i in nx_graph.nodes():
            assert i < nx_graph.number_of_nodes()
