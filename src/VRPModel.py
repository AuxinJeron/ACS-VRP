

class Locker:
    def __init__(self, locker_id, pos):
        self.id = locker_id
        self.pos = pos
        self.orders = []

    def __str__(self):
        return "[{}, {}]".format(self.id, self.pos)


class Deliver:
    def __init__(self, deliver_id, pos, max_distance, max_capacity):
        self.id = deliver_id
        self.pos = pos
        self.locker = None
        self.max_distance = max_distance
        self.max_capacity = max_capacity

    def __str__(self):
        return "[{}, {}, {}, {}]".format(self.id, self.pos, self.max_distance, self.max_capacity)