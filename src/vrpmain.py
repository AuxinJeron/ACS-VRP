from src.util import tspparser
from src.util import argparser
from src.ant_colony.AntGraph import AntGraph
from src.ant_colony.AntColony import AntColony


def run_ant_colony(nodes_coord):
    antGraph = AntGraph(nodes_coord)
    antColony = AntColony(antGraph, 10, 10)
    antColony.start()

def main():
    args = argparser.parse_args()
    print(args.tsp_file)
    tspparser.read_file(args.tsp_file[0])

    print("-------------------------------------------")
    print("Problem formulation information")
    print("-------------------------------------------")
    print("Name: " + tspparser.name)
    print ("Comment: " + tspparser.comment)
    print("Type: " + tspparser.type)
    print("Cities: ")
    for i in range(1, len(tspparser.cities_coord)):
        print("Node " + str(i) + " coordinate is " + str(tspparser.cities_coord[i][0]) + ", " + str(tspparser.cities_coord[i][1]))

    run_ant_colony(tspparser.cities_coord[1:])

if __name__ == "__main__":
    main()