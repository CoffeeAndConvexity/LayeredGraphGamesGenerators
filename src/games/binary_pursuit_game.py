from __future__ import annotations 
from src.games.layered_game import LayeredGame, ClosenessFn
import networkx as nx
from collections import deque

class BinaryPursuitGame(LayeredGame):
    def __init__(self,
                 nx_graph_atk: nx.MultiDiGraph,
                 nx_graph_def: nx.MultiDiGraph,
                 source_atk: list[int],
                 source_def: list[int],
                 target_vals: list[float],
                 max_depth: int,
                 closeness_type: str):

        assert max_depth > 0
        self.sanity_check(nx_graph_atk)
        self.sanity_check(nx_graph_def)
        assert nx_graph_atk.number_of_nodes() == nx_graph_def.number_of_nodes()
        assert len(target_vals) == nx_graph_atk.number_of_nodes()

        # We introduce three dummy vertices over two layers.
        # First layer has a single source with index 0 (RESTRICTION BY DESIGN).
        # Second layer has two vertices (0 and 1), one for each player. Only one vertex
        # has outgoing edges, these lead to the possible starting nodes in the 3rd layer.
        # Third to last layer are max_depth number layers obtaned from unrolling.
        # The last layer has no outgoing vertices (RESTRICTION BY DESIGN).
        atk_connections = self.do_bfs(
            nx_graph_atk, source_atk, max_depth, 0)
        def_connections = self.do_bfs(
            nx_graph_def, source_def, max_depth, 1)
        target_vals = target_vals.copy()

        if closeness_type == 'exact_edge':
            adj_to_attacker_path = self.exact_edge_closeness(
                nx_graph_def, max_depth)  # Mapping for paths from ATTACKER
            adj_to_defender_path = self.exact_edge_closeness(
                nx_graph_atk, max_depth)  # Mapping for paths from DEFENDER
        elif closeness_type == 'share_dst_vertex':
            adj_to_attacker_path = self.vertex_ending_closeness(
                nx_graph_def, nx_graph_def.number_of_nodes()+1, source_def, max_depth)
            adj_to_defender_path = self.vertex_ending_closeness(
                nx_graph_atk, nx_graph_atk.number_of_nodes(), source_atk, max_depth)
        else:
            assert False, 'Closeness type not explicitly stated.'

        super().__init__(atk_connections, def_connections,
                         target_vals, adj_to_attacker_path, adj_to_defender_path)

    def do_bfs(self,
               nx_digraph: nx.MultiDiGraph,
               start_nodes: list[int],
               d_max: int,
               dummy_node_id: int):
        """ dummy_node_id: either number_of_nodes() or number_of_nodes() + 1
        """

        assert dummy_node_id == 0 or dummy_node_id == 1

        # Initialize connections.
        connections = [[[dummy_node_id]], [[], []]] + [[[] for node_idx in range(
            nx_digraph.number_of_nodes())] for layer_id in range(d_max)]

        # connect from pair of dummy nodes to starting vertics.
        connections[1][dummy_node_id] = start_nodes.copy()

        visited = set()
        queue = deque([(start_node, 2) for start_node in start_nodes])

        while queue:
            node, depth = queue.popleft()
            if (node, depth) in visited:
                continue
            visited.add((node, depth))

            if depth < d_max+2:
                neighbors = nx_digraph.neighbors(node)
                for neighbor in neighbors:
                    if depth < d_max + 1:
                        connections[depth][node].append(neighbor)
                    queue.append((neighbor, depth + 1))
                    # You can perform any additional processing here based on your requirements

        return connections

    ######### Closeness Functions #########
    def exact_edge_closeness(self, nx_graph_p2: nx.MultiDiGraph, max_depth: int):
        """ Get closeness function for matching exact edges.
        """
        class ExactEdgeClosenessFn(ClosenessFn):
            """
            `path` is assumed to be in the returned layered graph for p1
            returns a list of sets L where L[layer_id] is a set
            containing edges of the form (v_start, v_end) in p2's layered graph
            (for layer_id) which is shares exatly the edge in `path`.

            NOTE: we do not check if `path` is a valid one in the first place.
            However, we do make sure that the edges we return are indeed present
            in p2's graph.
            """

            def __init__(self, nx_graph_p2: nx.MultiDiGraph, max_depth: int):
                self.layered_max_depth = max_depth + 2
                self.nx_graph_p2 = nx_graph_p2

                super().__init__()

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.layered_max_depth

                ans = [set() for i in range(self.layered_max_depth)]
                for layer_id in range(2, self.layered_max_depth-1):
                    # Collisions for exact edge closness can only occur on layer 2 and beyond.
                    v_now, v_next = path[layer_id], path[layer_id+1]
                    # Dictionary over neighbors of v_now
                    if v_next in self.nx_graph_p2[v_now]:
                        ans[layer_id].add((v_now, v_next))

                return ans

        return ExactEdgeClosenessFn(nx_graph_p2, max_depth)

    def vertex_ending_closeness(self, nx_graph_p2: nx.MultiDiGraph, p2_dummy_id: int, p2_initial_states: list[int], max_depth: int):
        """ Returns a closeness_fn for paths using nx_graph_p1 and
            adjacent edges in nx_graph_p2.
        """

        class VertexEndingClosenessFn(ClosenessFn):
            """
            `path` is assumed to be in the returned layered graph for p1
            returns a list of sets L where L[layer_id] is a set
            containing edges of the form (v_start, v_end) in p2's layered graph
            (for layer_id) which are adjacent to some vertex in path p1's graph.

            NOTE: we do not check if `path` is a valid one in the first place.
            However, we do make sure that the edges we return are indeed present
            in p2's graph.
            """

            def __init__(self,
                         nx_graph_p2: nx.MultiDiGraph,
                         p2_dummy_id: int,
                         p2_initial_states: list[int],
                         max_depth: int):
                self.layered_max_depth = max_depth + 2
                self.nx_graph_p2 = nx_graph_p2
                self.initial_states = set(p2_initial_states)
                self.p2_dummy_id = p2_dummy_id

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.layered_max_depth

                ans = [set(), set()]
                for layer_id in range(2, self.layered_max_depth-1):
                    # Collisions for exact edge closness can only occur on layer 2 and beyond.
                    v_now, v_next = path[layer_id], path[layer_id+1]
                    # Dictionary over neighbors of v_now
                    for v_prev in self.nx_graph_p2.pred[v_next]:
                        ans[layer_id].add((v_prev, v_next))

                # Also make sure we test for them being initially in the same vertex
                # for v_prev in self.nx_graph_p2.pred[path[2]]:
                for v_init in self.initial_states:
                    ans[1].add((self.p2_dummy_id, v_init))

                return ans

        return VertexEndingClosenessFn(nx_graph_p2, p2_dummy_id, p2_initial_states, max_depth)

    def sanity_check(self, nx_graph: nx.MultiDiGraph):
        # Ensure that node labels are [0,...num_nodes)
        for i in nx_graph.nodes():
            assert i < nx_graph.number_of_nodes()
