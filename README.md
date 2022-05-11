# VizDoom Navigation
Navigation skill for WSU's VizDoom AI (REU)

# Directions
It is advised to place the skills folder next to GUI-Vizdoom.py. Instructions for how to implement the skill are provided, but a drop-in replacement for GUI-Vizdoom.py is provided, which can be used as a reference or simply run as is. The provided GUI-Vizdoom.py allows access to manual input as well as automatic pathfinding. Instructions for these controls are also provided below.

## Interface
First import the necessary class as such:<br><br>
  &nbsp;&nbsp;&nbsp;&nbsp;```from skills.Navigation import Navigator```<br><br>
Initiate a Navigation object, preferably tied to the agent's object properties. Leave the parameters as their defaults.
Every frame, update the navigator's internal features as such:<br><br>
  &nbsp;&nbsp;&nbsp;&nbsp;```navigator.update_features(feature_vector: dict)```<br><br>
Whenever we plan to pathfind or continue pathfinding, run:<br><br>
  &nbsp;&nbsp;&nbsp;&nbsp;```navigator.review_action()```<br><br>
 This will ensure the previous action executed correctly if there was one. If there was any problem, it'll make internal adjustments. Now, to pathfind, choose two coordinates that represent our destination, and pass them to the navigator's travel_to method. It'll return an action and a boolean which lets you know if there are more actions. Here's an example:<br><br>
  &nbsp;&nbsp;&nbsp;&nbsp;```action, more_actions = navigator.travel_to(destination_x, destination_y)```<br><br>
In this case, action is a dict and more_actions is a bool. The x and y coordinates can also be packaged as a tuple and passed as a single parameter. To retrieve the next action, call the same method with the same parameters, and it will return the next move. Once there are no more moves, or it has run into an error (see note 1 below), it'll return False as the second return value.<br><br>
Once we are done pathfinding, especially once a False value is returned for the second return value, it's important to run this command:<br><br>
  &nbsp;&nbsp;&nbsp;&nbsp;```navigator.clear_pathfinding()```<br><br>
This can also be run anytime to cancel all pathfinding operations.

## Manual Input
The default manual controls of VizDoom are retained (wasd for movement and jkl for orientation and shooting), however a few new controls have been added. Pressing p will initiate a request for pathfinding. Upon pressing p, the program will instantly begin waiting for the first coordinate. The program supports negative values. Backspace can also be used to correct any mistakes. Once the coordinate in the terminal looks correct, press enter. Now enter your second coordinate. Press enter when ready to begin pathfinding. The agent will take control and follow the instructions given to it via navigator.travel_to, and once it receives a False as the second return value, it'll give you manual control again.<br>

At any point during this process, you can press o to regain control and cancel all pathfinding or coordinate-entering operations. There is also another button, i, which will execute the navigator.debug_print() method, which can be customized for your use, or can be left alone entirely; this is mostly just for debugging on my end.

# Notes
1. In the future, the return values of navigator.travel_to will be updated from (dict, bool) to (dict, int), where the integer denotes the status of the navigator, whether it be to expect more moves, completed pathfinding, or that it has run into an error. Other than this change, the interface will likely remain the same.

2. There are still bugs, especially when navigating to a location other than (0, 0). The center of the map is currently the most reliable location that can be pathfinded to. This will be looked at soon.

3. Diagonals will be supported soon once a suitable algorithm is found (likely a second breadth-first search that only deals with diagonal movements).
