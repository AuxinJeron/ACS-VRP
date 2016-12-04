from math import pow
from threading import *
from VRPModel import Package
from enum import Enum
import random
import logging

logger = logging.getLogger("logger")

class AntStatus(Enum):
    suspend = 1
    active = 2
    succeed= 3
    failed = 4

class Ant(Thread):
    def __init__(self, ID, colony):
        Thread.__init__(self)
        self.cv = Condition()
        self.id = ID
        self.colony = colony
        self.dead = False
        self.working = False
        self.status = AntStatus.suspend

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
            if self.demands[i] > 0:
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
                self.status = AntStatus.active
                self.run_iteration()
                self.status = AntStatus.suspend
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

        if self.status == AntStatus.failed:
            # failed to find a solution
            self.path_cost = float('inf')
            self.colony.update(self)
        else:
            # succeed to find a solution
            # local search update
            # use 2-opt heuristic
            for key in self.routes.keys():
             self.routes[key] = self.opt_heuristic(self.routes[key])
            self.update_optimum_routes()
            # insertion and interchange heuristic
            self.insertion_interchange()

            self.update_optimum_routes()
            # compress path
            for deliver in self.routes:
                path = self.routes[deliver]
                self.routes[deliver] = self.compress_path(path)
            self.colony.update(self)

        # update global colony
        logger.debug('===========Ant {} terminated==========='.format(self.id))

    def end(self):
        if not self.nodes_to_visit:
            self.status = AntStatus.succeed
        elif not self.delivers:
            self.status = AntStatus.failed
        return self.status != AntStatus.active

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
        self.curr_path_vec.append(Package(new_node, consume_demand, self.curr_deliver.id, len(self.curr_path_vec)))
        self.path_mat[self.curr_node][new_node] = 1
        # current state of ant
        logger.debug('[Insert]Ant {} : {}'.format(str(self.id), self.curr_path_vec))
        logger.debug('[Insert]cost : {}'.format(self.curr_path_cost))
        logger.debug('[Insert]capacity : {}'.format(self.curr_path_capacity))
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

        self.curr_deliver = None
        while self.curr_deliver == None and self.delivers:
            new_deliver = self.delivers.pop()
            if self.check_deliver_feasibility(new_deliver):
                self.curr_deliver = new_deliver
        if self.curr_deliver == None:
            return

        self.curr_node = self.curr_deliver.pos
        self.curr_path_vec = []
        self.curr_path_cost = 0
        consume_demand = min(self.curr_deliver.max_capacity, self.demands[self.curr_node])
        self.demands[self.curr_node] -= consume_demand
        self.curr_path_vec.append(Package(self.curr_node, consume_demand, self.curr_deliver.id, 0))
        self.curr_path_capacity += consume_demand
        if self.demands[self.curr_node] == 0 and self.curr_node in self.nodes_to_visit:
            self.nodes_to_visit.remove(self.curr_node)

        logger.debug('[Find deliver]Ant {} : {}'.format(str(self.id), self.curr_deliver))

        # go to the locker
        locker = self.colony.deliver_locker(self.curr_deliver)
        self.curr_node = locker.pos
        self.curr_path_vec.append(Package(self.curr_node, 0, self.curr_deliver.id, 1))
        if self.curr_node in self.nodes_to_visit:
            self.nodes_to_visit.remove(self.curr_node)
        #logger.debug('[Find deliver]Ant {} Demands'.format(self.id))
        # for i in range(0, len(self.demands)):
        #     logger.debug("Demands {} : {}".format(i, self.demands[i]))

    def check_deliver_feasibility(self, deliver):
        graph = self.graph
        locker = self.colony.deliver_locker(deliver)
        if graph.delta(deliver.pos, locker.pos) + graph.delta(locker.pos, deliver.pos) > deliver.max_distance:
            return False
        return True

    def update_optimum_routes(self):
        self.path_cost = 0
        self.path_mat = [[0 for i in range(0, self.graph.nodes_num)] for i in range(0, self.graph.nodes_num)]

        for deliver in self.routes.keys():
            self.routes_cost[deliver], self.routes_capacity[deliver] = self.update_optimum_path(self.routes[deliver])
            self.path_cost += self.routes_cost[deliver]
            logger.debug("Ant {} Deliver {} : {}".format(self.id, deliver, self.routes[deliver]))
            logger.debug("cost : {}, capacity : {}".format(self.routes_cost[deliver], self.routes_capacity[deliver]))

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

    def compress_path(self, path_vec):
        new_path_vec = [path_vec[0]]
        for i in range(1, len(path_vec)):
            pack = path_vec[i]
            if pack.pos == new_path_vec[-1].pos:
                new_path_vec[-1].capacity += pack.capacity
            elif i == len(path_vec) - 1 and pack.pos == new_path_vec[0].pos:
                new_path_vec[0].capacity += pack.capacity
            else:
                pack.index = len(new_path_vec)
                new_path_vec.append(pack)
        return new_path_vec

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
            for i in range(1, l - 1):
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
        # update package index
        for i in range(0, len(path_vec)):
            path_vec[i].index = i
        return path_vec

    # insertion/interchange heuristic
    def insertion_interchange(self):
        packages = set()
        for deliver in self.routes.keys():
            for j in range(0, len(self.routes[deliver])):
                packages.add(self.routes[deliver][j])

        noChange = False
        self.print_result()
        while not noChange:
            noChange = self.insertion_interchange_iteration(set(packages))
            self.print_result()

    def insertion_interchange_iteration(self, infos):
        noChange = True
        while infos:
            r_pack = infos.pop()
            r_deliver = r_pack.deliver
            r_index = r_pack.index
            if  r_index == 0 or r_index == 1:
                continue
            min_d_insertion = 0
            min_d_interchange = 0
            min_s_insertion = None
            min_s_interchange = None
            for s_deliver in self.routes.keys():
                if r_deliver == s_deliver:
                    continue
                d_insertion, s_insertion = self.exam_insert_package(r_pack, r_deliver, r_index, s_deliver)
                d_interchange, s_interchange = self.exam_interchange_package(r_pack, r_deliver, r_index, s_deliver)
                if d_insertion < min_d_insertion:
                    min_d_insertion = d_insertion
                    min_s_insertion = s_insertion
                if d_interchange < min_d_interchange:
                    min_d_interchange = d_interchange
                    min_s_interchange = s_interchange
            if min_d_insertion >= 0 and min_d_interchange >= 0:
                continue
            noChange = False
            if min_d_insertion < min_d_interchange:
                self.do_insertion_package(min_s_insertion)
            else:
                self.do_interchange_package(min_s_interchange)
        return noChange

    def exam_insert_package(self, pack, r_deliver, r_index, s_deliver):
        graph = self.graph
        delivers = self.colony.delivers_dict

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
            return 0, None
        # exceed the max capacity of the target deliver
        if s_route_capacity + pack.capacity > delivers[s_deliver].max_capacity:
            return 0, None

        r_pre_index = r_index - 1
        r_suc_index = (r_index + 1) % len(r_route)
        strategy = None
        decrease = 0

        # logger.debug("r_route : {}".format(r_route))
        # logger.debug("r_index : {}".format(r_index))
        # logger.debug("r_pre_index : {}".format(r_pre_index))
        # logger.debug("r_suc_index : {}".format(r_suc_index))
        # logger.debug("r_pack : {}".format(pack))

        for s_index in range(1, len(s_route)):
            s_pre_index = s_index
            s_suc_index = (s_index + 1) % len(s_route)
            r_cost = - graph.delta(r_route[r_pre_index].pos, pack.pos) - graph.delta(pack.pos, r_route[r_suc_index].pos) + graph.delta(r_route[r_pre_index].pos, r_route[r_suc_index].pos)
            s_cost = graph.delta(s_route[s_pre_index].pos, pack.pos) + graph.delta(pack.pos, s_route[s_suc_index].pos) - graph.delta(s_route[s_pre_index].pos, s_route[s_suc_index].pos)
            if r_cost + s_cost < decrease:
                decrease = r_cost + s_cost
                strategy = (pack, r_deliver, r_index, s_deliver, s_index)
        # if strategy != None:
        #     logger.debug("Ant {} insertion change:".format(self.id))
        #     logger.debug("r_pack : {}".format(pack))
        #     logger.debug("r_deliver : {} r_index : {} s_deliver : {} s_index : {}".format(r_deliver, r_index, s_deliver, strategy[4]))
        return decrease, strategy

    def do_insertion_package(self, strategy):
        graph = self.graph
        r_pack = strategy[0]
        r_deliver = strategy[1]
        r_index = strategy[2]
        s_deliver = strategy[3]
        s_index = strategy[4]

        r_route = self.routes[r_deliver]
        s_route = self.routes[s_deliver]

        # logger.debug("Ant {} insertion change:".format(self.id))
        # logger.debug("r_pack : {}".format(r_pack))
        # logger.debug("r_deliver : {} r_index : {} s_deliver : {} s_index : {}".format(r_deliver, r_index, s_deliver, s_index))
        #
        # logger.debug("origin r_route : {}".format(self.routes[r_deliver]))
        # logger.debug("origin s_route : {}".format(self.routes[s_deliver]))
        # logger.debug("r_route origin cost : {}".format(self.routes_cost[r_deliver]))
        # logger.debug("s_route origin cost : {}".format(self.routes_cost[s_deliver]))

        # update route capacity
        self.routes_capacity[r_deliver] -= r_pack.capacity
        self.routes_capacity[s_deliver] += r_pack.capacity

        # update route cost
        r_pre_index = r_index - 1
        r_suc_index = (r_index + 1) % len(r_route)
        s_pre_index = s_index
        s_suc_index = (s_index + 1) % len(s_route)
        r_cost = - graph.delta(r_route[r_pre_index].pos, r_pack.pos) - graph.delta(r_pack.pos, r_route[r_suc_index].pos) + graph.delta(r_route[r_pre_index].pos, r_route[r_suc_index].pos)
        s_cost = graph.delta(s_route[s_pre_index].pos, r_pack.pos) + graph.delta(r_pack.pos, s_route[s_suc_index].pos) - graph.delta(s_route[s_pre_index].pos, s_route[s_suc_index].pos)
        self.routes_cost[r_deliver] += r_cost
        self.routes_cost[s_deliver] += s_cost

        # logger.debug("r_route wrong cost : {} r_cost : {}".format(self.routes_cost[r_deliver], r_cost))
        # logger.debug("s_route wrong cost : {} s_cost : {}".format(self.routes_cost[s_deliver], s_cost))

        # update the route
        r_pack.deliver = s_deliver
        self.routes[r_deliver] = r_route[0:r_index]
        if r_suc_index != 0:
            self.routes[r_deliver] += r_route[r_suc_index:]
        if s_suc_index == 0:
            self.routes[s_deliver] = s_route[:] + [r_pack]
        else:
            self.routes[s_deliver] = s_route[0:s_suc_index] + [r_pack] + s_route[s_suc_index:]
        for i in range(r_index, len(self.routes[r_deliver])):
            self.routes[r_deliver][i].index = i
        for i in range(s_suc_index, len(self.routes[s_deliver])):
            self.routes[s_deliver][i].index = i

        # self.routes_cost[r_deliver] = self.tour_length(self.routes[r_deliver])
        # self.routes_cost[s_deliver] = self.tour_length(self.routes[s_deliver])
        # logger.debug("new r_route : {}".format(self.routes[r_deliver]))
        # logger.debug("new s_route : {}".format(self.routes[s_deliver]))
        # logger.debug("r_route correct cost : {}".format(self.routes_cost[r_deliver]))
        # logger.debug("s_route correct cost : {}".format(self.routes_cost[s_deliver]))

    def exam_interchange_package(self, pack, r_deliver, r_index, s_deliver):
        graph = self.graph
        delivers = self.colony.delivers_dict

        r_route = self.routes[r_deliver]
        s_route = self.routes[s_deliver]
        # r_route_cost = self.routes_cost[r_deliver]
        # s_route_cost = self.routes_cost[s_deliver]
        r_route_capacity = self.routes_capacity[r_deliver]
        s_route_capacity = self.routes_capacity[s_deliver]

        s_route_nodes = set()
        for i in range(0, len(s_route)):
            s_route_nodes.add(s_route[i].pos)

        # none neighbours served by target deliver
        if not graph.cand_list[pack.pos].intersection(s_route_nodes):
                return 0, None

        r_pack = pack
        r_pre_index = r_index - 1
        r_suc_index = (r_index + 1) % len(r_route)
        strategy = None
        decrease = 0

        # logger.debug("r_route : {}".format(r_route))
        # logger.debug("r_index : {}".format(r_index))
        # logger.debug("r_pre_index : {}".format(r_pre_index))
        # logger.debug("r_suc_index : {}".format(r_suc_index))
        # logger.debug("r_pack : {}".format(r_pack))

        for s_index in range(2, len(s_route)):
            s_pack = s_route[s_index]
            # check the capacity
            if r_route_capacity - r_pack.capacity + s_pack.capacity > delivers[r_deliver].max_capacity:
                continue
            if s_route_capacity - s_pack.capacity + r_pack.capacity > delivers[s_deliver].max_capacity:
                continue
            s_pre_index = s_index - 1
            s_suc_index = (s_index + 1) % len(s_route)
            r_cost = -graph.delta(r_route[r_pre_index].pos, r_pack.pos) - graph.delta(r_pack.pos, r_route[r_suc_index].pos)
            r_cost += graph.delta(r_route[r_pre_index].pos, s_pack.pos) + graph.delta(s_pack.pos, r_route[r_suc_index].pos)
            s_cost = -graph.delta(s_route[s_pre_index].pos, s_pack.pos) - graph.delta(s_pack.pos, s_route[s_suc_index].pos)
            s_cost += graph.delta(s_route[s_pre_index].pos, r_pack.pos) + graph.delta(r_pack.pos, s_route[s_suc_index].pos)
            if r_cost + s_cost < decrease:
                decrease = r_cost + s_cost
                strategy = (r_pack, r_deliver, r_index, s_pack, s_deliver, s_index)
        # if strategy != None:
        #     logger.debug("Ant {} interchange change:".format(self.id))
        #     logger.debug("r_pack : {}".format(r_pack))
        #     logger.debug("s_pack : {}".format(strategy[3]))
        #     logger.debug("r_deliver : {} r_index : {} s_deliver : {} s_index : {}".format(r_deliver, r_index, s_deliver, strategy[5]))
        return decrease, strategy

    def do_interchange_package(self, strategy):
        graph = self.graph
        r_pack = strategy[0]
        r_deliver = strategy[1]
        r_index = strategy[2]
        s_pack = strategy[3]
        s_deliver = strategy[4]
        s_index = strategy[5]

        r_route = self.routes[r_deliver]
        s_route = self.routes[s_deliver]

        # logger.debug("Ant {} interchange change:".format(self.id))
        # logger.debug("r_pack : {}".format(r_pack))
        # logger.debug("s_pack : {}".format(s_pack))
        # logger.debug("r_deliver : {} r_index : {} s_deliver : {} s_index : {}".format(r_deliver, r_index, s_deliver, s_index))
        #
        # logger.debug("origin r_route : {}".format(self.routes[r_deliver]))
        # logger.debug("origin s_route : {}".format(self.routes[s_deliver]))
        # logger.debug("r_route origin cost : {}".format(self.routes_cost[r_deliver]))
        # logger.debug("s_route origin cost : {}".format(self.routes_cost[s_deliver]))

        # update route capacity
        self.routes_capacity[r_deliver] += s_pack.capacity - r_pack.capacity
        self.routes_capacity[s_deliver] += r_pack.capacity - s_pack.capacity

        # update route cost
        r_pre_index = r_index - 1
        r_suc_index = (r_index + 1) % len(r_route)
        s_pre_index = s_index - 1
        s_suc_index = (s_index + 1) % len(s_route)
        r_cost = -graph.delta(r_route[r_pre_index].pos, r_pack.pos) - graph.delta(r_pack.pos, r_route[r_suc_index].pos)
        r_cost += graph.delta(r_route[r_pre_index].pos, s_pack.pos) + graph.delta(s_pack.pos, r_route[r_suc_index].pos)
        s_cost = -graph.delta(s_route[s_pre_index].pos, s_pack.pos) - graph.delta(s_pack.pos, s_route[s_suc_index].pos)
        s_cost += graph.delta(s_route[s_pre_index].pos, r_pack.pos) + graph.delta(r_pack.pos, s_route[s_suc_index].pos)
        self.routes_cost[r_deliver] += r_cost
        self.routes_cost[s_deliver] += s_cost

        # logger.debug("r_route wrong cost : {} r_cost : {}".format(self.routes_cost[r_deliver], r_cost))
        # logger.debug("s_route wrong cost : {} s_cost : {}".format(self.routes_cost[s_deliver], s_cost))

        # update the route
        r_pack.deliver = s_deliver
        s_pack.deliver = r_deliver
        self.routes[r_deliver] = r_route[0:r_index] + [s_pack]
        if r_suc_index != 0:
            self.routes[r_deliver] += r_route[r_suc_index:len(r_route)]
        self.routes[s_deliver] = s_route[0:s_index] + [r_pack]
        if s_suc_index != 0:
            self.routes[s_deliver] += s_route[s_suc_index:len(s_route)]
        for i in range(r_index, len(self.routes[r_deliver])):
            self.routes[r_deliver][i].index = i
        for i in range(s_index, len(self.routes[s_deliver])):
            self.routes[s_deliver][i].index = i

        # self.routes_cost[r_deliver] = self.tour_length(self.routes[r_deliver])
        # self.routes_cost[s_deliver] = self.tour_length(self.routes[s_deliver])
        # logger.debug("new r_route : {}".format(self.routes[r_deliver]))
        # logger.debug("new s_route : {}".format(self.routes[s_deliver]))
        # logger.debug("r_route correct cost : {}".format(self.routes_cost[r_deliver]))
        # logger.debug("s_route correct cost : {}".format(self.routes_cost[s_deliver]))

    def local_updating_rule(self, curr_node, next_node):
        graph = self.colony.graph
        val = (1 - self.Rho) * graph.tau(curr_node, next_node) + (self.Rho * graph.tau0)
        graph.update_tau(curr_node, next_node, val)

    def print_result(self):
        logger.debug("=============solution=============")
        cost = 0
        for key in self.routes.keys():
            logger.debug("route : {}".format(self.routes[key]))
            logger.debug("cost : {} capacity : {}".format(self.routes_cost[key], self.routes_capacity[key]))
            cost += self.routes_cost[key]
        logger.debug("total cost : {}".format(cost))