from __future__ import annotations 
from abc import ABC, abstractmethod
import itertools
import networkx as nx

class ClosenessFn(ABC):
    def __init__(self):
        # TODO:
        pass

    @abstractmethod
    def __call__(self, path: list[int]) -> list[set[int, int]]:
        pass



class LayeredGame(object):
    def __init__(self,
                 atk_adj: list[list[list[int]]],
                 def_adj: list[list[list[int]]],
                 target_vals: list[float],
                 closeness_fn_atk_path: ClosenessFn,
                 closeness_fn_def_path: ClosenessFn):
        """
        TODO: closeness_fn. For each edge, what are the other edges that are adjacent to it
        for the purposes of being caught?
        """
        self.atk_adj = atk_adj
        self.def_adj = def_adj
        self.target_vals = target_vals

        # TODO: allow stochasticity.
        # Check restrictions
        # A) Only one source vertex.
        assert len(atk_adj[0]
                   ) == 1, 'Layered graph only allows for single source!'
        assert len(def_adj[0]
                   ) == 1, 'Layered graph only allows for single source!'
        # B) Last layers must have no succeeding vertices
        assert sum([len(z) for z in atk_adj[-1]]
                   ) == 0, 'Last layer must have no successors'
        assert sum([len(z) for z in def_adj[-1]]
                   ) == 0, 'Last layer must have no successors'
        # C) Target vals must be equal to the number of vertices
        # in the last layer of the attacker layered graph (atk_adj)
        assert len(target_vals) == len(atk_adj[-1])

        self.closeness_fn_atk_path = closeness_fn_atk_path
        self.closeness_fn_def_path = closeness_fn_def_path

    ###################################
    #  Default closeness functions (use if convenient)
    #  These are defined on the layered graph directly.
    ###################################
    def MakeExactEdgeClosenessFn(nonpath_player_adj: list[list[list[int]]]):
        num_layers = len(nonpath_player_adj)
        layer_sizes = [len(x) for x in nonpath_player_adj]

        class ExactEdgeClosenessFn(ClosenessFn):
            def __init__(self, adj2: list[list[list[int]]]):
                self.num_layers = num_layers
                self.sto = [set() for i in range(num_layers)]
                for layer_id in range(num_layers):
                    for vertex_id in range(layer_sizes[layer_id]):
                        for neighbor in adj2[layer_id][vertex_id]:
                            edge = (vertex_id, neighbor)
                            self.sto[layer_id].add(edge)
                super().__init__()

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.num_layers
                ret = [set() for i in range(self.num_layers)]
                for layer_id in range(self.num_layers-1):
                    edge = (path[layer_id], path[layer_id+1])
                    assert edge not in ret[layer_id]
                    if edge in self.sto[layer_id]:
                        ret[layer_id].add(edge)
                return ret

        # Functions for attacker first, followed by defender (so the adjacencies added are reversed)
        return ExactEdgeClosenessFn(nonpath_player_adj)

    def MakeExactVertexClosenessFn(nonpath_player_adj: list[list[list[int]]]):
        num_layers = len(nonpath_player_adj)
        layer_sizes = [len(x) for x in nonpath_player_adj]

        class ExactVertexClosenessFn(ClosenessFn):
            def __init__(self, adj2: list[list[list[int]]]):
                self.num_layers = num_layers

                # Precompute parents
                self.parents = [[[] for i in range(layer_sizes[layer_id])]
                                for layer_id in range(num_layers)]  # Could possibly change to a set() in the middle if it helps.
                for layer_id in range(num_layers-1):
                    for vertex_id in range(layer_sizes[layer_id]):
                        for next_vertex_id in adj2[layer_id][vertex_id]:
                            self.parents[layer_id +
                                         1][next_vertex_id].append(vertex_id)

            def __call__(self, path: list[int]) -> list[set[int, int]]:
                assert len(path) == self.num_layers
                ret = [set() for i in range(self.num_layers)]

                for layer_id in range(self.num_layers-1):
                    dst = path[layer_id+1]
                    for parent_id in self.parents[layer_id+1][dst]:
                        ret[layer_id].add((parent_id, dst))

                return ret

        return ExactVertexClosenessFn(nonpath_player_adj)

    def num_layers(self):
        if len(self.atk_adj) != len(self.def_adj):
            assert 'Called LayeredGame.num_layers() when number of layers for atk and def are different'
        return len(self.atk_adj)

################################################
# Utility functions
################################################


def vis_layers(connectivity):
    layer_sizes = [len(z) for z in connectivity]
    extents = nx.utils.pairwise(
        itertools.accumulate((0,) + tuple(layer_sizes)))

    vertex_ids_by_layer = [list(range(start, end)) for start, end in extents]

    G = nx.DiGraph()
    for layer_idx, global_indices in enumerate(vertex_ids_by_layer):
        G.add_nodes_from(global_indices, layer=layer_idx)

    layer_idx = 0
    for layer1, layer2 in nx.utils.pairwise(vertex_ids_by_layer):
        edges_this_layer = []
        for local_vertex_idx, edge_list in enumerate(connectivity[layer_idx]):
            start_global_vertex = layer1[local_vertex_idx]
            for end_local_vertex_idx in edge_list:
                end_global_vertex = layer2[end_local_vertex_idx]
                edges_this_layer.append(
                    (start_global_vertex, end_global_vertex))

        G.add_edges_from(edges_this_layer)
        layer_idx += 1

    return G

