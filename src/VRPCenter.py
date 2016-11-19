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
        antColony = AntColony(self.antGraph, self.lockers, self.delivers, self.demands, 10, 250)
        antColony.start()

        best_path_vec = antColony.best_path_vec
        best_path_cost = antColony.best_path_cost
        for i in range(0, len(best_path_vec)):
            if best_path_vec[i] == 0:
                best_path_vec = antColony.best_path_vec[i:]
                best_path_vec += antColony.best_path_vec[0:i]
                break
        logger.info("-------------------------------------------")
        logger.info("Problem optimization result")
        logger.info("-------------------------------------------")
        logger.info("Best path found  is")
        logger.info("{}".format(best_path_vec))
        logger.info("cost : {}".format(best_path_cost))