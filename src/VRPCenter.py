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
        self.delivers = tspparser.delivers
        self.demands = tspparser.demands

    def start(self):
        antColony = AntColony(self.antGraph, self.lockers, self.delivers, self.demands, 1, 250)
        antColony.start()

        best_path_routes = antColony.best_path_routes
        best_path_cost = antColony.best_path_cost
        logger.info("-------------------------------------------")
        logger.info("Problem optimization result")
        logger.info("-------------------------------------------")
        logger.info("Best path found  is")
        for key in best_path_routes.keys():
            logger.info("Deliver {} {}".format(key, best_path_routes[key]))
        logger.info("cost : {}".format(best_path_cost))