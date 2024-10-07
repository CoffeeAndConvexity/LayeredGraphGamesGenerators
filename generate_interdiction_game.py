from __future__ import annotations

from src.games.starvation_game import StarvationGame
from src.worlds.world import RandomGridWorld, StreetMapWorld
from src.games.layered_game import LayeredGame
from src.util.layered_graph import find_all_paths_efficient

import numpy as np


def path_clash(game, p_atk, p_def):
    num_layers = len(game.atk_adj)
    interdicting_edges = game.closeness_fn_atk_path(p_atk)
    clash = False
    for L in range(num_layers-1):
        if (p_def[L], p_def[L+1],) in interdicting_edges[L]:
            clash = True
            break
    return clash

################################################
# Game depth, delay factor and randomization seed
################################################

depth = 5
delay_factor = 0.8
seed_num = 0

num_targets = 5

R = np.random.default_rng(seed_num)

################################################
# Construct grid worlds 
################################################
grid_size_x = 5
grid_size_y = 3
drop_prob = 0.1
atk_stay = True
def_stay = True

world_atk = RandomGridWorld(grid_size_x, grid_size_y, drop_prob, directed=False,
                            allow_stay=atk_stay, seed=seed_num)
world_def = RandomGridWorld(grid_size_x, grid_size_y, drop_prob, directed=False,
                            allow_stay=def_stay, seed=seed_num+100000)


################################################
# Download real-world map
################################################
# place = "Columbia University, USA"
# world_atk = StreetMapWorld(place, directed=False, allow_stay=True, consolidate_tolerance=10, normalizing_distance=1e6, osmnx_nx_type="all_private")
# world_def = world_atk


nx_graph_atk = world_atk.convert_to_networkx_graph()
nx_graph_def = world_def.convert_to_networkx_graph()


################################################
# Set up target values and starting points
################################################
is_target = [False] * nx_graph_atk.number_of_nodes()
targets = list(set([R.integers(low = 0, high=nx_graph_atk.number_of_nodes()) for _ in range(num_targets)]))
for t in targets: is_target[t] = True

delayed_payoffs = [1* (delay_factor**x) for x in range(depth)]
rescaled_delayed_payoffs = [y/max(delayed_payoffs)*10 for y in delayed_payoffs]


start_atk, start_def = [0], [nx_graph_def.number_of_nodes()-1]
world_atk.draw_annotated_map(attacker_points = start_atk)
world_def.draw_annotated_map(defender_points = start_def)




################################################
# Create the interdiction game
################################################
clg = StarvationGame(nx_graph_atk, nx_graph_atk, start_atk, start_def, is_target, depth, rescaled_delayed_payoffs, 'share_dst_vertex')

paths_maximizer = find_all_paths_efficient(clg.atk_adj)
paths_minimizer = find_all_paths_efficient(clg.def_adj)

num_paths_maximizer = len(paths_maximizer)
num_paths_minimizer = len(paths_minimizer)

print('Number of paths per player:', num_paths_maximizer, num_paths_minimizer)


################################################
# Construct the utility matrix
################################################

game_matrix = np.zeros((num_paths_minimizer, num_paths_maximizer))

for path_min_idx in range(num_paths_minimizer):
    for path_max_idx in range(num_paths_maximizer):
        game_matrix[path_min_idx][path_max_idx] = 0.0 if path_clash(clg,
                paths_maximizer[path_max_idx], paths_minimizer[path_min_idx]) else clg.target_vals[paths_maximizer[path_max_idx][-1]]



