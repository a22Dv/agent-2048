import cv2
import time
import numpy as np
import pytweening
import pyautogui as gui
import pydirectinput as pyinput
import random
from typing import Any, Tuple, List
from agent_2048.visual import Visual
from agent_2048.utils import Utils
from enum import Enum


class Action(Enum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3

class Application:
    game_state : List[int] = []
    vis : Visual = Visual()
    SCALE_FACTOR : int = 3

    def __init__(self) -> None:
        img = cv2.imread("assets/template_gs.png")
        if img is not None:
            self.template = img
        else:
            raise Exception("INVALID FILE.")

    def run(self) -> None:
        LATENCY: float = 0.25

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
                continue
            x, y, w, h = cv2.boundingRect(grid[0][grid[1]])
            intersects : List[Tuple[int, int]] = Visual.get_grid_central_intersects(grid[0][grid[1]])
            self.game_state, coordinates = self.vis.extract_state(ss_scaled, intersects, (x, y, w, h))

            # Apply labels.
            cv2.drawContours(ss_scaled, grid[0], grid[1], (0, 255, 0), 1)
            cv2.rectangle(ss_scaled, (x, y), (x + w, y + h), (0, 255, 0), 1)
            cv2.putText(ss_scaled, "board", (x, y - 10), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 255, 0), 1)
            for inter in intersects:
                cv2.circle(ss_scaled, inter, 1, (0, 255, 0), 1)
            for i, (p1, p2) in enumerate(coordinates):
                cv2.rectangle(ss_scaled, p1, p2, (0, 255, 0), 1)
                cv2.putText(ss_scaled, f"{self.game_state[i]}", (p1[0] + 3, p1[1] + 15), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 255, 0), 1)
            cv2.imshow("", ss_scaled)
            if Utils.wait("q"):
                break
            time.sleep(LATENCY)

            # Move.
            action : Action = self.get_action()
            self.move(action, intersects)
        cv2.destroyAllWindows()

    def get_action(self) -> Action:

        # Placeholder.
        return random.choice([Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT])
    
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
