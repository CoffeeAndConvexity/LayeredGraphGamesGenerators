from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import itertools
import osmnx as ox

from random import randint, choice, seed as init_random


class World(object):
    def __init__(self, adj_list: list[list]):
        self.adj_list = adj_list

    def convert_to_networkx_graph(self):
        adj_list_as_dict = {k: v for k, v in enumerate(self.adj_list)}
        G = nx.MultiDiGraph(adj_list_as_dict)

        return G


class RandomGridWorld(World):
    def __init__(self, width: int, height: int, prob_drop: float = 0.0, directed=True, allow_stay=False, seed=None):
        """
        allow_stay: allow player to stay at the same spot?
        """
        self.width = width
        self.height = height
        self.directed = directed
        self.prob_drop = prob_drop
        self.allow_stay = allow_stay

        if directed == False:
            adj_list = self.generate_undirected(seed=seed)
        else:
            raise NotImplementedError()

        super().__init__(adj_list)

    def generate_directed(self):
        # TODO
        adj_grid = [np.ones(self.height, self.width) for i in range(4)]
        # grid[direction][y, x] tells us if an edge originating from vertex (y, x)
        # is poiting in direction (assuming it stays in bounds)
        # Directions are [UP, DOWN, LEFT, RIGHT]

        self.num_vertices = self.height * self.width
        self.adj_list = [[] for i in range(self.num_vertices)]

    def generate_undirected(self, seed):
        R = np.random.default_rng(seed)
        num_vertices = self.height * self.width
        adj_list = [[] for i in range(num_vertices)]
        for y in range(self.height):
            for x in range(self.width):
                if y < self.height - 1:
                    if R.choice([False, True], p=[self.prob_drop, 1-self.prob_drop]):
                        adj_list[self.scalar_idx(x, y)].append(
                            self.scalar_idx(x, y+1))
                    # if R.choice([False, True], p=[self.prob_drop, 1-self.prob_drop]):
                        adj_list[self.scalar_idx(
                            x, y+1)].append(self.scalar_idx(x, y))
                if x < self.width - 1:
                    if R.choice([False, True], p=[self.prob_drop, 1-self.prob_drop]):
                        adj_list[self.scalar_idx(x, y)].append(
                            self.scalar_idx(x+1, y))
                    # if R.choice([False, True], p=[self.prob_drop, 1-self.prob_drop]):
                        adj_list[self.scalar_idx(
                            x+1, y)].append(self.scalar_idx(x, y))
                if self.allow_stay:
                    # The "staying" edge is *always* allowed, will never be dropped
                    adj_list[self.scalar_idx(x, y)].append(
                        self.scalar_idx(x, y))

        return adj_list

    def scalar_idx(self, x, y):
        return y * self.width + x

    def draw_annotated_map(self, attacker_points = [], defender_points = []):
        f = plt.figure(figsize=(9, 7), dpi=120)
        nx_world = self.convert_to_networkx_graph()
        labels = {n:str(n) for n in nx_world.nodes()}
        node_color = ['tab:gray' for _ in range(len(nx_world.nodes()))]
        for n in attacker_points: node_color[n] = 'tab:red'
        for n in defender_points: node_color[n] = 'tab:blue'
        pos = {n : (n%self.width, int(n/self.width)) for n in nx_world.nodes()}
        nx.draw(nx_world, pos=pos, node_color=node_color, labels=labels, alpha=0.9, linewidths=1, node_size=250)
        plt.show()

