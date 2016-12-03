from AntColony import AntColony
from AntGraph import AntGraph
from VRPModel import *
import logging

logger = logging.getLogger("logger")


class VRPCenter:
    def __init__(self, tspparser):
        self.build_graph(tspparser)

    def build_graph(self, tspparser):
        self.antGraph = AntGraph(tspparser.cities_coord)
        self.lockers = tspparser.lockers
        self.lockers_dict = {}
        self.delivers_dict = {}
        for locker in self.lockers:
            self.lockers_dict[locker.id] = locker
        self.delivers = tspparser.delivers
        for deliver in self.delivers:
            self.delivers_dict[deliver.id] = deliver
        self.demands = tspparser.demands

        self.build_nearest_locker()

    def build_nearest_locker(self):
        for deliver in self.delivers:
            deliver.locker_id = deliver.nearest_locker(self.lockers, self.antGraph.nodes_mat)
            locker = self.lockers_dict[deliver.locker_id]
            locker.delivers.append(deliver.id)

    def start(self):
        antColony = AntColony(self.antGraph, self.lockers, self.delivers, self.demands, 10, 250)
        antColony.start()

        best_path_routes = antColony.best_path_routes
        best_path_cost = antColony.best_path_cost
        logger.info("-------------------------------------------")
        logger.info("Problem optimization result")
        logger.info("-------------------------------------------")
        logger.info("Best path routes found  is")
        if best_path_routes != None:
            for key in best_path_routes.keys():
                logger.info("Deliver {} {}".format(key, best_path_routes[key]))
            logger.info("cost : {}".format(best_path_cost))
        else:
            logger.info("Failed to path routes")