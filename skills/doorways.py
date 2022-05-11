from skills.geometry import *

class LocalEnum:
    #check_intersection parameters
    update_none = 0
    update_both = 1
    update_first = 2

    #check_intersection return
    no_intersection = 0
    intersection = 1
    intersection_parallel = 2
    overlap_parallel = 3
    no_intersection_parallel = 4

    #line.s
    diagonal = None
    horizontal = False
    vertical = True

enum = LocalEnum()

class Wall(Line):
    def __init__(self, a = None, b = None):
        super().__init__(a, b)
        self.doorway_corners = {} #this may not even be needed honestly
        self.all_corners = {}

    def prepare_all_corners(self):
        if self.all_corners == None:
            keys = set(self.doorway_corners.keys())

            def concatenate(dicti: dict, key):
                lis = self.doorway_corners[key] #this is a set
                if dicti.get(key) != None:
                    map(lambda x: dicti[key].add(x), lis) #for every item in the set, add it to the existing set
                else:
                    dicti[key] = lis
                return dicti

            #first we need to concatenate the two lists
            self.all_corners = reduce(concatenate, keys, self.corners.copy())

    def next_corner_doorways(self, direction, side, rotation, coords): #find the next corner while factoring in the doorways
        #print("DEBUGGING, NEXT_CORNER &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
        #print("DEBUGGING, ALL_CORNERS", self.all_corners)
        return self.next_corner(direction, side, rotation, coords, self.all_corners)

    def add_doorway_intersection(self, intersection, line):
        if self.doorway_corners.get(intersection) == None:
            self.doorway_corners[intersection] = {line}
        else:
            self.doorway_corners[intersection].add(line)
        if self.all_corners.get(intersection) == None:
            self.all_corners[intersection] = {line}
        else:
            self.all_corners[intersection].add(line)

    def add_intersection(self, intersection, line): #this will also factor in all_corners
        super().add_intersection(intersection, line)
        if self.all_corners.get(intersection) == None:
            self.all_corners[intersection] = {line}
        else:
            self.all_corners[intersection].add(line)

    def to_string(self):
        return f"{self.coords[0]} to {self.coords[1]}"

class Doorway(Wall):
    def __init__(self, a = None, b = None):
        super().__init__(a, b)
        self.room_l = None
        self.room_r = None

    def adjacent_room(self, room): #given a room, find the adjacent room
        if self.room_l == room:
            return self.room_r
        elif self.room_r == room:
            return self.room_l
        else:
            return None

class Room():
    def __init__(self, doorways = None):
        if doorways != None:
            self.doorways = doorways #a room stores a list of doorways that it contains
        else:
            self.doorways = set()
        self.corners = set()
        self.walls = set()
        #self.generate_name()

    #def generate_name(self):
    #    global room_name
    #    self.name = room_name
    #    room_name += 1

    def adjacent_room(self, doorway): #given a doorway, find the adjacent room
        if doorway.room_l == self:
            return doorway.room_r
        elif doorway.room_r == self:
            return doorway.room_l
        else:
            return None

    def adjacent_rooms(self): #return a set of all adjacent rooms
        ret = set()
        for doorway in self.doorways:
            ret.add(self.adjacent_room(doorway))
        return ret