class StreetMapWorld(World):
    def __init__(self,
                 place: str,
                 directed: bool = False,
                 allow_stay: bool = False,
                 osmnx_nx_type: str = 'drive',
                 consolidate_tolerance: float = 30,
                 normalizing_distance : float = 80,
                 edge_ndrop_property = lambda g,e : False):

        self.allow_stay = allow_stay
        self.edge_ndrop = edge_ndrop_property 

        self.osmnx_graph = ox.graph_from_place(place, network_type=osmnx_nx_type)
        self.osmnx_graph = ox.consolidate_intersections(ox.project_graph(
            self.osmnx_graph), tolerance=consolidate_tolerance)
        self.osmnx_graph = nx.relabel.convert_node_labels_to_integers(self.osmnx_graph, 
            first_label=0, ordering='default')

        
        self.uniform_graph = nx.DiGraph(list(set(self.osmnx_graph.edges())))
        self._normalize(normalizing_distance)

        if allow_stay:
            self._add_loops()

        if directed == False:
            adj_list = self.generate_undirected()
            self.uniform_graph = self.uniform_graph.to_undirected()
            self.osmnx_graph = ox.get_undirected(self.osmnx_graph)

        else:
            adj_list = self.generate_directed()

        super().__init__(adj_list)

    def convert_to_networkx_graph(self):
        return self.uniform_graph

    def get_underlying_osm(self):
        return self.osmnx_graph

    def generate_undirected(self):
        adj_list = [[i] if self.allow_stay else [] for i in range(self.uniform_graph.number_of_nodes())]
        for edge in self.uniform_graph.edges():
            adj_list[edge[0]].append(edge[1])
            adj_list[edge[1]].append(edge[0])
        adj_list = [list(set(l)) for l in adj_list]
        return adj_list

    def generate_directed(self):
        adj_list = [[i] if self.allow_stay else [] for i in range(self.uniform_graph.number_of_nodes())]
        for edge in self.uniform_graph.edges():
            adj_list[edge[0]].append(edge[1])
        adj_list = [list(set(l)) for l in adj_list]
        return adj_list

    def draw_map(self):
        ox.plot_graph(self.osmnx_graph)

    def draw_annotated_map(self, attacker_points = [], defender_points = []):
        fig, ax = ox.plot_graph(self.osmnx_graph, node_size=0, show=False, close=False,edge_color='black', bgcolor='white', node_color='black')
        for n_id, n_data in ox.graph_to_gdfs(self.osmnx_graph)[0].fillna('').iterrows():
            text = str(n_id)
            c = n_data['geometry'].centroid
            color = 'tab:red' if n_id in attacker_points else ('tab:blue' if n_id in defender_points else 'tab:gray')
            ax.annotate(text, (c.x, c.y), c=color,weight='bold')
            # print(text, (c.x, c.y), color)
        plt.show()
        plt.clf()
        plt.close()


    def _uniform2osm_path(self, paths):
        paths = [list(filter(lambda x: x < self.osmnx_graph.number_of_nodes(), path[2:])) for path in paths]
        paths = [[key for key, _group in itertools.groupby(path)] for path in paths]
        return paths

    def draw_player_paths(self, paths):
        paths = self._uniform2osm_path(paths)
        ox.plot_graph_routes(self.osmnx_graph, paths)

    def draw_paths(self, paths_atk, paths_def):
        paths_atk = [path for path in self._uniform2osm_path(paths_atk) if len(path) > 0]
        paths_def = [path for path in self._uniform2osm_path(paths_def) if len(path) > 0]
        paths = paths_atk + paths_def
        rc = ['r' for _ in range(len(paths_atk))] + \
            ['b' for _ in range(len(paths_def))]
        ox.plot_graph_routes(self.osmnx_graph, paths, route_colors=rc)

    def _normalize(self, unit_length):
        edges_to_delete = []
        edges_to_add = []
        points_to_add = []
        # TODO: check if osmnx is indexing nodes from 0 so starting with some large index is ok
        current_point = max(self.uniform_graph.nodes()) + 1
        for e in self.uniform_graph.edges():
            e_d = self.osmnx_graph.get_edge_data(e[0], e[1])
            if e_d[0]['length'] > 2 * unit_length:
                points = [v for v in ox.utils_geo.interpolate_points(
                    e_d[0]['geometry'], unit_length)]
                if len(points) > 0:
                    for i in range(len(points)):
                        points_to_add.append(current_point+i)
                    edges_to_add.append((e[0], current_point,))
                    for i in range(len(points)-1):
                        edges_to_add.append((current_point, current_point+1,))
                        current_point += 1
                    edges_to_add.append((current_point, e[1],))
                    if not self.edge_ndrop(self.osmnx_graph, e): edges_to_delete.append((e[0], e[1],))
                    current_point += 1
        for p in points_to_add:
            self.uniform_graph.add_node(p)
        self.uniform_graph.add_edges_from(edges_to_add)
        self.uniform_graph.remove_edges_from(edges_to_delete)

    def _add_loops(self):
        edges_to_add = []
        for node in self.uniform_graph.nodes():
            if node not in self.uniform_graph.neighbors(node):
                edges_to_add.append((node, node,))
        self.uniform_graph.add_edges_from(edges_to_add)


class ManualWorld(World):
    def __init__(self, adj_list: list[list[int]]):
        super() .__init__(adj_list)

