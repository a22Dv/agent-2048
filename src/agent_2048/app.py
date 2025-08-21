import cv2
import time
import numpy as np
import pytweening
import pyautogui as gui
import pydirectinput as pyinput
import random
import os
import ctypes
from pathlib import Path
from typing import Any, Tuple, List
from agent_2048.visual import Visual
from agent_2048.utils import Utils
from enum import Enum


class Action(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

class Algorithm(Enum):
    RANDOM = 0
    EXPECTIMAX = 1
    RULE_BASED = 2

class Application:
    game_state : List[int] = []
    vis : Visual = Visual()
    algo : Algorithm = Algorithm.RULE_BASED
    SCALE_FACTOR : int = 3
    OVERLAY_COLOR : Tuple[int, ...] = (0, 255, 0)
    FONT : int = cv2.FONT_HERSHEY_PLAIN
    FONT_SIZE : float = 0.8
    LATENCY : float = 0.25
    LIB : ctypes.CDLL = ctypes.CDLL(Path(__file__).parent / "eval.dll")

    def __init__(self) -> None:
        self.LIB.expectimax.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self.LIB.expectimax.restype = ctypes.c_int
        self.LIB.rule_based.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self.LIB.rule_based.restype = ctypes.c_int

    def run(self) -> None:

        # Get algorithm
        while True:
            os.system("cls")
            print(f"Options:")
            for s in [f"[{i}] {a}" for i, a in [(0, "RANDOM"), (1, "EXPECTIMAX"), (2, "RULE-BASED")]]:
                print(s)
            user_input: str = input("Enter algorithm no.: ")
            if not user_input.isnumeric():
                continue
            value : int = int(user_input)
            self.algo = Algorithm(value) if value < 3 and value >= 0 else Algorithm.RULE_BASED
            break

        os.system("cls")
        print("Configuration finished. Program is running...")

        # Main loop.
        while True:

            # Capture screen.
            ss: np.ndarray[Any, Any] = Visual.get_rgb(Visual.get_screenshot())
            ss_scaled: np.ndarray[Any, Any] = Visual.img_resize(
                ss, (ss.shape[1] // self.SCALE_FACTOR, ss.shape[0] // self.SCALE_FACTOR)
            )
            ss_canny: np.ndarray[Any, Any] = Visual.apply_canny(ss_scaled, 60, 180)

            # Get board.
            grid: Tuple[List[np.ndarray[Any, Any]], int] = Visual.get_grid_candidates(ss_canny, ss_scaled)
            if len(grid[0]) == 0:
                cv2.destroyAllWindows()
                time.sleep(self.LATENCY)
                continue
            x, y, w, h = cv2.boundingRect(grid[0][grid[1]])
            intersects : List[Tuple[int, int]] = Visual.get_grid_central_intersects(grid[0][grid[1]])
            self.game_state, coordinates = self.vis.extract_state(ss_scaled, intersects, (x, y, w, h))

            # Apply labels.
            cv2.rectangle(ss_scaled, (x, y), (x + w, y + h), self.OVERLAY_COLOR, 1)
            cv2.putText(ss_scaled, "board", (x, y - 10), self.FONT, self.FONT_SIZE, self.OVERLAY_COLOR, 1)
            cv2.putText(ss_scaled, f"BOARD-LOCATION: {(x, y)}", (10, 20), self.FONT, self.FONT_SIZE, self.OVERLAY_COLOR, 1)
            cv2.putText(ss_scaled, f"BOARD-SIZE: {w}x{h}", (10, 40), self.FONT, self.FONT_SIZE, self.OVERLAY_COLOR, 1)
            for inter in intersects:
                cv2.circle(ss_scaled, inter, 1, self.OVERLAY_COLOR, 1)
            for i, (p1, p2) in enumerate(coordinates):
                cv2.rectangle(ss_scaled, p1, p2, self.OVERLAY_COLOR, 1)
                cv2.putText(ss_scaled, f"{self.game_state[i]}", (p1[0] + 3, p1[1] + 15), self.FONT, self.FONT_SIZE, self.OVERLAY_COLOR, 1)
            cv2.imshow("Agent-2048", ss_scaled)
            if Utils.wait("q"):
                break
            time.sleep(self.LATENCY)

            # Move.
            action : Action = self.get_action()
            self.move(action, intersects)
        cv2.destroyAllWindows()

    def get_action(self) -> Action:
        match self.algo:
            case Algorithm.RANDOM:
                return random.choice([Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT])
            case Algorithm.RULE_BASED:
                return Action(self.LIB.rule_based((ctypes.c_int * len(self.game_state))(*self.game_state)))
            case Algorithm.EXPECTIMAX:
                return Action(self.LIB.expectimax((ctypes.c_int * len(self.game_state))(*self.game_state)))
    
    def move(self, action : Action, intersects : List[Tuple[int, int]]) -> None:
        center_intersect : Tuple[int, int] = intersects[4]
        x, y = center_intersect

        # To make movement smooth. Higher minimum duration results in less "posts" to land on.
        # resulting in choppy stuttery movement.
        gui.MINIMUM_DURATION = 0.01
        gui.MINIMUM_SLEEP = 0.01
        gui.moveTo(x * self.SCALE_FACTOR, y * self.SCALE_FACTOR, 0.25, pytweening.easeInOutQuad)
        gui.leftClick()

        # We use pydirectinput instead of pyautogui due to quirks regarding numpads and arrow keys.
        match action:
            case Action.UP: pyinput.press("up")
            case Action.DOWN: pyinput.press("down")
            case Action.RIGHT: pyinput.press("right")
            case Action.LEFT: pyinput.press("left")
