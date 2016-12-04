from AntColony import AntColony
from AntGraph import AntGraph
from TspPainter import tspPainter
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
        antColony = AntColony(self.antGraph, self.lockers, self.lockers_dict, self.delivers, self.delivers_dict, self.demands, 10, 250)
        antColony.start()

        best_path_routes = antColony.best_path_routes
        best_path_cost = antColony.best_path_cost
        logger.info("-------------------------------------------")
        logger.info("Problem optimization result")
        logger.info("-------------------------------------------")
        if best_path_routes != None:
            logger.info("Best path routes found  is")
            for key in best_path_routes.keys():
                logger.info("Deliver {} {}".format(key, best_path_routes[key]))
            logger.info("Locker scheme is")
            for locker in self.lockers:
                logger.info("Locker {} scheme: {}".format(locker.id, self.locker_scheme(locker, best_path_routes)))
            logger.info("cost : {}".format(best_path_cost))
            tspPainter.drawRoutes(best_path_routes)
        else:
            logger.info("Failed to path routes")

        input("Press Enter to quit...")

    def locker_scheme(self, locker, path_routes):
        capacity = 0
        for deliver_id in locker.delivers:
            if deliver_id in path_routes.keys():
                path = path_routes[deliver_id]
                for pack in path:
                    capacity += pack.capacity
        capacity += self.demands[locker.pos]
        return capacity