from AntColony import AntColony
from AntGraph import AntGraph
from TsplibParser import parser as tspparser
from VRPModel import *
import logging

logger = logging.getLogger("logger")


class VRPCenter:
    def __init__(self, tspparser):
        self.build_ant_colony(tspparser)

    def build_ant_colony(self, tspparser):
        self.antGraph = AntGraph(tspparser.cities_coord)

    def start(self):
        antColony = AntColony(self.antGraph, 28, 250)
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