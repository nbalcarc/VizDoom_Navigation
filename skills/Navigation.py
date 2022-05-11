from collections import namedtuple
from functools import reduce
import sys
import math
from skills.doorways import *
import itertools

class Navigator():

    def __init__(self, walls = None, debugging = False, manual_input = False):
        self.unit = Decimal("16.0076")     #the size of a tile, or the distance the player travels in one move
        self.current_location = None
        self.walls = set()
        self.obstacles = [] #obstacle objects, dictionaries
        self.enemies = []
        self.wall_tiles = set() #tiles tied to walls
        self.obstacles_old = set() #tiles tied to obstacles (don't move all game but are different every game, may be deprecated in favor of wall_tiles)
        self.temporary_tiles = set() #constantly moving objects like enemies
        self.access_tiles = set() #temporarily block access to certain areas (finding a new path to destination or blocking out all other doorways)
        if walls != None:
            self.walls_raw = walls
            self.setup_map()
        else:
            self.walls_raw = None
        self.map_corners = set()
        self.doorways = set()
        self.rooms = set()
        self.path_actions = [] #set of instructions to reach a location
        self.path_tiles = [] #used for movement verification
        self.path_doorways = [] #set of doorways to reach location
        self.path_rooms = []
        self.destination = None #the destination of the pathfinding
        self.tile_bias = None
        self.tile_divider = Decimal(1) #the fineness of tiles compared to the unit
        self.current_action = None
        #self.previous_tile = None
        self.current_tile = None
        self.expected_tile = None
        self.previous_doorway = None #whenever we need to reroute our path, we'll use this value
        self.anterior_doorway = None #the doorway prior to previous_doorway, we'll be sitting on this doorway at some point
        self.crossing_doorway = False #there are certain places where this bool will override the current pathfinding to cross a doorway

        self.debugging = debugging #changes some behavior to either respect the agent's current location or the expected current location, plus other behavior

        if manual_input == True:
            self.prepare_window()
        else:
            self.reading = False
            self.window = None

        '''
        dict({'action': 'left'})          #1
        dict({'action': 'right'})         #2
        dict({'action': 'forward'})       #3
        dict({'action': 'backward'})      #4
        dict({'action': 'turn_left'})     #6
        dict({'action': 'turn_right'})    #7
        '''

    def __del__(self):
        if self.window != None:
            self.window.close()

    def prepare_window(self):
        global sg
        import PySimpleGUIQt as sg
        header = [[sg.Text("Coordinate Chooser", justification = "center", text_color = "#000000", font = "Any 12 bold")]]
        column = [[sg.Text("Status:")], [sg.Text("Current Location:")], [sg.Text("Destination:")]]
        column1 = [[sg.Text("Waiting for input", visible = True, text_color = "#00FF00", key = "_WAITING_"), 
                sg.Text("Executing instructions...", visible = False, text_color = "#0000FF", key = "_EXECUTING_")], 
            [sg.Text("( , )")], [sg.Input(key = "_COORD_X_"), sg.Input(key = "_COORD_Y_")],
            [sg.Checkbox("Run until destination", key = "_RUN_"), sg.Button("Next", key = "_NEXT_"),
                sg.Button("Ok", key = "_OK_")]]
        body = [[sg.Column(column), sg.Column(column1)]]
        window = sg.Window("Coordinate Chooser", header + body)
        self.window = window
        self.reading = True
        window.finalize()

    def finalize_window(self):
        self.window.finalize()

    def get_window(self):
        if self.reading == True:
            self.window["_NEXT_"].update(disabled = False, button_color = ('white', '#283b5b'))
            self.window["_OK_"].update(disabled = False, button_color = ('white', '#283b5b'))
            event, values = self.window.read()
        else:
            event, values = self.window.read(timeout = 10)

        if self.reading == False and values["_RUN_"] == False: #stop automatic pathfinding
            self.allow_reading()

        if event == sg.WIN_CLOSED: #crash
            #self.window.finalize()
            "INTENTIONALLY CRASHED" + 1
        elif event == "_NEXT_":
            #just do whatever is already doing
            self.window.refresh()
            #or crash
            #"INTENTIONALLY CRASHED" + 1
            #pass
        elif event == "_OK_": #we pressed the ok button
            if values["_RUN_"] == True: #we've checked the button to skip to when the bot is at the destination
                self.reading = False
                self.window["_WAITING_"].update(visible = False)
                self.window["_EXECUTING_"].update(visible = True)
                self.window["_NEXT_"].update(disabled = True, button_color = ('black', '#555555'))
                self.window["_OK_"].update(disabled = True, button_color = ('black', '#555555'))
            if values["_COORD_X_"] != "" and values["_COORD_Y_"] != "":
                return Decimal(values["_COORD_X_"]), Decimal(values["_COORD_Y_"])

        return None
            
            
    def allow_reading(self):
        self.reading = True
        self.window["_WAITING_"].update(visible = True)
        self.window["_EXECUTING_"].update(visible = False)
        self.window["_NEXT_"].update(disabled = False, button_color = ('white', '#283b5b'))
        self.window["_OK_"].update(disabled = False, button_color = ('white', '#283b5b'))
        self.window.refresh()


    def update_features(self, feature_vector: dict) -> str: #returns a log entry
        if 'enemies' not in feature_vector: #not a vizdoom feature vector
            return 'This does not appear to be a vizdoom feature vector! Did you forget to set the correct domain in the agent config file?'
        else: #vizdoom feature vector
            self.feature_vector = feature_vector #not yet implemented
            self.current_location = coord_tuple(Decimal(self.feature_vector["player"]["x_position"]), Decimal(self.feature_vector["player"]["y_position"]))
            self.angle = feature_vector["player"]["angle"]
            if self.tile_bias == None:
                self.set_tile_bias(self.current_location)
            if self.walls_raw == None and feature_vector.get("walls") != None:
                self.set_walls(self.feature_vector["walls"])
            #if self.obstacles_old == None:
            #    for obstacle in self.feature_vector["items"]["obstacle"]:
            #        self.obstacles_old.add(coord_tuple(obstacle["x_position"], obstacle["y_position"]))
            if self.obstacles == []:
                print(f"DEBUGGING, {self.feature_vector['items']}")
                print(f"DEBUGGING, {self.feature_vector['items']['obstacle']}")
                for obstacle in self.feature_vector["items"]["obstacle"]:
                    print(f"DEBUGGING, {obstacle}")
                    self.obstacles.append(obstacle)
            self.enemies = [] #needs to be updated every frame
            for enemy in self.feature_vector["enemies"]:
                self.enemies.append(enemy)
            return 'Updated the Navigator feature vector'

    def set_unit(self, unit):
        self.unit = unit

    #if the walls were not provided during an update_featuers() call, you can provide them here
    def set_walls(self, new_walls):
        if self.walls_raw == None:
            self.walls_raw = new_walls
            self.setup_map()

    #prints a customizable set of messages
    def debug_print(self):
        print(f"############ CURRENT LOCATION: {self.current_location}")
        '''
        if self.doorways != None:
            print(f"############ DOORWAYS: {len(self.doorways)}")
            for doorway in self.doorways:
                print(f"{doorway}, {doorway.coords[0]} to {doorway.coords[1]} with rooms {doorway.room_l}, {doorway.room_r}")
        if self.rooms != None:
            print(f"############ ROOMS: {len(self.rooms)}")
            for room in self.rooms:
                print(f"{room}, doorways: {[doorway.to_string() for doorway in room.doorways]}, walls: {[wall.to_string() for wall in room.walls]}")
        if self.obstacles != None:
            print(f"############ OBSTACLES: {len(self.obstacles)}")
            for obstacle in self.obstacles:
                print(f"{obstacle}")
        if self.enemies != None:
            print(f"############ ENEMIES: {len(self.enemies)}")
            for enemy in self.enemies:
                print(f"{enemy}")
        print(f"############ FEATURE VECTOR: {self.feature_vector}")
        '''

    #convert the raw wall coordinates into a full interpretation of the map with rooms and doorways
    def setup_map(self): 
        self.walls = set() #reset all the walls
        
        #first generate the new Wall objects
        self.max_x = None #remember the wall furthest right to find the boundaries of the map initially
        for raw in self.walls_raw: #each wall defined as dictionary with x1, x2, y1, and y2 defined
            self.walls.add(Wall((raw["x1"], raw["y1"]), (raw["x2"], raw["y2"])))
            if self.max_x == None:
                self.max_x = max(raw["x1"], raw["x2"])
            else:
                self.max_x = max(self.max_x, max(raw["x1"], raw["x2"]))

        for a, b in itertools.combinations(self.walls, 2): #find all corners between the walls
            check_intersection(a, b, enum.update_both)

        #set up agent ray
        agent_wall = create_ray(self.current_location, self.max_x, self.walls)
        print("DEBUGGING, AGENT LOCATION:", self.current_location)

        #gather all corners that are part of the map and sort them into a dictionary
        raw_map_corners = discover_map(self.current_location, agent_wall)
        dicti = {}
        for corner in raw_map_corners: #corner layout: Line, direction, side, rotation, coordinates
            if dicti.get(corner[4]) != None: #first add the current corner
                dicti[corner[4]].append(corner[0])
            else:
                dicti[corner[4]] = [corner[0]]
            for wall_corner in corner[0].corners[corner[4]]: #then add all other known lines that intersect at this corner
                dicti[corner[4]].append(wall_corner)
        self.map_corners = dicti

        #extend and sort all the walls in preparation for doorways
        actual_walls = list(map(lambda x: x[0], raw_map_corners))
        extended_walls = []
        while len(actual_walls) > 0:
            cur = actual_walls.pop(0)
            j = 0 #counter for the walls we've compared so far
            while j < len(actual_walls):
                if check_intersection(cur, actual_walls[j], enum.update_none)[0] == enum.intersection_parallel: #the walls intersect and are parallel
                    #cur.extend(actual_walls[j], False) #extend cur to include j
                    cur = Wall(cur.extend_coordinates(actual_walls[j]))
                    actual_walls.pop(j)
                else:
                    j += 1
            if len(extended_walls) == 0:
                extended_walls.append([cur])
                continue
            for group in extended_walls:
                #if check_intersection(cur, group[0], enum.update_none): #the walls are in the same 1d plane
                if ((cur.s == enum.vertical and group[0].s == enum.vertical and cur.coords[0].x == group[0].coords[0].x) or
                        cur.s != enum.vertical and cur.s == group[0].s and cur.b == group[0].b): #the walls are in the same 1d plane
                    group.append(cur)
                    break
            else:
                extended_walls.append([cur])

        #create the doorways
        self.doorways = set()
        for group in extended_walls:
            if group[0].s == enum.vertical: #if vertical
                group.sort(key = (lambda x: x.coords[0].y)) #sort all the items first to reveal the gaps
                for i in range(len(group) - 1): #compare i and i+1 to see the gaps
                    top = group[i].coords[0] if group[i].coords[0].y > group[i].coords[1].y else group[i].coords[1]
                    bot = group[i+1].coords[0] if group[i+1].coords[0].y < group[i+1].coords[1].y else group[i+1].coords[1]
                    new_door = Doorway(bot, top)
                    self.doorways.add(new_door)
            else:
                group.sort(key = (lambda x: x.coords[0].x)) #sort all the items first to reveal the gaps
                for i in range(len(group) - 1): #compare i and i+1 to see the gaps
                    top = group[i].coords[0] if group[i].coords[0].x > group[i].coords[1].x else group[i].coords[1]
                    bot = group[i+1].coords[0] if group[i+1].coords[0].x < group[i+1].coords[1].x else group[i+1].coords[1]
                    new_door = Doorway(bot, top)
                    self.doorways.add(new_door)

        #confirm that no two doorways intersect, and if so then delete both (but don't delete if they intersect at any of the two's endpoints)
        for a, b in itertools.combinations(self.doorways, 2): #compare all two doorways
            inter = check_intersection(a, b)
            if (inter[0] == enum.intersection or inter[0] == enum.intersection_parallel) and not a.is_endpoint(inter[1]) and not b.is_endpoint(inter[1]): 
                self.doorways.discard(a)
                self.doorways.discard(b)


        #TODO split strangely shaped rooms and add doorways here


        #update all walls and doorways to intersect one another
        for doorway in self.doorways:
            for wall in self.map_corners[doorway.coords[0]]:
                check_intersection(wall, doorway, enum.update_both)
            for wall in self.map_corners[doorway.coords[1]]:
                check_intersection(wall, doorway, enum.update_both)
            self.map_corners[doorway.coords[0]].append(doorway)
            self.map_corners[doorway.coords[1]].append(doorway)

        #create the rooms by starting at any doorway and circling around the inside on walls and doorways, noting any doorways we run into
        truncated_doorways = set() #used to discard unused doorways
        frontier = [identify_room(agent_wall, doorway = True)] #grab a doorway close to the agent
        #frontier = [next(iter(self.doorways))]
        while len(frontier) > 0:
            cur = frontier.pop(0)
            truncated_doorways.add(cur)
            if cur.room_l == None: #this door has no defined room on its left/bottom
                if cur.s != enum.horizontal: #if vertical or diagonal
                    returned = discover_room(cur.midpoint(), cur, Room(), 1, -1, 1) #returns current room, doorways found along the way, walls making up the room
                else: #if horizontal
                    returned = discover_room(cur.midpoint(), cur, Room(), -1, -1, 1)
                cur.room_l = returned[0]
                self.rooms.add(returned[0])
                frontier += list(returned[1])
            if cur.room_r == None: #this door has no defined room on its right/top
                if cur.s != enum.horizontal: #if vertical or diagonal
                    returned = discover_room(cur.midpoint(), cur, Room(), -1, 1, 1)
                else: #if horizontal
                    returned = discover_room(cur.midpoint(), cur, Room(), 1, 1, 1)
                cur.room_r = returned[0]
                self.rooms.add(returned[0])
                frontier += list(returned[1])
        

        #during the discovering of the rooms, if a doorway is not discovered then discard it
        self.doorways = truncated_doorways
        print(f"DEBUGGING, {len(self.doorways)} total doorways")
        self.walls_to_tiles()
        print(f"DEBUGGING, {len(self.rooms)} total rooms")

    #create a new set of actions, or return the action if already generated
    def travel_to(self, a = None, b = None):

        if self.window != None:
            print("DEBUGGING, reading")
            returned = self.get_window()
            if returned != None: #if we got a return value, set these as the coords
                a = returned[0]
                b = returned[1]

        if a != None and b == None:
            destination = coord_tuple(Decimal(a[0]), Decimal(a[1]))
        else:
            destination = coord_tuple(Decimal(a), Decimal(b))

        if self.crossing_doorway == True: #if crossing doorway, forget the normal process, just get over the doorway soon
            print("DEBUGGING, CROSSING DOORWAY")
            print(f"DEBUGGING1, length of path_actions: {len(self.path_actions)}")
            ret_action = self.path_actions.pop(0)
            ret_bool = True
            if len(self.path_actions) == 0: #once we're done crossing the doorway, then set the bool to false
                self.crossing_doorway = False
            if len(self.path_doorways) == 0:
                ret_bool = False
            return ret_action, ret_bool

        if (destination.x == None or destination.y == None) and self.destination == None: #not pathfinding and not given a new destination
            print("DEBUGGING, not pathfinding and not given a new destination")
            return None, False
        if (destination.x != None and destination.y != None and self.destination != destination) or self.destination == None: #begin new pathfinding
            print("DEBUGGING, begin new pathfinding")
            self.destination = destination
            self.access_tiles.clear() #empty out all blocked access tiles
            #self.previous_tile = self.current_tile if self.current_tile != None else self.to_tile(self.current_location)
            print(f"DEBUGGING, DESTINATION: {destination}")
            current_room = identify_room(create_ray(self.current_location, self.max_x, self.walls.union(self.doorways))) #identify current room
            destination_room = identify_room(create_ray(self.destination, self.max_x, self.walls.union(self.doorways))) #identify destination room
            self.path_rooms = self.pathfind_rooms(current_room, destination_room) #get list of rooms to pathfind through
            self.path_doorways = self.pathfind_doorways(self.path_rooms) #get list of doorways to pathfind through
            self.path_rooms.insert(0, None) #padding at front so current room isn't popped
            self.path_doorways.append(None)
            self.path_actions = []
            self.path_tiles = []

        if self.debugging == True:
            if self.expected_tile != None:
                self.current_tile = self.expected_tile
            elif self.path_tiles != []:
                self.current_tile = self.path_tiles[0]
            else:
                self.current_tile = self.to_tile(self.current_location)
        else:
            self.current_tile = self.to_tile(self.current_location) #remember the tile we're in currently after making the next action

        #continue with pathfinding to the already selected location
        self.temporary_tiles = set() #reset these
        #self.access_tiles.clear()
        for enemy in self.feature_vector["enemies"]:
            self.temporary_tiles.add(coord_tuple(enemy["x_position"], enemy["y_position"]))
        if self.destination != None and self.reached_destination_tiles(self.current_tile, self.to_tile(self.destination)):
                print("DEBUGGING, already on destination tile, so end pathfinding")
                self.clear_pathfinding()
                return dict({'action': 'nothing'}), False
        if len(self.path_actions) == 0: #current list of actions is empty
            self.path_rooms.pop(0)
            self.set_tile_bias(self.current_location)
            if len(self.path_doorways) > 1: #pathfind to next doorway (if only delimiter is left then don't pathfind to it)
                self.anterior_doorway = self.previous_doorway
                self.previous_doorway = self.path_doorways.pop(0)
                self.path_tiles, self.path_actions = self.pathfind(self.current_location, self.previous_doorway.midpoint())
            else: #should be in the same room as the destination now, generate a path and pop the delimiter
                print("DEBUGGING, should be in same room as the destination now")
                self.path_doorways.pop()
                self.path_tiles, self.path_actions = self.pathfind(self.current_location, self.destination)
            #sometimes our list of actions is empty
            if self.path_tiles == None and self.path_actions == None:
                print("DEBUGGING, NO PATH FOUND, PERHAPS COORDINATES ARE INVALID")
                return dict({'action': 'nothing'}), False
            if len(self.path_tiles) == 0:
                print("DEBUGGING, LIST OF ACTIONS WAS 0, TRYING TO RECALCULATE PATH")
                return dict({'action': 'nothing'}), True
            self.path_tiles.pop(0) #we are already on the first tile so we can pop it
        else:
            pass

        if len(self.path_doorways) == 0 and len(self.path_actions) == 1: #exhausted all doorways and actions
            self.destination = None

        #set up parameter for the next line
        #cur = self.to_tile(self.current_location) if self.debugging == False else self.current_tile
        if self.angle not in [0, 90, 180, 270]:
            return dict({'action': 'turn_right'}), True
        #if self.verify_action_old(cur, self.path_tiles[0], self.path_actions[0]) == True: #if immediate action is valid
        if self.verify_action(self.current_location, self.path_tiles[0], self.path_actions[0], self.path_rooms[0]) == True: #if immediate action is valid
            current_action = self.path_actions.pop(0)
            print(f"DEBUGGING, GETTING EXPECTED TILE, CURRENTLY LEN {len(self.path_tiles)}")
            self.expected_tile = self.path_tiles.pop(0)

            if (self.window != None and self.reading == False and 
                    not (len(self.path_actions) > 0 or len(self.path_doorways) > 0)): #update the gui to allow readinga again?
                self.allow_reading()

            if len(self.path_actions) == 0 and self.previous_doorway != None and len(self.path_doorways) > 0: #if we've finished the official path, begin crossing the doorway
                self.crossing_doorway = True
                closest_point = distance_to_line(self.current_location, self.previous_doorway, True) #get closest point on doorway (we want to move towards it)
                diff_x = closest_point.x - self.current_location.x
                diff_y = closest_point.y - self.current_location.y
                direc = 0 if abs(diff_x) > abs(diff_y) else 1
                if abs(diff_x) > abs(diff_y): #more difference in x direction than y
                    diff_overall = diff_x
                    direc = 0
                else:
                    diff_overall = diff_y
                    direc = 1
                if diff_overall < 0: #if we need to head in negative direction, flip the direction
                    direc += 2
                elif diff_overall == 0: #if we're on the doorway perfectly, then just copy the last action
                    direc = current_action
                print(f"DEBUGGING, STARTING THE CROSS_DOORWAY PROTOCOL")
                temp_tile = self.adjacent_tile(self.to_tile(self.current_location), current_action, int(self.tile_divider)) #factor in current action
                self.path_tiles.append(self.adjacent_tile(temp_tile, direc, 2 * int(self.tile_divider)))
                self.expected_tile = self.path_tiles[0]
                print(f"DEBUGGING, NEWLY EXPECTED TILE: {self.expected_tile}, {len(self.path_actions)}")
                print(f"DEBUGGING, CURRENT TILE: {self.to_tile(self.current_location)}")
                self.path_actions.append(self.true_action(direc)) #move two tiles in the direction of the doorway (will hopefully reach, then pass it onto the other side)
                self.path_actions.append(self.true_action(direc))
                print(f"DEBUGGING, length of path_actions: {len(self.path_actions)}")

                
            #ret = (self.true_action(current_action), len(self.path_actions) > 0 or len(self.path_doorways) > 0)
            ret = (self.true_action(current_action), True)
            print(f"DEBUGGING, returning action {ret}")
            return ret
        else: #action is invalid and as such we need to generate a new path
            #self.destination = None #generate a new path
            #self.access_tiles.add(self.path_tiles[0]) #temporarily block the tile that we couldn't reach
            self.recalculate_path(self.path_tiles[0])

            #if self.window != None and self.reading == False and not (len(self.path_actions) > 0 or len(self.path_doorways) > 0): #gui
            #    self.allow_reading()

            #return self.true_action(self.travel_to(destination)), len(self.path_actions) > 0 or len(self.path_doorways) > 0

            #for debugging, this is a separate variable
            #ret = (self.true_action(self.travel_to(destination)), True)
            return dict({'action': 'nothing'}), True #we know there's more path to go, so we'll return True

    #confirm that the actual action played out as expected and if not we need to make adjustments, should be called after taking an action (right before next action)
    def review_action(self):
        if self.crossing_doorway == True: #if crossing doorway, forget reviewing the action for now
            return True
        if self.current_tile == None: #if no previous move then just return True, everything is good so far (current_tile is the previous tile by now)
            return True
        
        if self.expected_tile == self.to_tile(self.current_location): #we reached the correct tile, no issue
            print("DEBUGGING, reached expected tile correctly")
            return True
        else: #if we weren't able to reach the expected destination, then we need to create a new path
            print("DEBUGGING, didn't reach expected tile, making adjustments")
            print(f"DEBUGGING, expected tile: {self.expected_tile}")
            print(f"DEBUGGING, actual tile: {self.to_tile(self.current_location)}")
            self.recalculate_path(self.expected_tile)
            self.set_tile_bias(self.current_location) #reset the tile bias just in case this was the issue
            return False

    #will ensure the expected move has no problems
    def verify_action_old(self, from_tile, to_tile, action):
        distance = abs(from_tile.x - to_tile.x) if (action == 0 or action == 2) else abs(from_tile.y - to_tile.y)
        for i in range(1, int(distance) + 1): #check every tile to make sure there's nothing blocking
            if self.adjacent_tile(from_tile, action, i) in self.blocked_tiles:
                return False
        return True

    def verify_action(self, current_coords: coord_tuple, new_coords: coord_tuple, action: int, room: Room):
        #for blocked in self.blocked_coords:
        #    if self.reached_destination(blocked, new_coords): #if this coord is close to any blocked location, return False
        #        return False
        current_tile = self.to_tile(current_coords)
        new_tile = self.to_tile(new_coords)
        dist = abs(current_tile.x - new_tile.x) if (action == 0 or action == 2) else abs(current_tile.y - new_tile.y)
        for i in range(1, int(dist) + 1): #check every tile to make sure there's nothing blocking
            if self.adjacent_tile(current_tile, action, i) in self.access_tiles: #used to be blocked_tiles
                print("DEBUGGING, FOUND IN ACCESS_TILES")
                return False
        door_ret = None
        for door in self.doorways: #TODO make these selfs into rooms
            if door != self.previous_doorway and distance_to_line(new_coords, door) < 16: #collision with bad doorway
                if door == self.anterior_doorway:
                    print("DEBUGGING, COLLISION WITH ANTERIOR DOORWAY, NOT SURE HOW TO FIX THIS QUITE YET")
                else:
                    door_ret = False
            #if door == self.previous_doorway and distance_to_line(new_coords, door) < 16: #collision with good doorway
            #    print("DEBUGGING, COLLISION WITH GOOD DOORWAY")
            #    return True
        for wall in self.walls:
            if distance_to_line(new_coords, wall) < 16: #collision with wall
                door_ret = False
        if door_ret == False:
            print("DEBUGGING, COLLISION WITH BAD DOORWAY OR WALL")
            return False
        for enemy in self.enemies:
            if distance(new_coords, coord_tuple(Decimal(enemy["x_position"]), Decimal(enemy["y_position"]))) < 20: #enemies are larger than people
                print("DEBUGGING, COLLISION WITH ENEMY")
                return False
        for obstacle in self.obstacles:
            if distance(new_coords, coord_tuple(Decimal(obstacle["x_position"]), Decimal(obstacle["y_position"]))) < 16:
                print("DEBUGGING, COLLISION WITH OBSTACLE")
                return False
        print("DEBUGGING, NO ISSUE")
        return True

    #given an objective action, convert it into a true action for the agent to take
    def true_action(self, action):
        direction = (int(action) - int(self.angle) / 90 + 4) % 4
        if direction == 0:
            return dict({'action': 'forward'})
        elif direction == 1:
            return dict({'action': 'left'})
        elif direction == 2:
            return dict({'action': 'backward'})
        elif direction == 3:
            return dict({'action': 'right'})
        return direction

    @property
    def tile_size(self):
        return self.unit / self.tile_divider

    @property
    def blocked_tiles(self): #TODO consider doorways either here or elsewhere to boost performance
        return self.wall_tiles.union(self.obstacles_old).union(self.temporary_tiles).union(self.access_tiles)

    #sets tile bias to align the tile plane with the agent (agent lands close to the center of a tile)
    def set_tile_bias(self, coords):
        def formula(coord):
            return (coord + self.tile_size / 2) % self.tile_size
        self.tile_bias = coord_tuple(formula(coords.x), formula(coords.y))

    #converts true coordinates to tile coordinates, also eliminates -0 and converts to normal 0
    def to_tile(self, coords):
        a = (coords.x - self.tile_bias.x) // self.tile_size
        b = (coords.y - self.tile_bias.y) // self.tile_size
        if a == 0:
            a = 0
        if b == 0:
            b = 0
        #return coord_tuple((coords.x - self.tile_bias.x) // self.tile_size, (coords.y - self.tile_bias.y) // self.tile_size)
        return coord_tuple(Decimal(a), Decimal(b))

    #gives adjacent tiles in 'distance' away from the given tile, uses tile coordinates not real coordinates
    def adjacent_tile(self, tile, direction, distance = 1):
        #distance *= int(self.tile_divider)
        if direction == 0:
            return coord_tuple(tile.x + distance, tile.y)
        elif direction == 1:
            return coord_tuple(tile.x, tile.y + distance)
        elif direction == 2:
            return coord_tuple(tile.x - distance, tile.y)
        elif direction == 3:
            return coord_tuple(tile.x, tile.y - distance)

    #depending on the tile divider, will return adjacent tiles where the agent would end up in
    def adjacent_tiles(self, tile, distance = 1): 
        ret = [(self.adjacent_tile(tile, 0, distance), 0), (self.adjacent_tile(tile, 1, distance), 1), 
            (self.adjacent_tile(tile, 2, distance), 2), (self.adjacent_tile(tile, 3, distance), 3)]
        return ret

    #provides all adjacent coordines that our agent can move to from its current position
    def adjacent_coords(self, coord: coord_tuple):
        return [(coord_tuple(coord.x + 16, coord.y), 0), (coord_tuple(coord.x, coord.y + 16), 1),
            (coord_tuple(coord.x - 16, coord.y), 2), (coord_tuple(coord.x, coord.y - 16), 3)]

    #depending on the tile size, we may never reach the exact destination tile, so we must allow extra leeway
    def reached_destination_tiles(self, tile, destination_tile):
        max_distance = self.tile_divider / 2 #the player's radius is 16 units
        return abs(tile.x - destination_tile.x) <= max_distance and abs(tile.y - destination_tile.y) <= max_distance

    #have we reached a certain set of coordinates?
    def reached_destination_coords(self, coord, destination_coord):
        return distance(coord, destination_coord) < 8 #this is our leeway

    #converts walls into tiles so we can avoid them (not enemies nor barriers because those need to be recalculated often)
    def walls_to_tiles(self):
        converted = 0
        tiles = set()
        for line in self.walls:
            converted += 1
            newtiles = set()
            if line.s == enum.vertical: #vertical line
                y_start = min(line.coords[0].y, line.coords[1].y)
                y_end = max(line.coords[0].y, line.coords[1].y)
                length = int((y_end - y_start) // self.tile_size)
                for i in range(length + 1):
                    newtiles.add(self.to_tile(coord_tuple(line.coords[0].x, y_start + i * self.tile_size)))
                if (y_end - y_start) > length:
                    newtiles.add(self.to_tile(coord_tuple(line.coords[0].x, y_end)))
            else: #diagonal or horizontal line
                x_start = min(line.coords[0].x, line.coords[1].x)
                x_end = max(line.coords[0].x, line.coords[1].x)
                length = int((x_end - x_start) // self.tile_size)
                for i in range(length + 1):
                    newtiles.add(self.to_tile(coord_tuple(x_start + i * self.tile_size, line.equation(x = x_start + i * self.tile_size))))
                if (x_end - x_start) > length:
                    newtiles.add(self.to_tile(coord_tuple(x_end, line.equation(x = x_end))))
            #if converted < 10:
            #    print(f"DEBUGGING, line: {line.to_string()}, tiles: {newtiles}")
            tiles = tiles.union(newtiles)

        self.wall_tiles = tiles

    #clear all information regarding pathfinding
    def clear_pathfinding(self):
        self.path_actions = []
        self.path_tiles = []
        self.path_doorways = []
        self.path_rooms = []
        self.destination = None
        self.crossing_doorway = False
        self.previous_doorway = None
        self.anterior_doorway = None
        self.current_tile = None
        self.current_action = None
        self.access_tiles = set()

    #in case we need to recalculate a path, set up the paths to do so (which means resetting certain variables to what they were during the start of this room)
    def recalculate_path(self, blocked_tile = None):
        if blocked_tile != None:
            self.access_tiles.add(blocked_tile)
            print(f"DEBUGGING, added to access_tiles: {blocked_tile}")
            print(f"DEBUGGING, current_tile: {self.to_tile(self.current_location)}")
        self.path_doorways.insert(0, self.previous_doorway)
        self.path_actions.clear()
        self.path_rooms.insert(0, self.path_rooms[0])
        #self.previous_doorway = self.anterior_doorway

    #find a set of instructions from current location to destination location, accept tile coordinates as parameters
    def pathfind(self, start_coords, destination_coords):
        '''
        if a != None and b == None:
            destination = coord_tuple(a[0], a[1])
        else:
            destination = coord_tuple(a, b)
        '''
        #start_tile = self.to_tile(start_location)
        #destination_tile = self.to_tile(destination)
        destination_tile = self.to_tile(destination_coords)
        frontier_coords = [[start_coords]]
        frontier_tiles = [[self.to_tile(start_coords)]] #stores the tiles leading to the frontier
        frontier_actions = [[]] #stores the actions leading to the frontier
        visited = {self.to_tile(start_coords)} #stores all tiles we've visited to ensure there's no overlapping paths
        print(f"DEBUGGING, start_tile: {self.to_tile(start_coords)}")
        print(f"DEBUGGING, destination_tile: {destination_tile}")
        print("DEBUGGING &&&&&&&&&&&&&&&& find a path to destination &&&&&&&&&&&&&&&&&&&&&&&&&&&")
        while (len(frontier_tiles) > 0):
            print(f"DEBUGGING, length of frontier: {len(frontier_coords)}")
            #for tile, action in self.adjacent_tiles(frontier_tiles[0][-1], self.tile_divider):
            for coord, action in self.adjacent_coords(frontier_coords[0][-1]): #for every adjacent coordinate the agent can be at
                tile = self.to_tile(coord)
                print(f"DEBUGGING, handling: {tile}")
                if tile not in visited: #we haven't visited this tile yet
                    print("DEBUGGING, haven't visited")
                    new_path_coords = frontier_coords[0].copy()
                    new_path_coords.append(coord)
                    new_path_tiles = frontier_tiles[0].copy()
                    new_path_tiles.append(tile)
                    new_path_actions = frontier_actions[0].copy()
                    new_path_actions.append(action)
                    if (self.reached_destination_tiles(tile, destination_tile) or 
                            self.reached_destination_coords(coord, destination_coords)): #if we reached the destination
                        print("DEBUGGING, pathfinded to destination")
                        return new_path_tiles, new_path_actions
                    else: #if this isn't the destination tile, want to perform a check so there's no collisions with walls
                        visited.add(tile)
                        #if self.verify_action_old(frontier_tiles[0][-1], tile, action) == True: #confirmed that this move is valid
                        if self.verify_action(frontier_coords[0][-1], coord, action, self.path_rooms[0]) == True: #confirmed that this move is valid
                            print("DEBUGGING, PASSED verification")
                            frontier_coords.append(new_path_coords)
                            frontier_tiles.append(new_path_tiles)
                            frontier_actions.append(new_path_actions)
                        else: #this move is not valid
                            print("DEBUGGING, FAILED verification")
                            pass

                else: #already visited this tile
                    print("DEBUGGING, have visited")
                    pass
            frontier_coords.pop(0)
            frontier_tiles.pop(0)
            frontier_actions.pop(0)
        print("DEBUGGING, NO PATH FOUND TO DESTINATION (maybe the agent isn't in the room it expects to be in?)")
        return None, None

    def pathfind_doorways(self, path_rooms):
        if path_rooms == []:
            print("DEBUGGING, NO PATH_ROOMS, COULD MEAN ALREADY IN THE RIGHT ROOM")
            return []
        ret = []
        for i in range(len(path_rooms) - 1):
            room = path_rooms[i]
            for doorway in room.doorways:
                if room.adjacent_room(doorway) == path_rooms[i + 1]:
                    ret.append(doorway)
        return ret

    #find a set of rooms from starting room to destination room
    def pathfind_rooms(self, start_room, destination_room):
        print(f"DEBUGGING, start_room: {start_room}")
        print(f"DEBUGGING, destination_room: {destination_room}")
        if start_room == destination_room:
            return [destination_room]
        frontier = [[start_room]] #where we grab the next path from, where we store the different paths
        visited = {start_room} #list of rooms we've already visited
        while len(frontier) > 0:
            for room in frontier[0][-1].adjacent_rooms(): #for every room adjacent to the final room in the path
                if room not in visited:
                    new_path = frontier[0].copy()
                    new_path.append(room)
                    if room is destination_room:
                        return new_path
                    else:
                        frontier.append(new_path)
                        visited.add(room)
            frontier.pop(0)
        return []

def create_ray(start_location, max_x, lines):
    ray = Wall((start_location, (max_x, start_location.y)))
    for line in lines: #find all lines that intersect with the ray
        check_intersection(ray, line, enum.update_first)
    return ray
    
#basic discover map function for the start of the program
def discover_map(start_location, ray, direction = 1, side = 1, rotation = 1):
    cur_corner = ray.next_corner(direction, side, rotation, start_location) #get intersection of ray with closest wall
    cur_pointer = cur_corner[0]
    cur_corner = cur_pointer.next_corner(cur_corner[1], cur_corner[2], cur_corner[3], cur_corner[4]) #first corner between two walls
    base_corner = cur_corner #remember this corner, we want to end up here again
    corners = {cur_corner} #we'll return a set of corners

    cur_pointer = cur_corner[0]
    cur_corner = cur_pointer.next_corner(cur_corner[1], cur_corner[2], cur_corner[3], cur_corner[4])
    while cur_corner[4] != base_corner[4]:
        corners.add(cur_corner)
        cur_pointer = cur_corner[0]
        cur_corner = cur_pointer.next_corner(cur_corner[1], cur_corner[2], cur_corner[3], cur_corner[4])
    return corners

#function to circle around the interior of a room, given a point on a doorway (ideally midpoint)
def discover_room(start_location, initial_doorway, room, direction = 1, side = 1, rotation = 1):
    print(f"DEBUGGING, CURRENTLY DISCOVERING ROOM, direction = {direction}, side = {side}, rotation = {rotation}")
    print(f"DEBUGGING, INITIAL {initial_doorway.coords}")
    doorways = set()
    room.doorways.add(initial_doorway)
    cur_corner = initial_doorway.next_corner_doorways(direction, side, rotation, start_location) #end of doorway
    cur_pointer = cur_corner[0] #this should be a wall object
    while cur_pointer != initial_doorway:
        if type(cur_pointer) == Doorway:
            room.doorways.add(cur_pointer)
            doorways.add(cur_pointer)
            #add current room to the doorway
            if cur_corner[2] == -1:
                cur_pointer.room_l = room
            if cur_corner[2] == 1:
                cur_pointer.room_r = room
        elif type(cur_pointer) == Wall:
            room.walls.add(cur_pointer)
        cur_corner = cur_pointer.next_corner_doorways(cur_corner[1], cur_corner[2], cur_corner[3], cur_corner[4])
        cur_pointer = cur_corner[0]
    return room, doorways

#used to find what room the ray is inside
def identify_room(ray, doorway = False):
    start_location = coord_tuple(min(ray.coords[0].x, ray.coords[1].x), ray.coords[0].y)
    #intersection with closest wall
    cur_corner = ray.next_corner_doorways(direction = 1, side = 1, rotation = 1, coords = start_location)
    while type(cur_corner[0]) != Doorway: #keep searching until we find a doorway
        cur_pointer = cur_corner[0]
        cur_corner = cur_pointer.next_corner_doorways(cur_corner[1], cur_corner[2], cur_corner[3], cur_corner[4])
    if doorway == True:
        return cur_corner[0]
    if cur_corner[2] == -1: #if the current side is left, return the left room
        return cur_corner[0].room_l
    else:
        return cur_corner[0].room_r







'''
Know when to give up and also be able to be told to give up
Have a skill return a reward, either when it completes its action or give up
Generate a grid, about 16x16 and navigate similar to wumpus world, around walls and enemies, 
    can recompute if plan is messed with, but downside is calculation could take a very long time depending on map size

Week 2 Milestones:
Continue with navigation agent, algorithm that computes set of actions to get from point a to point b, assuming only walls is fine
Then you can begin considering obstacles, enemies

Week 2 Log:
Can create a performance measure, like Wumpus World had, and then find the most optimal path to reach the destination by running
a search tree.
-Problem: Assuming a location can be reached most efficiently via diagonal moves, because moving diagonally requires an extra move
    to face diagonally, this move will be thrown out in favor of moving a suboptimal amount of distance. In the short term,
    making two unoptimal moves looks better than turning and then moving once diagonally.

Week 3 Milestones:
Define each set of rooms, and which rooms they're connected to, and define a path going from room to room.
Set waypoints at each doorway between two rooms.
Path find from doorway to doorway.

Week 4 Notes:
Make navigation interruptable
Name some functions to reach healthpacks, ammo etc
If can't reach location, return "FAILURE" for now
If no progress after a few moves, do some random moves
    If still can't make progress, fail
    If run into object, return some sort of code, but then work way around
For me: make a list of return values, in a list, and just call that index

Week 5 Notes:
The next move is guaranteed
When moving, want to avoid walls, enemies, traps (might need to move through it in some cases, avoid traps as a parameter?), and obstacles



Vincent Lombardi, contact for deep-q learning agent, message him about implementing ai into the code properly
Compare F (estimated total cost) to the G (actual cost so far)


Future Goals:
Replace numerical values with "enumerators"


Implement into actual VizDoom agent
write it correctly
test on new maps, maybe diagonals too





Future Goals:
implement diagonal movement when ideal over straight movement
respect the player's and other objects' sizes when considering movements
make sure program doesn't break when already on destination
block out any doorways that are irrelevant
change the pathfinding method, consider an A* heuristic
wed 2:00

'''
