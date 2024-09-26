import networkx as nx
import itertools

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