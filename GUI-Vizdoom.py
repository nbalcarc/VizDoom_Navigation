#!/usr/bin/env python3
# ************************************************************************************************ #
# **                                                                                            ** #
# **    AIQ-SAIL-ON Vizdoom GUI                                                                 ** #
# **                                                                                            ** #
# **        Brian L Thomas, 2020                                                                ** #
# **                                                                                            ** #
# **  Tools by the AI Lab - Artificial Intelligence Quotient (AIQ) in the School of Electrical  ** #
# **  Engineering and Computer Science at Washington State University.                          ** #
# **                                                                                            ** #
# **  Copyright Washington State University, 2020                                               ** #
# **  Copyright Brian L. Thomas, 2020                                                           ** #
# **                                                                                            ** #
# **  All rights reserved                                                                       ** #
# **  Modification, distribution, and sale of this work is prohibited without permission from   ** #
# **  Washington State University.                                                              ** #
# **                                                                                            ** #
# **  Contact: Vincent Lombardi (vincent.lombardi@wsu.edu)                                      ** #
# **  Contact: Larry Holder (holder@wsu.edu)                                                    ** #
# **  Contact: Diane J. Cook (djcook@wsu.edu)                                                   ** #
# ************************************************************************************************ #

import copy
import optparse
import queue
import random
import sys
import threading
import time
import numpy as np
import cv2
import string

from objects.TA2_logic import TA2Logic

from skills.Navigation import Navigator

class ThreadedProcessingExample(threading.Thread):
    def __init__(self, processing_object: list, response_queue: queue.Queue):
        threading.Thread.__init__(self)
        self.processing_object = processing_object
        self.response_queue = response_queue
        self.is_done = False
        return

    def run(self):
        """All work tasks should happen or be called from within this function.
        """
        return

    def stop(self):
        self.is_done = True
        return


