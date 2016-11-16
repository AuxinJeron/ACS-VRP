from src.util import tspparser
from src.util import argparser

def main() :
    args = argparser.parse_args()
    print(args.tsp_file)
    tspparser.read_file(args.tsp_file[0])

    # print
    print("Name: " + tspparser.name)
    print ("Comment: " + tspparser.comment)
    print("Type: " + tspparser.type)
    print("Cities: ")
    for i in range(0, len(tspparser.cities_coord)):
        print("Node " + str(i) + " coordinate is " + str(tspparser.cities_coord[i][0]) + ", " + str(tspparser.cities_coord[i][1]))

    

if __name__ == "__main__" :
    main()