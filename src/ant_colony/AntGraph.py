from math import sqrt
from math import pow
from threading import Lock

class AntGraph:
    def __init__(self, coord_mat, delta_mat=None, tau_mat=None):
        self.lock = Lock()
        self.build_nodes_mat(coord_mat)

        if tau_mat is None:
            self.build_tau_mat()
        else:
            self.tau_mat = tau_mat

    def build_nodes_mat(self, coord_mat):
        self.nodes_num = len(coord_mat)
        self.visited = [False] * self.nodes_num
        self.nodes_mat = [[0 for i in range(0, self.nodes_num)] for i in range(0, self.nodes_num)]
        for i in range(0, self.nodes_num):
            for j in range(i, self.nodes_num):
                d = sqrt(pow((coord_mat[i][0] - coord_mat[j][0]), 2) + pow((coord_mat[i][1] - coord_mat[j][1]), 2))
                self.nodes_mat[i][j], self.nodes_mat[j][i] = d, d

        # print nodes_mat
        for i in range(0, self.nodes_num):
            print(self.nodes_mat[i])

    def build_tau_mat(self):
        self.tau_mat = []
        for i in range(0, self.nodes_num):
            self.tau_mat.append([0] * self.nodes_num)

    def delta(self, r, s):
        return self.nodes_mat[r][s]

    def tau(self, r, s):
        return self.tau_mat[r][s]

    def etha(self, r, s):
        return 1.0 / self.delta(r, s)

    def update_tau(self, r, s, val):
        lock = Lock()
        lock.acquire()
        self.tau_mat[r][s] = val
        lock.release()