#may request a function for updating in the future
def check_intersection(line: Line, line1: Line, update: int = 0):
    if line.m == line1.m: #the lines are parallel
        if line.s == enum.vertical: #lines are vertical
            if line.coords[0].x != line1.coords[0].x: #the vertical lines don't intersect, don't line up
                rcode, rcoords = enum.no_intersection_parallel, None
            elif (max(line.coords[0].y, line.coords[1].y) == min(line1.coords[0].y, line1.coords[1].y) or
                    max(line1.coords[0].y, line1.coords[1].y) == min(line.coords[0].y, line.coords[1].y)): #parallel vertical lines share an endpoint
                rcode, rcoords = enum.intersection_parallel, line.coords[0] if (line1.coords[0] == line.coords[0] or line1.coords[1] == line.coords[0]) else line.coords[1]
            elif (max(line.coords[0].y, line.coords[1].y) > max(line1.coords[0].y, line1.coords[1].y) > min(line.coords[0].y, line.coords[1].y) or
                    max(line1.coords[0].y, line1.coords[1].y) > max(line.coords[0].y, line.coords[1].y) > min(line1.coords[0].y, line1.coords[1].y)):
                rcode, rcoords = enum.overlap_parallel, None #the parallel vertical lines overlap each other
            elif (max(line1.coords[0].y, line1.coords[1].y) > min(line.coords[0].y, line.coords[1].y) > min(line1.coords[0].y, line1.coords[0].y) or
                    max(line.coords[0].y, line.coords[1].y) > min(line1.coords[0].y, line1.coords[1].y) > min(line.coords[0].y, line.coords[0].y)):
                rcode, rcoords = enum.overlap_parallel, None #the parallel vertical lines overlap each other (in a different way)
            else:
                rcode, rcoords = enum.no_intersection_parallel, None #vertical parallel lines don't touch
        else: #lines aren't vertical, can be diagonal or horizontal
            if line.b != line1.b: #don't line up but still parallel
                rcode, rcoords = enum.no_intersection_parallel, None
            elif (max(line.coords[0].x, line.coords[1].x) == min(line1.coords[0].x, line1.coords[1].x) or 
                    max(line1.coords[0].x, line1.coords[1].x) == min(line.coords[0].x, line.coords[1].x)): #lines share an endpoint
                rcode, rcoords = enum.intersection_parallel, line.coords[0] if (line1.coords[0] == line.coords[0] or line1.coords[1] == line.coords[0]) else line.coords[1]
            elif (max(line.coords[0].x, line.coords[1].x) > max(line1.coords[0].x, line1.coords[1].x) > min(line.coords[0].x, line.coords[1].x) or
                    max(line1.coords[0].x, line1.coords[1].x) > max(line.coords[0].x, line.coords[1].x) > min(line1.coords[0].x, line1.coords[1].x)):
                rcode, rcoords = enum.overlap_parallel, None #lines overlap each other
            elif (max(line1.coords[0].x, line1.coords[1].x) > min(line.coords[0].x, line.coords[1].x) > min(line1.coords[0].x, line1.coords[0].x) or
                    max(line.coords[0].x, line.coords[1].x) > min(line1.coords[0].x, line1.coords[1].x) > min(line.coords[0].x, line.coords[0].x)):
                rcode, rcoords = enum.overlap_parallel, None #lines overlap each other (in a different way)
            else:
                rcode, rcoords = enum.no_intersection_parallel, None #lines don't touch
    elif line.s == enum.vertical or line1.s == enum.vertical: #one of the two lines is vertical
        if line.s == enum.vertical: #if line is vertical
            vert = line
            nvert = line1
        else: #line1 is vertical
            vert = line1
            nvert = line
        intersection = coord_tuple(vert.coords[0].x, nvert.equation(x = vert.coords[0].x))
        if (min(nvert.coords[0].x, nvert.coords[1].x) <= intersection.x <= max(nvert.coords[1].x, nvert.coords[0].x) and 
                min(vert.coords[0].y, vert.coords[1].y) <= intersection.y <= max(vert.coords[1].y, vert.coords[0].y)):
            rcode, rcoords = enum.intersection, intersection #the intersection is within the bounds of both segments
        else:
            rcode, rcoords = enum.no_intersection, intersection #intersection lies outside the bounds of both segments
    else: #neither of the two lines are vertical
        intersection = coord_tuple((line.b - line1.b) / (line1.m - line.m), (line1.b * line.m - line.b * line1.m) / (line.m - line1.m))
        if (min(line.coords[0].x, line.coords[1].x) <= intersection.x <= max(line.coords[0].x, line.coords[1].x) and
                min(line.coords[0].y, line.coords[1].y) <= intersection.y <= max(line.coords[0].y, line.coords[1].y)):
            rcode, rcoords = enum.intersection, intersection #the intersection is within the bounds of both segments
        else:
            rcode, rcoords = enum.no_intersection, intersection

    #now update the lines if asked to and return
    valid = rcode == enum.intersection or rcode == enum.intersection_parallel
    if update == enum.update_both and valid: #update both lines to include this corner
        #update first line
        if type(line1) == Wall:
            line.add_intersection(rcoords, line1)
        elif type(line1) == Doorway:
            line.add_doorway_intersection(rcoords, line1)
        #update second line
        if type(line) == Wall:
            line1.add_intersection(rcoords, line)
        elif type(line) == Doorway:
            line1.add_doorway_intersection(rcoords, line)
    elif update == enum.update_first and valid: #update only the first line to include this corner
        if type(line1) == Wall:
            line.add_intersection(rcoords, line1)
        elif type(line1) == Doorway:
            line.add_doorway_intersection(rcoords, line1)
    return rcode, rcoords
