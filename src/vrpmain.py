from src.util import tspparser
from src.util import argparser
from src.ant_colony.AntGraph import AntGraph
from src.ant_colony.AntColony import AntColony
import logging

# construct the logger
logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)s] [%(levelname)s]  %(message)s")
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

def run_ant_colony(nodes_coord):
    antGraph = AntGraph(nodes_coord)
    antColony = AntColony(antGraph, 28, 250)
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

def main():
    args = argparser.parse_args()
    tspparser.read_file(args.tsp_file[0])

    logger.info("-------------------------------------------")
    logger.info("Problem formulation information")
    logger.info("-------------------------------------------")
    logger.info("Name: " + tspparser.name)
    logger.info("Comment: " + tspparser.comment)
    logger.info("Type: " + tspparser.type)
    logger.info("Cities: ")
    for i in range(1, len(tspparser.cities_coord)):
        logger.info("Node " + str(i) + " coordinate is " + str(tspparser.cities_coord[i][0]) + ", " + str(tspparser.cities_coord[i][1]))

    run_ant_colony(tspparser.cities_coord[1:])

if __name__ == "__main__":
    main()