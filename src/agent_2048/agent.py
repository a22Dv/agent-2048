import mss
from mss.base import MSSBase
from cv2.typing import Rect
from time import sleep
from .types import Image
from .acv import screen_cap, detect_grid, detect_digits, get_state
from .utils import dbg_show, dbg_profile, dbg_close


class Agent:
    def __init__(self) -> None:
        self.LATENCY_ACTIVE: float = 0.5
        self.LATENCY_PASSIVE: float = 1.5
        self.sct: MSSBase = mss.mss()
        self.bRect: Rect = (-1, -1, -1, -1)
        self.tracked: bool = False
    def run(self) -> None:
        while True:

            # Recognize.
            env: Image = dbg_profile(
                screen_cap, self.sct, self.bRect
            )  # 30~50ms
            sts1, grid, loc = dbg_profile(detect_grid, env)  # 5~7ms
            if not sts1:
                self.bRect = (-1, -1, -1, -1)
                self.tracked = False
                sleep(self.LATENCY_PASSIVE)
                continue
            # Only reached whenever it acquires the board again. 
            if not self.tracked:
                self.bRect = loc
                self.tracked = True
            sts2, digits = dbg_profile(detect_digits, grid)
            if not sts2:
                sleep(self.LATENCY_PASSIVE)
                continue
            # sts3, g_state = dbg_profile(get_state, digits)
            sleep(self.LATENCY_ACTIVE)
