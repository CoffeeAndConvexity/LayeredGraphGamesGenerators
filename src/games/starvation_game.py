from __future__ import annotations

from numpy import number 
from src.games.layered_game import LayeredGame, ClosenessFn
import networkx as nx
from collections import deque

class StarvationGame(LayeredGame):
    """ 
    Vertex ID scheme
    ================
    Defender: Same as the usual pursuit evasion game, first two layers are 
              dummy layers, following layers are obtained by unrolling.
    Attacker: We unroll the graph, but introduce max_depth+1 extra 'terminal vertices',
              each of which is tells us how long it took to reach a terminal vertex.

              Let M be the number of vertices in nx_graph_atk (the world graph)
              The first M vertices (i.e., {0, 1, ... M=1}) vertices of each layer 
              corresspond to them. The vertices in {M, M+1, ... M+max_depth-1} are
              terminal vertices for time = {1, , ... max_depth} time that was played
              before reaching the target. Note that the value for depth = 0 
              is required. 
              
              Delayed utilities is typically something like [1, x, x^2 ...x^depth] for 
              some 0 <= x <= 1.
    """
    def __init__(self,
                 nx_graph_atk: nx.MultiDiGraph,
                 nx_graph_def: nx.MultiDiGraph,
                 source_atk: list[int],
                 source_def: list[int],
                 is_target_list: list[bool], # True if is a target, false if not.
                 max_depth: int,
                 delayed_utilities: list[float], # <= 1.0 for each timestep. 1-x gives the proportion of people who starved before aid arrived.
                 closeness_type: str):

        assert max_depth > 0
        assert len(delayed_utilities) == max_depth
        self.sanity_check(nx_graph_atk)
        self.sanity_check(nx_graph_def)
        assert nx_graph_atk.number_of_nodes() == nx_graph_def.number_of_nodes()
        assert len(is_target_list) == nx_graph_atk.number_of_nodes()
        self.delayed_utilities = delayed_utilities.copy()
        self.is_target_list = is_target_list.copy()

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

        if closeness_type == 'exact_edge':
            closeness_fn_atk_path, closeness_fn_def_path = self.exact_edge_closeness(
                atk_connections, def_connections)

        elif closeness_type == 'share_dst_vertex':
            closeness_fn_atk_path, closeness_fn_def_path = self.vertex_ending_closeness(
                atk_connections, def_connections)

        expanded_target_vals = self.expanded_target_vals(is_target_list, nx_graph_atk.number_of_nodes(), delayed_utilities)

        super().__init__(atk_connections, def_connections, expanded_target_vals,
                         closeness_fn_atk_path, closeness_fn_def_path)

    def do_bfs_atk(self,
                   nx_digraph: nx.MultiDiGraph,
                   start_nodes: list[int],
                   d_max: int):

        ATK_DUMMY_NODE_ID = 0

        # Initialize connections in first two layers.
        connections = [[[0]], [[], []]] + [[[] for node_idx in range(
            nx_digraph.number_of_nodes() + d_max - 1)] for layer_id in range(d_max)]

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

            if node is not None:
                assert node < nx_digraph.number_of_nodes()
                # Option 1:
                # Do *normal* move to neighbor (could be self if nx_digraph has loops)
                # May only be done if node is not terminal
                if not self.is_target_list[node]:
                    neighbors = nx_digraph.neighbors(node)
                    for neighbor in neighbors:
                        if depth < d_max + 1:
                            connections[depth][node].append(neighbor)
                        queue.append((neighbor, depth + 1, 0))

                # Option 2:
                # Dummy move that may only be used at a terminal state
                else: 
                    connections[depth][node].append(nx_digraph.number_of_nodes())
                    queue.append((None, depth + 1, 1))

            # We have already reached terminal state and are just waiting things out.
            elif node is None:
                connections[depth][nx_digraph.number_of_nodes() + wait - 1].append(
                    nx_digraph.number_of_nodes() + wait)
                queue.append((None, depth + 1, wait + 1))

        return connections

    def do_bfs_def(self,
                   nx_digraph: nx.MultiDiGraph,
                   start_nodes: list[int],
                   d_max: int):

        DEF_DUMMY_NODE_ID = 1

        # Initialize connections.
        connections = [[[1]], [[], []]] + [[[] for node_idx in range(
            nx_digraph.number_of_nodes() + d_max - 1)] for layer_id in range(d_max)]

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
                     def_connections):
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

                    # Redundant
                    # if edge[1] >= num_vertices:
                    #     continue

                    if edge in self.sto[layer_id]:
                        ret[layer_id].add(edge)

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
                return ret

        # Functions for attacker first, followed by defender (so the adjacencies added are reversed)
        return ExactEdgeClosenessAtkPathFn(def_connections), ExactEdgeClosenessDefPathFn(atk_connections)

    def vertex_ending_closeness(self, 
                     atk_connections, 
                     def_connections):
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
                self.sto = [[set() for j in range(len(atk_connections[i]))] for i in range(num_layers)]
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

                    # Redundant.
                    # if edge[1] >= num_vertices:
                    #     continue

                    for node_id_start in self.sto[layer_id+1][edge[1]]:
                        ret[layer_id].add((node_id_start, edge[1]))

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
                    edge = (path[layer_id], path[layer_id+1])

                    for node_id_start in self.sto[layer_id+1][edge[1]]:
                        ret[layer_id].add((node_id_start, edge[1]))

                return ret

        # Functions for attacker first, followed by defender (so the adjacencies added are reversed)
        return VertexEndingClosenessAtkPathFn(def_connections), VertexEndingClosenessDefPathFn(atk_connections)

    def expanded_target_vals(self, 
        is_target_list: list[bool], 
        number_of_nodes: int,
        delayed_utilities: list[float]):
        """ Construct target values in the sense of the layered graph.
        """        
        
        # First num_of_nodes vertices are the usual vertices. 1 if target, 
        # 0 otherwise.
        ret_final_vertices = [delayed_utilities[-1] if is_target_list[x] else 0.0 for x in range(number_of_nodes)]
        # Terminal vertices
        ret_extra_terminal_vertices = list(reversed(delayed_utilities[:-1]))

        ret = ret_final_vertices + ret_extra_terminal_vertices
        return ret

    def sanity_check(self, nx_graph: nx.MultiDiGraph):
        # Ensure that node labels are [0,...num_nodes)
        for i in nx_graph.nodes():
            assert i < nx_graph.number_of_nodes()

