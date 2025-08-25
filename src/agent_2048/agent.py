import mss
import pyautogui
from pyautogui import leftClick, moveTo
from pydirectinput import press
from mss.base import MSSBase
from cv2.typing import Rect
from time import sleep, perf_counter
from typing import Tuple, List
from .types import Image, Move
from .acv import screen_cap, detect_grid, detect_digits, get_state, Recognizer
from .utils import show_dbg_state
from .evl import get_move


class Agent:
    def __init__(self) -> None:
        self.LATENCY_ACTIVE: float = 0.1
        self.LATENCY_PASSIVE: float = 1.5
        self.sct: MSSBase = mss.mss()
        self.bRect: Rect = (-1, -1, -1, -1)
        self.tracked: bool = False
        self.recognizer: Recognizer = Recognizer()
        self.predicted_state: Tuple[int, ...] = ()
        pyautogui.PAUSE = 0.00
        pyautogui.MINIMUM_SLEEP = 0.00
        pyautogui.MINIMUM_DURATION = 0.00

    def _move(self, move: Move) -> None:
        if not self.tracked:
            return
        x, y, w, h = self.bRect
        moveTo(x + w // 2, y + h // 2, duration=0.0)
        leftClick(duration=0.0)
        match move:
            case Move.UP:
                press("up")
            case Move.DOWN:
                press("down")
            case Move.LEFT:
                press("left")
            case Move.RIGHT:
                press("right")

    def _update_templates(self, nstate: Tuple[int, ...], images: List[Image]) -> None:
        for i, tile in enumerate(nstate):
            # 0 CANNOT be passed to the recognizer. As 0 is an empty tile, and the recognizer treats
            # it as an actual digit to be learned. Bootstrapping already guarantees* that the empty tile
            # will be learned.
            if tile == 0:
                continue
            self.recognizer.add_template(images[i], tile)

    def run(self) -> None:
        while True:
            # Recognize.
            rts: float = perf_counter()
            env: Image = screen_cap(self.sct, self.bRect)  # 30~50ms
            sts1, grid, loc = detect_grid(env)  # 5~7ms
            if not sts1:
                self.bRect = (-1, -1, -1, -1)
                self.tracked = False
                sleep(self.LATENCY_PASSIVE)
                show_dbg_state(None, self, rts, grid, [], False, Move.NULL)
                continue
            # Only reached whenever it acquires the board again.
            if not self.tracked:
                self.bRect = loc
                self.tracked = True
            sts2, digits = detect_digits(grid)
            if not sts2:
                sleep(self.LATENCY_PASSIVE)
                show_dbg_state(None, self, rts, grid, [], False, Move.NULL)
                continue
            self._update_templates(self.predicted_state, digits)
            sts3, state = get_state(digits, self.recognizer)
            if not sts3:
                sleep(self.LATENCY_PASSIVE)
                show_dbg_state(None, self, rts, grid, digits, False, Move.NULL)
                continue
            sts4, move, self.predicted_state = get_move(state)
            if not sts4:
                sleep(self.LATENCY_PASSIVE)
                show_dbg_state(state, self, rts, grid, digits, False, move)
                continue
            show_dbg_state(state, self, rts, grid, digits, True, move)
            sleep(self.LATENCY_ACTIVE)
            self._move(move)
           
