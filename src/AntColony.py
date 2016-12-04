from Ant import Ant
from threading import Lock, Condition
from VRPModel import *

import random
import logging

logger = logging.getLogger("logger")

class AntColony:
    def __init__(self, graph, lockers, lockers_dict, delivers, delivers_dict, demands, num_ants, num_iterations):
        self.graph = graph
        self.lockers = lockers
        self.lockers_dict = lockers_dict
        self.delivers = delivers
        self.delivers_dict = delivers_dict
        self.demands = list(demands)
        self.ignore_locker_demand()
        self.num_ants = num_ants
        self.num_iterations = num_iterations
        self.Alpha = 0.1

        # condition var
        self.cv = Condition()
        self.create_ants()
        self.reset()

    def reset(self):
        self.iter_count = 0
        self.best_path_cost = float('inf')
        self.best_path_routes = None
        self.best_path_mat = None
        self.last_best_path_iteration = 0

    def start(self):
        self.reset()

        while self.iter_count < self.num_iterations:
            self.iteration()
            # wait until all ants finishing their jobs
            with self.cv:
                self.cv.wait_for(self.end)
                self.avg_path_cost /= len(self.ants)
                logger.info("=================Iteration {} finish=================".format(self.iter_count))
                logger.info("Best path routes in iteration {} is".format(self.iter_count))
                if self.best_path_routes != None:
                    for deliver in self.best_path_routes.keys():
                        logger.info("Deliver {} : {}".format(deliver, self.best_path_routes[deliver]))
                    for locker in self.lockers:
                        logger.info("Locker {} scheme: {}".format(locker.id, self.locker_scheme(locker, self.best_path_routes)))
                    logger.info("cost : {}".format(self.best_path_cost))
                    self.global_updating_rule()
                else:
                    logger.info("Failed to find path routes.")

        # kill all ants
        for ant in self.ants:
            ant.kill()

    def end(self):
        return self.finish_ant_count == len(self.ants)

    def ignore_locker_demand(self):
        for locker in self.lockers:
            self.demands[locker.pos] = 0

    def create_ants(self):
        self.ants = []
        for i in range(0, self.num_ants):
            #ant = Ant(i, random.randint(0, self.graph.nodes_num - 1), self)
            ant = Ant(i, self)
            self.ants.append(ant)
            ant.start()

    def iteration(self):
        self.avg_path_cost = 0
        self.finish_ant_count = 0
        self.iter_count += 1
        logger.debug("=================Iteration {} start=================".format(self.iter_count))
        for ant in self.ants:
            logger.debug("Ant {} started".format(ant.id))
            ant.begin_colony()

    def update(self, ant):
        with self.cv:
            self.finish_ant_count += 1
            self.avg_path_cost += ant.path_cost

            if ant.path_cost < self.best_path_cost:
                self.best_path_cost = ant.path_cost
                self.best_path_routes = ant.routes
                self.best_path_mat = ant.path_mat
                self.last_best_path_iteration = self.iter_count
                
            # release the lock
            self.cv.notify()

    def global_updating_rule(self):
        self.graph.lock.acquire()

        delta = 1.0 / self.best_path_cost

        # for i in range(0, len(self.best_path_mat)):
        #     logger.info(self.best_path_mat[i])

        for r in range(0, self.graph.nodes_num):
            for s in range(0, self.graph.nodes_num):
                if (r == s):
                    continue
                delta_rs = 0
                if self.best_path_mat[r][s] == 1:
                    delta_rs = delta
                evaporation = (1 - self.Alpha) * self.graph.tau(r, s)
                deposition = self.Alpha * delta_rs
                self.graph.update_tau(r, s, evaporation + deposition)

        self.graph.lock.release()

    def deliver_locker(self, deliver_id):
        deliver = self.delivers_dict[deliver_id]
        return self.deliver_locker(deliver)

    def deliver_locker(self, deliver):
        return self.lockers_dict[deliver.locker_id]

    def locker_scheme(self, locker, path_routes):
        capacity = 0
        for deliver_id in locker.delivers:
            if deliver_id in path_routes.keys():
                path = path_routes[deliver_id]
                for pack in path:
                    capacity += pack.capacity
        return capacity