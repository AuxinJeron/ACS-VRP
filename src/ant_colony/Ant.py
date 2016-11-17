from math import pow
from threading import *
import random
import operator


class Ant(Thread):
    def __init__(self, ID, start_node, colony):
        Thread.__init__(self)
        self.id = ID
        self.start_node = start_node
        self.colony = colony

        self.curr_node = self.start_node
        self.graph = self.colony.graph
        self.path_vec = []
        self.path_vec.append(self.start_node)
        self.path_cost = 0

        self.Beta = 1.0
        self.Q0 = 0.5
        self.Rho = 0.99

        self.nodes_to_visit = {}

        for i in range(0, self.graph.nodes_num):
            if i != self.start_node:
                self.nodes_to_visit[i] = i

        self.path_mat = []
        for i in range(0, self.graph.nodes_num):
            self.path_mat.append([0] * self.graph.nodes_num)

    def run(self):
        graph = self.colony.graph
        while not self.end():
            graph.lock.acquire()
            new_node = self.state_transition_rule(self.curr_node)
            self.path_cost += graph.delta(self.curr_node, new_node)

            self.path_vec.append(new_node)
            # current state of ant
            print('Ant {} : {}, {}'.format(str(self.id), self.path_vec, self.path_cost))
            self.local_updating_rule(self.curr_node, new_node)
            graph.lock.release()
        self.path_cost = graph.delta(self.path_vec[-1], self.path_vec[0])

        self.colony.update(self)

        # update global colony
        print('Ant {} terminated'.format(self.id))
        self.__init__(self.id, self.start_node, self.colony)

    def end(self):
        return not self.nodes_to_visit

    def state_transition_rule(self, curr_node):
        graph = self.colony.graph
        q = random.random()
        max_node = -1

        if q < self.Q0:
            print("Exploitation")
            max_val = -1
            val = None

            for node in self.nodes_to_visit.values():
                if graph.tau(curr_node, node) == 0:
                    raise Exception("tau = 0")

                val = graph.tau(curr_node, node) * pow(graph.etha(curr_node, node), self.Beta)
                if val > max_val:
                    max_val = val
                    max_node = node
        else:
            print("Exploration")
            sum = 0
            node = -1

            for node in self.nodes_to_visit.values():
                if graph.tau(curr_node, node) == 0:
                    raise Exception("tau = 0")
                sum += graph.tau(curr_node, node) * pow(graph.etha(curr_node, node), self.Beta)
            if sum == 0:
                raise Exception("sum = 0")

            avg = sum / len(self.nodes_to_visit)

            print("avg = " + str(avg))

            # random node selected according to the probability distribution
            # TODO check this method
            probability = {}
            pre_probability = 0
            r = random.random()
            for node in self.nodes_to_visit.values():
                probability[node] = graph.tau(curr_node, node) * pow(graph.etha(curr_node, node), self.Beta)
                pre_probability = pre_probability + probability[node]
                if pre_probability >= r:
                    max_node = node
                    break

            if max_node == -1:
                max_node = node

        if max_node < 0:
            raise Exception("max_node < 0")

        del self.nodes_to_visit[max_node]

        return max_node

    def local_updating_rule(self, curr_node, next_node):
        graph = self.colony.graph
        val = (1 - self.Rho) * graph.tau(curr_node, next_node) + (self.Rho * graph.tau0)
        graph.update_tau(curr_node, next_node, val)