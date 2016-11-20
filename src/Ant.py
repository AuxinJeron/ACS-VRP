from math import pow
from threading import *
from VRPModel import Package
import random
import logging

logger = logging.getLogger("logger")

class Ant(Thread):
    def __init__(self, ID, colony):
        Thread.__init__(self)
        self.cv = Condition()
        self.id = ID
        self.colony = colony
        self.dead = False
        self.working = False

        self.Beta = 2.0
        self.Q0 = random.randint(45, 98) / 100.0
        self.Rho = 0.1

    def reset(self):
        self.graph = self.colony.graph
        self.delivers = set(self.colony.delivers)
        # TODO: the demand per node may be larger than the capacity of each deliver
        self.demands = list(self.colony.demands)

        self.routes = {}
        self.routes_cost = {}
        self.routes_capacity = {}
        self.path_cost = 0
        self.path_mat = [[0 for i in range(0, self.graph.nodes_num)] for i in range(0, self.graph.nodes_num)]
        self.nodes_to_visit = set()
        for i in range(0, self.graph.nodes_num):
            self.nodes_to_visit.add(i)

        self.curr_deliver = None
        self.curr_node = None
        self.curr_path_vec = []
        self.curr_path_cost = 0
        self.curr_path_capacity = 0

    def kill(self):
        self.dead = True
        with self.cv:
            self.working = True
            self.cv.notify()

    def run(self):
        while not self.dead:
            with self.cv:
                self.reset()
                self.cv.wait_for(self.should_work)
                self.run_iteration()
                self.working = False

    def begin_colony(self):
        if self.dead:
            return
        with self.cv:
            self.working = True
            self.cv.notify()

    def should_work(self):
        return self.working

    def run_iteration(self):
        graph = self.colony.graph
        self.find_deliver()
        while not self.end():
            graph.lock.acquire()
            new_node = self.state_transition_rule(self.curr_node)
            if self.check_feasibilty(new_node):
                self.insert_node(new_node)
                self.curr_node = new_node
            else:
                self.find_deliver()
            graph.lock.release()
        # don't forget the last route
        graph.lock.acquire()
        self.find_deliver()
        graph.lock.release()

        # local search update
        # use 2-opt heuristic
        for key in self.routes.keys():
            self.routes[key] = self.opt_heuristic(self.routes[key])

        self.update_optimum_routes()

        self.colony.update(self)

        # update global colony
        logger.debug('===========Ant {} terminated==========='.format(self.id))

    def end(self):
        return not self.nodes_to_visit

    def state_transition_rule(self, curr_node):
        graph = self.colony.graph
        q = random.random()
        max_node = -1

        # search in the candidate list first
        candidates_nodes = self.graph.cand_list[curr_node].intersection(self.nodes_to_visit)
        if not candidates_nodes:
            candidates_nodes = self.nodes_to_visit

        # logger.debug("{} Candidates node : {}".format(curr_node, candidates_nodes))
        # for i in range(0, len(self.demands)):
        #     logger.debug("Demands {} : {}".format(i, self.demands[i]))

        if q < self.Q0:
            logger.debug("Exploitation")
            max_val = -1
            val = None

            for node in candidates_nodes:
                if graph.tau(curr_node, node) == 0:
                    raise Exception("tau = 0")

                val = graph.tau(curr_node, node) * pow(graph.etha(curr_node, node), self.Beta)
                if val > max_val:
                    max_val = val
                    max_node = node
        else:
            logger.debug("Exploration")
            sum = 0
            node = -1

            for node in candidates_nodes:
                if graph.tau(curr_node, node) == 0:
                    raise Exception("tau = 0")
                sum += graph.tau(curr_node, node) * pow(graph.etha(curr_node, node), self.Beta)
            if sum == 0:
                raise Exception("sum = 0")

            avg = sum / len(candidates_nodes)

            #print("avg = " + str(avg))

            # random node selected according to the probability distribution
            # TODO check this method
            probability = {}
            pre_probability = 0
            r = random.random()
            #logger.info("r " + str(r))
            for node in candidates_nodes:
                probability[node] = graph.tau(curr_node, node) * pow(graph.etha(curr_node, node), self.Beta) / sum
                pre_probability = pre_probability + probability[node]
                #logger.info("p " + str(pre_probability))
                if pre_probability >= r:
                    max_node = node
                    break

            if max_node == -1:
                max_node = node

        if max_node < 0:
            raise Exception("max_node < 0")
        return max_node

    def check_feasibilty(self, next_node):
        distance = self.graph.delta(self.curr_path_vec[-1].pos, next_node) + self.graph.delta(next_node, self.curr_path_vec[0].pos)
        if self.curr_path_cost + distance > self.curr_deliver.max_distance:
            return False
        next_capacity = self.curr_path_capacity + self.demands[next_node]
        # if the capacity exceeds the max capacity of the deliver return false
        # expects that the demand in that node is larger than the origin max capacity of the deliver
        if next_capacity > self.curr_deliver.max_capacity and self.demands[next_node] <= self.curr_deliver.max_capacity:
            return False
        return True

    def insert_node(self, new_node):
        graph = self.graph

        consume_demand = min(self.curr_deliver.max_capacity - self.curr_path_capacity, self.demands[new_node])
        self.demands[new_node] -= consume_demand
        if self.demands[new_node] == 0:
            self.nodes_to_visit.remove(new_node)

        self.curr_path_cost += graph.delta(self.curr_node, new_node)
        self.curr_path_capacity += consume_demand
        self.curr_path_vec.append(Package(new_node, consume_demand))
        self.path_mat[self.curr_node][new_node] = 1
        # current state of ant
        logger.debug('[Insert]Ant {} : {}'.format(str(self.id), self.curr_path_vec))
        logger.debug('[Insert]cost : {}'.format(self.curr_path_cost))
        logger.debug('[Insertion]capacity : {}'.format(self.curr_path_capacity))
        self.local_updating_rule(self.curr_node, new_node)
        self.curr_node = new_node

    def find_deliver(self):
        graph = self.graph
        # add new route
        if self.curr_path_vec:
            self.local_updating_rule(self.curr_path_vec[-1].pos, self.curr_path_vec[0].pos)
            self.curr_path_cost += graph.delta(self.curr_path_vec[-1].pos, self.curr_path_vec[0].pos)
            self.routes[self.curr_deliver.id] = self.curr_path_vec
            self.routes_cost[self.curr_deliver.id] = self.curr_path_cost
            self.routes_capacity[self.curr_deliver.id] = self.curr_path_capacity
            self.path_cost += self.curr_path_cost

        self.curr_path_vec = []
        self.curr_path_cost = 0
        self.curr_path_capacity = 0

        if self.end():
            return

        # find next deliver
        self.curr_deliver = self.delivers.pop()
        self.curr_node = self.curr_deliver.pos
        self.curr_path_vec = []
        self.curr_path_cost = 0
        consume_demand = min(self.curr_deliver.max_capacity, self.demands[self.curr_node])
        self.demands[self.curr_node] -= consume_demand
        self.curr_path_vec.append(Package(self.curr_node, consume_demand))
        self.curr_path_capacity += consume_demand
        if self.demands[self.curr_node] == 0 and self.curr_node in self.nodes_to_visit:
            self.nodes_to_visit.remove(self.curr_node)

        logger.debug('[Find deliver]Ant {} : {}'.format(str(self.id), self.curr_deliver))
        #logger.debug('[Find deliver]Ant {} Demands'.format(self.id))
        # for i in range(0, len(self.demands)):
        #     logger.debug("Demands {} : {}".format(i, self.demands[i]))

    def update_optimum_routes(self):
        self.path_cost = 0
        self.path_mat = [[0 for i in range(0, self.graph.nodes_num)] for i in range(0, self.graph.nodes_num)]

        for deliver in self.routes.keys():
            cost, capacity = self.update_optimum_path(self.routes[deliver])
            self.routes_capacity[deliver] = capacity
            self.routes_cost[deliver] = cost
            self.path_cost += cost
            logger.debug("Ant {} Deliver {} : {}".format(self.id, deliver, self.routes[deliver]))
            logger.debug("cost : {}, capacity : {}".format(cost, capacity))

    def update_optimum_path(self, path_vec):
        cost = 0
        capacity = 0
        nodes_mat = self.graph.nodes_mat
        for i in range(0, len(path_vec) - 1):
            cost += nodes_mat[path_vec[i].pos][path_vec[i + 1].pos]
            self.path_mat[path_vec[i].pos][path_vec[i + 1].pos] = 1
            capacity += path_vec[i].capacity
        cost += nodes_mat[path_vec[-1].pos][path_vec[0].pos]
        self.path_mat[path_vec[-1].pos][path_vec[0].pos] = 1
        capacity += path_vec[-1].capacity
        return cost, capacity

    def tour_length(self, path_vec):
        nodes_mat = self.graph.nodes_mat
        sum = 0
        for i in range(0, len(path_vec) - 1):
            sum += nodes_mat[path_vec[i].pos][path_vec[i + 1].pos]
        sum += nodes_mat[path_vec[-1].pos][path_vec[0].pos]
        return sum

    # 2-opt heuristic
    def opt_heuristic(self, path_vec):
        graph = self.graph
        l = len(path_vec)
        noChange = False
        while not noChange:
            noChange = True
            for i in range(0, l - 1):
                diff = 0
                diff_j = i
                for j in range(i + 1, l):
                    ori_val = graph.delta(path_vec[i].pos, path_vec[i + 1].pos) + graph.delta(path_vec[j].pos, path_vec[(j + 1) % l].pos)
                    new_val = graph.delta(path_vec[i].pos, path_vec[j].pos) + graph.delta(path_vec[i + 1].pos, path_vec[(j + 1) % l].pos)
                    if new_val - ori_val < diff:
                        diff = new_val - ori_val
                        diff_j = j
                j = diff_j
                if j != i:
                    new_path_vec = path_vec[0:i + 1]
                    new_path_vec += path_vec[j:i:-1]
                    new_path_vec += path_vec[j + 1:l]
                    path_vec = new_path_vec
                    noChange = False
        # TODO: check the path mat
        return path_vec

    # insertion/interchange heuristic
    def insertion_interchange(self):
        packages = set()
        for deliver in self.routes.keys():
            for j in range(0, len(self.routes[deliver])):
                packages.add((self.routes[deliver][j], deliver, j))

        noChange = self.insertion_interchange_iteration(set(packages))


    def insertion_interchange_iteration(self, packages):
        for o in packages:
            r_route = o[0]

    def exam_insert_package(self, pack, r_deliver, r_index, s_deliver):
        graph = self.graph
        delivers = self.colony.delivers

        r_route = self.routes[r_deliver]
        s_route = self.routes[s_deliver]
        # r_route_cost = self.routes_cost[r_deliver]
        # s_route_cost = self.routes_cost[s_deliver]
        # r_route_capacity = self.routes_capacity[r_deliver]
        s_route_capacity = self.routes_capacity[s_deliver]

        s_route_nodes = set()
        for i in range(0, len(s_route)):
            s_route_nodes.add(s_route[i].pos)

        # none neighbours served by target deliver
        if not graph.cand_list[pack.pos].intersection(s_route_nodes):
            return None
        # exceed the max capacity of the target deliver
        if s_route_capacity + pack.capacity > delivers[s_deliver].max_capacity:
            return None

        r_pre_index = r_index - 1
        r_suc_index = (r_index + 1) % len(r_route)
        strategy = None
        decrease = 0
        for s_index in range(0, len(s_route)):
            s_pre_index = s_index
            s_suc_index = (s_index + 1) % len(s_route)
            r_cost = - graph.delta(r_route[r_pre_index].pos, pack.pos) - graph.delta(pack.pos, r_route[r_suc_index].pos)
            s_cost = graph.delta(s_route[s_pre_index].pos, pack.pos) + graph.delta(pack.pos, s_route[s_suc_index].pos)
            if r_cost + s_cost < decrease:
                decrease = r_cost + s_cost
                strategy = (pack, r_deliver, r_index, s_deliver, s_index, decrease)
        return strategy

    def exam_interchange_package(self):

    def local_updating_rule(self, curr_node, next_node):
        graph = self.colony.graph
        val = (1 - self.Rho) * graph.tau(curr_node, next_node) + (self.Rho * graph.tau0)
        graph.update_tau(curr_node, next_node, val)