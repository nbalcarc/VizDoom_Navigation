from collections import namedtuple
from decimal import Decimal
from functools import reduce
import math

coord_tuple = namedtuple("Coords", ["x", "y"])

class Line:
    def __init__(self, a = None, b = None):
        if a == None and b == None:
            self._coords = None
        if a != None and b == None:
            b = a[1]
            a = a[0]
        self.coords = (coord_tuple(Decimal(a[0]), Decimal(a[1])), coord_tuple(Decimal(b[0]), Decimal(b[1])))
        self.m, self.b, self.s = generate_equation(self._coords)
        self.corners = {} #dictionary of points and the lines that intersect at that point

        '''
        Standard form of a line:
        Ax + By = C
        aka
        (y-intercept) * x + (x-intercept) * y = (x-intercept * y-intercept)
        aka
        -mx + y = b
        '''

    '''
    def __str__(self) -> str:
        return f"<Line: ({self.coords[0].x},{self.coords[0].y}) to ({self.coords[1].x},{self.coords[1].y})>"
    '''

    @property
    def coords(self) -> tuple[coord_tuple, coord_tuple]:
        return self._coords

    @coords.setter
    def coords(self, c):
        if len(c) == 2:
            if (isinstance(c[0], tuple) or isinstance(c[0], coord_tuple)) and (isinstance(c[1], tuple) or isinstance(c[1], coord_tuple)):
                x1 = c[0][0] if isinstance(c[0][0], Decimal) else Decimal(c[0][0])
                y1 = c[0][1] if isinstance(c[0][1], Decimal) else Decimal(c[0][1])
                x2 = c[1][0] if isinstance(c[1][0], Decimal) else Decimal(c[1][0])
                y2 = c[1][1] if isinstance(c[1][1], Decimal) else Decimal(c[1][1])
                self._coords = (coord_tuple(x1, y1), coord_tuple(x2, y2))
                self.m, self.b, self.s = generate_equation(self._coords)

    @property
    def length(self):
        return ((self._coords[0].x - self._coords[1].x)**2 + (self._coords[0].y - self._coords[1].y)**2)**Decimal("0.5")
    
    def set_coords(self, a, b):
        self.coords = (a, b)

    def equation(self, x = None, y = None):
        if x != None and y == None:
            if not isinstance(self.s, bool) or not self.s: #if self is not vertical
                return self.m * Decimal(x) + self.b
            else: #self is vertical
                return None
        elif y != None and x == None:
            if not isinstance(self.s, bool) or self.s: #if self is not horizontal, might break with verticals
                return (y - self.b) / self.m
            else: #self is horizontal
                return None
        elif y != None and x != None: #essentially works as a check on whether the point (x,y) is on this segment
            returned_y = self.equation(x) #a single recursive call, to check if the y matches with the result of passing x through
            if returned_y == None or round(Decimal(returned_y), 3) == round(Decimal(y), 3): #the point is on the line but not necessarily within the bounds of the segment
                if (round(min(self.coords[0].x, self.coords[1].x), 3) <= round(Decimal(x), 3) <= round(max(self.coords[0].x, self.coords[1].x), 3) and 
                        round(min(self.coords[0].y, self.coords[1].y), 3) <= round(Decimal(y), 3) <= round(max(self.coords[0].y, self.coords[1].y), 3)):
                    return True
            return False
        else: #return a spring representation of the equation
            return f"y = {self.m}x + {self.b}"

    def next_corner(self, direction, side, rotation, coords, corners = "__UNSET__", this_corner = False):
        '''
        Provide a line-follow direction, the side of the line we're on, the rotation of the search, and the coordinates of the search (may be a corner or just a point on the line). 
        NOTE: direction (-1 = left, 1 = right), side (-1 = left, 1 = right), rotation (-1 = counterclockwise, 1 = clockwise)
        '''

        #this_corner says whether to teleport to the next corner or just find the next line on the current corner

        #Find the angle between two lines based on their slopes: arctan((m1 - m2) / (1 + m1*m2))
        #This formula works clockwise from m1 to m2, though it will return negative values in addition to positive

        if corners == "__UNSET__":
            corners = self.corners
        coords = coord_tuple(coords[0], coords[1])
        if not self.equation(coords.x, coords.y): #if the coordinates aren't on the line
            return None, None, None

        #search for the next corner, whether or not we're on a corner already, if search_next is True
        if this_corner == False:
            corn_coords = list(corners.keys()) #get all the coordinates for the corners
            if self.s == True: #vertical line
                corn_coords.sort(key = lambda c: c.y)
                if direction == 1: #if we're searching upwards
                    corn_coords.sort(key = lambda c: c.y)
                    corn_coord = next(c for c in corn_coords if c.y > coords.y)
                else: #we're searching downwards
                    corn_coords.sort(key = lambda c: c.y, reverse = True)
                    corn_coord = next(c for c in corn_coords if c.y < coords.y)
            else: #not vertical line
                if direction == 1: #if we're searching towards the right
                    corn_coords.sort(key = lambda c: c.x)
                    corn_coord = next(c for c in corn_coords if c.x > coords.x) #find the first corner with a larger x value than our specified coordinates
                else: #we're searching towards the left
                    corn_coords.sort(key = lambda c: c.x, reverse = True)
                    corn_coord = next(c for c in corn_coords if c.x < coords.x) #find the first corner with a smaller x value than our specified coordinates
        else:
            corn_coord = coords
        lines = corners[corn_coord] #retrieve the lines this corner contains

        if self.s == True: #we're dealing with a vertical line here, so the usual formulas break :)

            #the line is literally straight upwards
            if direction == 1: #reached the corner by moving up
                cur_angle = 270
            else: #reached the corner by moving down
                cur_angle = 90 
            
            def find_angles(s, x): #s is the list of angles prior to this, and x is the line whose angles we will append to s
                if x.s != True: #comparing the current vertical line with a nonvertical line
                    #RULE: if we are not on the left endpoint then generate the left angle
                    if corn_coord.x > min(x.coords[0].x, x.coords[1].x): #we are not on the left endpoint of x
                        s.append(((cur_angle - math.degrees(math.atan(x.m)) + 180) % 360, x)) #generate the left angle
                    if corn_coord.x < max(x.coords[0].x, x.coords[1].x): #we are not on the right endpoint of x
                        s.append(((cur_angle - math.degrees(math.atan(x.m)) + 360) % 360, x)) #generate the right angle
                else: #comparing a vertical with a vertical
                    if corn_coord.y > min(x.coords[0].y, x.coords[1].y): #we aren't on the bottom endpoint of the vertical line
                        s.append(((cur_angle + 90) % 360, x))
                    if corn_coord.y < max(x.coords[0].y, x.coords[1].y): #we aren't on the top endpoint of the vertical line
                        s.append(((cur_angle + 270) % 360, x))
                return s
            
        else: #we're dealing with a diagonal or horizontal line

            #calculate the angle from 0 to the current line, only positive
            if direction == 1: #reached the corner by moving right
                cur_angle = (math.degrees(math.atan(self.m)) + 180) % 360
            else: #reached the corner by moving left
                cur_angle = (math.degrees(math.atan(self.m)) + 360) % 360

            def find_angles(s, x): #s is the list of angles prior to this, and x is the line whose angles we will append to s
                if x.s == True: #comparing a nonvertical with a vertical
                    if corn_coord.y > min(x.coords[0].y, x.coords[1].y): #we are not on the bottom endpoint of x
                        s.append(((cur_angle + 90) % 360, x))
                    if corn_coord.y < max(x.coords[0].y, x.coords[1].y): #we are not on the top endpoint of x
                        s.append(((cur_angle + 270) % 360, x))
                else: #comparing a nonvertical with a nonvertical
                    if round(x.m * self.m, 3) == -1: #the two lines are perpendicular
                        if corn_coord.x > min(x.coords[0].x, x.coords[1].x): #we are not on the left endpoint of x
                            s.append((90, x)) #generate the left angle
                        if corn_coord.x < max(x.coords[0].x, x.coords[1].x): #we are not on the right endpoint of x
                            s.append((270, x)) #generate the right angle
                    else: #comparing two nonvertical, nonperpendicular lines
                        if self.s == False and x.s == False: #comparing two horizontal lines
                            s.append((180, x))
                        else:
                            if corn_coord.x > min(x.coords[0].x, x.coords[1].x): #we are not on the left endpoint of x
                                s.append(((math.degrees(math.atan((self.m - x.m) / (1 + self.m * x.m))) + 180) % 360, x))
                            if corn_coord.x < max(x.coords[0].x, x.coords[1].x): #we are not on the right endpoint of x
                                s.append(((math.degrees(math.atan((self.m - x.m) / (1 + self.m * x.m))) + 360) % 360, x))
                return s

        lines = reduce(find_angles, lines, [])
        
        #add the current line's opposite side if we are not on the endpoint of the line in the direction that we're searching
        if self.s == True:
            if (direction == -1 and corn_coord.y > min(self.coords[0].y, self.coords[1].y) or direction == 1 and corn_coord.y < max(self.coords[0].y, self.coords[1].y)): 
                lines.append((180, self))
        else:
            if (direction == -1 and corn_coord.x > min(self.coords[0].x, self.coords[1].x) or direction == 1 and corn_coord.x < max(self.coords[0].x, self.coords[1].x)): 
                lines.append((180, self))


        #by this point we have a list of angles to each of the paths. All paths are guaranteed to work (so if a line ends at this corner it'll only appear once)
        #if we're searching clockwise, find the lowest angle. If we're searching counterclockwise, find the highest angle
        lines.sort(key = lambda x: x[0], reverse = rotation == -1)
        if len(lines) == 0: #if there are no other lines at this corner then just turn back i guess, idk this shouldn't be possible
            new_line = (0, self) #new_line has this structure: (relative angle to this new line, the new line's object)
        else:
            new_line = lines[0]

        #calculate the true angle of the new line, cur_angle is the true angle of the current line and the angle to the new line is a relative angle
        new_angle = (cur_angle - new_line[0] + 360) % 360

        #need logic to distinguish if we're coming in from the left or right, so that we end up with the right direction in the end
        if 0 <= new_angle <= 90 or 360 >= new_angle > 270: #the new angle is in the 1st or 4th quadrant
            direction = 1
        else:
            direction = -1

        #calculate the side of the line we'll end up on
        if (((0 < cur_angle < 180 and 0 < new_angle < 180) or (180 < cur_angle < 360 and 180 < new_angle < 360)) or #if the hemisphere remains the same, then flip the side we're on
                ((new_angle == 0 and 180 < cur_angle < 360) or (new_angle == 180 and 0 < cur_angle < 180)) or #moving onto horizontal line
                ((cur_angle == 0 and 180 < new_angle < 360) or (cur_angle == 180 and 0 < new_angle < 180))): #the current line is horizontal 
            side *= -1
        return new_line[1], direction, side, rotation, corn_coord

    def midpoint(self) -> tuple:
        return coord_tuple((self.coords[0].x + self.coords[1].x) / 2, (self.coords[0].y + self.coords[1].y) / 2)

    def extend_coordinates(self, line): #will return the coordinates of a new extended line between touching and parallel lines self and line
        #if validate == False or (validate == True and check_intersection(self, line) == (True, "PARALLEL")):
        if self.s == True: #lines are vertical
            order_func = lambda c: c.y
        else: #lines are not vertical
            order_func = lambda c: c.x
        ordered_points = [self.coords[0], self.coords[1], line.coords[0], line.coords[1]] #sort the points from lowest to highest
        ordered_points.sort(key = order_func)
        return (ordered_points[0], ordered_points[-1])

    def is_endpoint(self, coords):
        rounded_x = round(coords.x, 3)
        rounded_y = round(coords.y, 3)
        if ((round(self.coords[0].x, 3) == rounded_x and round(self.coords[0].y, 3) == rounded_y) or
            (round(self.coords[1].x, 3) == rounded_x and round(self.coords[1].y, 3) == rounded_y)):
            return True
        return False

    def add_intersection(self, intersection, line): #this won't confirm if the intersection is correct, called by check_intersection
        if self.corners.get(intersection) == None:
            self.corners[intersection] = {line}
        else:
            self.corners[intersection].add(line)