class TA2Agent(TA2Logic):
    def __init__(self):
        super().__init__()

        self.possible_answers = list()
        self.possible_answers.append(dict({'action': 'nothing'}))
        self.possible_answers.append(dict({'action': 'left'}))
        self.possible_answers.append(dict({'action': 'right'}))
        self.possible_answers.append(dict({'action': 'forward'}))
        self.possible_answers.append(dict({'action': 'backward'}))
        self.possible_answers.append(dict({'action': 'shoot'}))
        self.possible_answers.append(dict({'action': 'turn_left'}))
        self.possible_answers.append(dict({'action': 'turn_right'}))

        '''
        self.keycode = dict({113: 'q', #codes are determined by order in the alphabet, starting at 97 with 'a', likely deprecated
                             119: 'w',
                             97: 'a',
                             115: 's',
                             100: 'd',
                             106: 'j',
                             107: 'k',
                             108: 'l',
                             112: 'p'})
        '''

        self.other_keycodes = dict({
            8: "backspace",
            13: "enter",
            32: "space",
            44: ",",
            45: "-",
            46: ".",
            91: "[",
            93: "]"
            })

        self.key_action = dict({'a': 1,
                                'd': 2,
                                'w': 3,
                                's': 4,
                                'l': 7,
                                'k': 6,
                                'j': 5})

        '''
        -1 no input
        13 enter
        32 space
        44 ,
        45 -
        46 .
        48 0
        49 1
        ...
        57 9
        91 [
        93 ]
        '''

        # This variable can be set to true and the system will attempt to end training at the
        # completion of the current episode, or sooner if possible.
        self.end_training_early = False
        # This variable is checked only during the evaluation phase.  If set to True the system
        # will attempt to cleanly end the experiment at the conclusion of the current episode,
        # or sooner if possible.
        self.end_experiment_early = False

        self.navigator = Navigator() #use the vizdoom pathway and don't use a gui
        self.alphabet = list(string.ascii_lowercase)
        self.human_control = True
        self.walls = None
        self.destination = (0, 0)
        self.pathfinding = False
        return

    def keycode_to_key(self, keycode) -> (str, bool):
        keycode = int(keycode)
        if -1 < keycode - 97 < 26: #alphabet
            return self.alphabet[keycode - 97], False
        elif -1 < keycode - 48 < 10: #number
            return str(keycode - 48), True
        else:
            return self.other_keycodes.get(keycode), keycode == 45 or keycode == 46 #could be None as well

    def user_interface(self, feature_vector: dict) -> dict:
        """Process an episode data instance.

        Parameters
        ----------
        feature_vector : dict
            The dictionary of the feature vector.  Domain specific feature vector formats are
            defined on the github (https://github.com/holderlb/WSU-SAILON-NG).

        Returns
        -------
        dict
            A dictionary of your label prediction of the format {'action': label}.  This is
                strictly enforced and the incorrect format will result in an exception being thrown.
        """
        found_error = False
        # Check for some error conditions and provide helpful feedback.
        if 'enemies' not in feature_vector:
            self.log.error('This does not appear to be a vizdoom feature vector! Did you forget '
                           'to set the correct domain in the agent config file?')
            found_error = True
        image = feature_vector['image']
        if image is None:
            self.log.error('No image received. Did you set use_image to True in TA1.config '
                           'for vizdoom?')
            found_error = True

        # If we found an error, we need to exit.
        if found_error:
            self.log.error('Closing Program')
            sys.exit()

        # Some debugging output.
        self.log.debug('player health: {}'.format(feature_vector['player']['health']))
        self.log.debug('player ammo: {}'.format(feature_vector['player']['ammo']))
        self.log.debug('enemies: {}'.format(feature_vector['enemies']))

        s = 640.0 / image.shape[1]
        dim = (640, int(image.shape[0] * s))

        resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

        cv2.imshow('ViZDoom', resized)

        
        #keycode = cv2.waitKey(int(10 * 1000))
        label_prediction = self.possible_answers[0]
        keycode = cv2.waitKey(10000 if not self.pathfinding else 1)
        '''
        key_pressed = ' '
        if int(keycode) in self.keycode:
            key_pressed = self.keycode[int(keycode)]
        '''
        key_pressed = self.keycode_to_key(keycode)[0]
        self.log.debug('keycode: {}   {}'.format(keycode, key_pressed))
        #print(f'Input: {keycode}, {key_pressed}')

        if key_pressed == 'q': #quit
            sys.exit()
        elif key_pressed in self.key_action: #action button
            act = 0
            act = self.key_action[key_pressed]
            label_prediction = self.possible_answers[act]
        elif key_pressed == "p": #input coordinates
            print("Requested to input coordinates! Press 'o' to cancel. Press 'enter' to enter the second coordinate.") #&&&&&&&&&&&&&&&&&&&&&&&&&&
            coord = ""
            coord1 = ""
            getting = True
            running = True
            while running: #get coords
                newkeycode = cv2.waitKey(10000)
                newkey_pressed, is_num = self.keycode_to_key(newkeycode)
                if is_num:
                    if getting:
                        coord += newkey_pressed
                        print(f"coord: {coord}")
                    else:
                        coord1 += newkey_pressed
                        print(f"coord1: {coord1}")
                elif newkey_pressed == 'enter':
                    if not getting:
                        break
                    else:
                        print("Now inputting second coordinate.")
                        getting = not getting
                elif newkey_pressed == 'o':
                    running = False
                    break
                elif newkey_pressed == 'backspace':
                    if getting:
                        if len(coord) > 0:
                            coord = coord[:-1]
                        print(f"coord: {coord}")
                    else:
                        if len(coord1) > 0:
                            coord1 = coord1[:-1]
                        print(f"coord1: {coord1}")
            if running: #if we exited the loop normally
                try:
                    self.destination = (float(coord), float(coord1))
                    self.pathfinding = True
                except:
                    pass
        elif key_pressed == "o": #cancel pathfinding
            print("Cancelling automatic pathfinding")
            self.pathfinding = False
            self.navigator.clear_pathfinding()
        elif key_pressed == 'i':
                self.navigator.debug_print()
        else: #anything else not covered
            print(f"Unused key: {keycode}, {key_pressed}")


        '''
        if self.human_control: #person controls the environment, just like it is as stock
            act = 0
            if key_pressed in self.key_action:
                act = self.key_action[key_pressed]

            label_prediction = self.possible_answers[act]

        else: #ai controls the environment, but can still use the built-in interface to control bot's navigation
            #time.sleep(0.16) #sleep to achieve realistic fps
            #self.navigator.finalize_window()
            print("DEBUGGING, HERE")
            label_prediction = None
        '''

        return label_prediction

    def experiment_start(self):
        """This function is called when this TA2 has connected to a TA1 and is ready to begin
        the experiment.
        """
        self.log.info('Experiment Start')
        return

    def training_start(self): 
        """This function is called when we are about to begin training on episodes of data in
        your chosen domain.
        """
        self.log.info('Training Start')
        return

    def training_episode_start(self, episode_number: int):
        """This function is called at the start of each training episode, with the current episode
        number (0-based) that you are about to begin.

        Parameters
        ----------
        episode_number : int
            This identifies the 0-based episode number you are about to begin training on.
        """
        self.log.info('Training Episode Start: #{}'.format(episode_number))
        return

    def training_instance(self, feature_vector: dict, feature_label: dict) -> dict:
        """Process a training

        Parameters
        ----------
        feature_vector : dict
            The dictionary of the feature vector.  Domain specific feature vector formats are
            defined on the github (https://github.com/holderlb/WSU-SAILON-NG).
        feature_label : dict
            The dictionary of the label for this feature vector.  Domain specific feature labels
            are defined on the github (https://github.com/holderlb/WSU-SAILON-NG). This will always
            be in the format of {'action': label}.  Some domains that do not need an 'oracle' label
            on training data will receive a valid action chosen at random.

        Returns
        -------
        dict
            A dictionary of your label prediction of the format {'action': label}.  This is
                strictly enforced and the incorrect format will result in an exception being thrown.
        """

        feature_debug = copy.deepcopy(feature_vector)
        feature_debug['image'] = list()
        self.log.debug('Training Instance: feature_vector={}  feature_label={}'.format(
            feature_debug, feature_label))

        '''
        if self.human_control:
            label_prediction = self.user_interface(feature_vector = feature_vector) #get user input
        else:
            self.user_interface(feature_vector = feature_vector) #just sleep for a sec
            self.navigator.update_features(feature_vector)
            self.navigator.review_action()
            label_prediction = self.navigator.travel_to(250, 100)[0]
        '''
        '''
        if self.walls == None:
            self.walls = feature_vector["walls"]
        label_prediction = self.user_interface(feature_vector = feature_vector) #get user input
        if self.pathfinding:
            self.navigator.update_features(feature_vector)
            if self.gave_walls == False:
                self.navigator.set_walls(self.walls)
                self.gave_walls = True
            self.navigator.review_action()
            label_prediction, more_actions = self.navigator.travel_to(self.destination)
            if more_actions == False:
                self.pathfinding = False
                self.navigator.clear_pathfinding()
        '''
        #if self.walls == None:
        #    self.walls = feature_vector["walls"]
        label_prediction = self.user_interface(feature_vector = feature_vector) #get user input
        self.navigator.update_features(feature_vector)
        if self.pathfinding:
            self.navigator.review_action()
            #label_prediction, more_actions = self.navigator.travel_to(self.destination)
            label_prediction, more_actions = self.navigator.travel_to(self.destination[0], self.destination[1])
            if more_actions == False:
                self.pathfinding = False
                self.navigator.clear_pathfinding()

        return label_prediction

    def training_performance(self, performance: float, feedback: dict = None):
        """Provides the current performance on training after each instance.

        Parameters
        ----------
        performance : float
            The normalized performance score.
        feedback : dict, optional
            A dictionary that may provide additional feedback on your prediction based on the
            budget set in the TA1. If there is no feedback, the object will be None.
        """
        self.log.debug('Training Performance: {}'.format(performance))
        return

    def training_episode_end(self, performance: float, feedback: dict = None) -> \
            (float, float, int, dict):
        """Provides the final performance on the training episode and indicates that the training
        episode has ended.

        Parameters
        ----------
        performance : float
            The final normalized performance score of the episode.
        feedback : dict, optional
            A dictionary that may provide additional feedback on your prediction based on the
            budget set in the TA1. If there is no feedback, the object will be None.

        Returns
        -------
        float, float, int, dict
            A float of the probability of there being novelty.
            A float of the probability threshold for this to evaluate as novelty detected.
            Integer representing the predicted novelty level.
            A JSON-valid dict characterizing the novelty.
        """
        self.log.info('Training Episode End: performance={}'.format(performance))

        novelty_probability = random.random()
        novelty_threshold = 0.8
        novelty = 0
        novelty_characterization = dict()

        return novelty_probability, novelty_threshold, novelty, novelty_characterization

    def training_end(self):
        """This function is called when we have completed the training episodes.
        """
        self.log.info('Training End')
        return

    def train_model(self):
        """Train your model here if needed.  If you don't need to train, just leave the function
        empty.  After this completes, the logic calls save_model() and reset_model() as needed
        throughout the rest of the experiment.
        """
        self.log.info('Train the model here if needed.')

        # Simulate training the model by sleeping.
        self.log.info('Simulating training with a 5 second sleep.')
        time.sleep(5)

        return

    def save_model(self, filename: str):
        """Saves the current model in memory to disk so it may be loaded back to memory again.

        Parameters
        ----------
        filename : str
            The filename to save the model to.
        """
        self.log.info('Save model to disk.')
        return

    def reset_model(self, filename: str):
        """Loads the model from disk to memory.

        Parameters
        ----------
        filename : str
            The filename where the model was stored.
        """
        self.log.info('Load model from disk.')
        return

    def trial_start(self, trial_number: int, novelty_description: dict):
        """This is called at the start of a trial with the current 0-based number.

        Parameters
        ----------
        trial_number : int
            This is the 0-based trial number in the novelty group.
        novelty_description : dict
            A dictionary that will have a description of the trial's novelty.
        """
        self.log.info('Trial Start: #{}  novelty_desc: {}'.format(trial_number,
                                                                  str(novelty_description)))

        if len(self.possible_answers) == 0:
            self.possible_answers.append(dict({'action': 'nothing'}))
            self.possible_answers.append(dict({'action': 'left'}))
            self.possible_answers.append(dict({'action': 'right'}))
            self.possible_answers.append(dict({'action': 'forward'}))
            self.possible_answers.append(dict({'action': 'backward'}))
            self.possible_answers.append(dict({'action': 'shoot'}))
            self.possible_answers.append(dict({'action': 'turn_left'}))
            self.possible_answers.append(dict({'action': 'turn_right'}))

        return

    def testing_start(self):
        """This is called after a trial has started but before we begin going through the
        episodes.
        """
        self.log.info('Testing Start')
        return

    def testing_episode_start(self, episode_number: int):
        """This is called at the start of each testing episode in a trial, you are provided the
        0-based episode number.

        Parameters
        ----------
        episode_number : int
            This is the 0-based episode number in the current trial.
        """
        self.log.info('Testing Episode Start: #{}'.format(episode_number))
        return

    def testing_instance(self, feature_vector: dict, novelty_indicator: bool = None) -> dict:
        """Evaluate a testing instance.  Returns the predicted label or action, if you believe
        this episode is novel, and what novelty level you beleive it to be.

        Parameters
        ----------
        feature_vector : dict
            The dictionary containing the feature vector.  Domain specific feature vectors are
            defined on the github (https://github.com/holderlb/WSU-SAILON-NG).
        novelty_indicator : bool, optional
            An indicator about the "big red button".
                - True == novelty has been introduced.
                - False == novelty has not been introduced.
                - None == no information about novelty is being provided.

        Returns
        -------
        dict
            A dictionary of your label prediction of the format {'action': label}.  This is
                strictly enforced and the incorrect format will result in an exception being thrown.
        """
        feature_debug = copy.deepcopy(feature_vector)
        feature_debug['image'] = list()
        self.log.debug('Testing Instance: feature_vector={}, novelty_indicator={}'.format(
            feature_debug, novelty_indicator))

        label_prediction = self.user_interface(feature_vector=feature_vector)

        return label_prediction

    def testing_performance(self, performance: float, feedback: dict = None):
        """Provides the current performance on training after each instance.

        Parameters
        ----------
        performance : float
            The normalized performance score.
        feedback : dict, optional
            A dictionary that may provide additional feedback on your prediction based on the
            budget set in the TA1. If there is no feedback, the object will be None.
        """
        # self.log.debug('Testing Performance: {}'.format(performance))
        return

    def testing_episode_end(self, performance: float, feedback: dict = None) -> \
            (float, float, int, dict):
        """Provides the final performance on the testing episode.

        Parameters
        ----------
        performance : float
            The final normalized performance score of the episode.
        feedback : dict, optional
            A dictionary that may provide additional feedback on your prediction based on the
            budget set in the TA1. If there is no feedback, the object will be None.

        Returns
        -------
        float, float, int, dict
            A float of the probability of there being novelty.
            A float of the probability threshold for this to evaluate as novelty detected.
            Integer representing the predicted novelty level.
            A JSON-valid dict characterizing the novelty.
        """
        self.log.info('Testing Episode End: performance={}'.format(performance))

        novelty_probability = random.random()
        novelty_threshold = 0.8
        novelty = random.choice(list(range(4)))
        novelty_characterization = dict()

        return novelty_probability, novelty_threshold, novelty, novelty_characterization

    def testing_end(self):
        """This is called after the last episode of a trial has completed, before trial_end().
        """
        self.log.info('Testing End')
        return

    def trial_end(self):
        """This is called at the end of each trial.
        """
        self.log.info('Trial End')
        return

    def experiment_end(self):
        """This is called when the experiment is done.
        """
        self.log.info('Experiment End')
        return


if __name__ == "__main__":
    print('controls a:left, d: right, w:forward, s:backward, j:shoot, k:turn left, l:turn right, q:QUIT, any other key: nothing')
    agent = TA2Agent()
    print("DEBUGGING, RUNNING")
    agent.run()
