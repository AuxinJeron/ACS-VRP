from collections import deque
from os import path

KEYWORDS = {'NAME', 'COMMENT', 'TYPE', 'DIMENSION', 'EDGE_WEIGHT_TYPE', 'CAPACITY', 'NODE_COORD_SECTION', 'DEMAND_SECTION', 'DEPOT_SECTION'}

class TsplibParser :
    def __init__(self) :
        self.file_path = ""
        # attribute for the tsp file
        self.name = ""
        self.comment = ""
        self.type = ""
        self.dimension = 0
        self.edge_weight_type = ""
        self.capacity = 10
        self.cities_coord = []

    def reset(self) :
        self.__init__()

    def scan_keywords(self, file) :
        # mark whether enter NODE_COORD_SECTION
        node_coord_section = False

        for line in file :
            words = deque(line.split())
            keyword = words.popleft().strip(": ")

            # meet next keyword, exit from node_coord_section
            if node_coord_section and keyword in KEYWORDS :
                node_coord_section = False

            if keyword == "COMMENT":
                self.comment = " ".join(words).strip(": ")
            elif keyword == "NAME":
                self.name = " ".join(words).strip(": ")
            elif keyword == "TYPE":
                self.type = " ".join(words).strip(": ")
            elif keyword == "DIMENSION":
                self.dimension = int(" ".join(words).strip(": "))
                self.cities_coord = [[0, 0]] * (self.dimension + 1)
            elif keyword == "EDGE_WEIGHT_TYPE" :
                self.edge_weight_type = " ".join(words).strip(": ")
            elif keyword == "CAPACITY":
                self.capacity = int(" ".join(words).strip(": "))
            elif keyword == "NODE_COORD_SECTION":
                node_coord_section = True
            else :
                if node_coord_section:
                    self.scan_city_coord(line)

    def scan_city_coord(self, line):
        words = deque(line.split(" "))
        if len(words) != 3 :
            return
        index = int(words[0])
        if index >= len(self.cities_coord):
            return
        self.cities_coord[index] = [int(words[1]), int(words[2])]

    def read_file(self, file_path):
        self.file_path = path.relpath(file_path)
        file = open(file_path, 'r')
        self.scan_keywords(file)

parser = TsplibParser()