def generate_equation(point: tuple, point1: tuple = None) -> tuple:
    if point1 == None: #allow both one and two parameters
        point1 = point[1]
        point = point[0]
    if point[0] - point1[0] == 0: #the line is vertical, change the approach so as to not cause mathematical errors
        s = True
        m = "VERTICAL"
        b = "VERTICAL"
    else: #the line is not vertical (so in most cases it will not crash, yay)
        m = (point[1] - point1[1]) / (point[0] - point1[0])
        b = point[1] - point[0] * m

        if point[1] - point1[1] == 0: #the line is horizontal
            s = False
        else: #the line is diagonal
            s = None
    return m, b, s

#calculates distance from point to line, 3 cases: endpoint, endpoint1, projection
def distance_to_line(point: coord_tuple, line: Line, return_point = False):
    endpoint, endpoint1 = line.coords #each endpoint is a coord_tuple
    projection: coord_tuple = project(point, line)
    #decide whether to include projection or not (is it within the bounds of the line segment?)
    if (min(line.coords[0].x, line.coords[1].x) <= projection.x <= max(line.coords[0].x, line.coords[1].x) and
            min(line.coords[0].y, line.coords[1].y) <= projection.y <= max(line.coords[0].y, line.coords[1].y)):
        points = [endpoint1, projection]
    else:
        points = [endpoint1]
    closest_point = endpoint
    closest_distance = distance(point, endpoint)
    for pnt in points:
        dist = distance(point, pnt)
        if dist < closest_distance: #if the new point is closer, replace the stored one
            closest_point = pnt
            closest_distance = dist
    if return_point == True: #if return_point is true, return the actual point we're closest to
        return closest_point
    return closest_distance #otherwise, return the distance to that closest point

#projection of a point onto a line
def project(point: coord_tuple, line: Line) -> coord_tuple:
    if line.s == True: #if line is vertical, then simply project the point's y value onto the line's x value
        return coord_tuple(line.coords[0].x, point.y)
    if line.s == False: #if line is horizontal, do the same but with x and y
        return coord_tuple(point.x, line.coords[0].y)
    m = -1 * (1 / float(line.m)) #slope of point's line
    b = float(point.y) + float(point.x) / float(line.m) #y-intercept of point's line
    return coord_tuple((float(line.b) - b) / (m - float(line.m)), (b * float(line.m) - float(line.b) * m) / (float(line.m) - m)) #intersection point

def distance(point: coord_tuple, point1: coord_tuple) -> float:
    return ((float(point.x) - float(point1.x)) ** 2 + (float(point.y) - float(point1.y)) ** 2) ** 0.5

if __name__ == "__main__":
    print("hi there buddy, import this module don't run it :)")
