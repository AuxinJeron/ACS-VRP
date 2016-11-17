from .Ant import Ant
from threading import Lock, Condition

import random


class AntColony:
    def __init__(self, graph, num_ants, num_iterations):
        self.graph = graph
        self.num_ants = num_ants
        self.num_iterations =
        self.lock = Lock()

        # condition var
        self.cv = Condition()
        self.reset()

    def reset(self):
        self.ants = []
        self.iter_count = 0
        self.best_path_cost = float('inf')
        self.best_path_vec = None
        self.last_best_path_iteration = 0

    def start(self):
        self.reset()

        while self.iter_count < self.num_iterations:
            self.iteration()


    def end(self):
        return self.iter_count == self.num_iterations

    def create_ants(self):
        self.ants = []
        for i in range(0, self.num_ants):
            ant = Ant(i, random.randint(0, self.graph.num_nodes - 1), self)
            self.ants.append(ant)

    def iteration(self):
        self.avg_path_cost = 0
        self.ant_count = 0
        self.iter_count += 1
        print("======================================")
        print("iter_count = " + str(self.iter_count))
        for i in range(0, len(self.ants)):
            print("Ant {} started".format(i))
            self.ants[i].start()

    def update(self, ant):
        # TODO: there are may be problem of lock
        self.lock.acquire()

        self.ant_count += 1
        self.avg_path_cost += ant.path_cost

        if ant.path_cost < self.best_path_cost:
            self.best_path_cost = ant.path_cost
            self.best_path_vec = ant.path_vec
            self.last_best_path_iteration = self.iter_count

        if self.ant_count == len(self.ants):
            self.avg_path_cost /= len(self.ants)
            print("Best path found in iteration {} is {}, cost {}".format(self.iter_count, self.best_path_vec, self.best_path_vec))
            # notify update global
            with self.cv:
                self.cv.notify()

        self.lock.release()






