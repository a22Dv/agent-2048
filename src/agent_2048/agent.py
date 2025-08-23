from time import sleep
from .types import Image
from .acv import screen_cap, detect_grid, detect_digits, get_state
from .utils import dbg_show, dbg_profile

class Agent:
    def __init__(self) -> None:
        self.LATENCY_ACTIVE : float = 0.5
        self.LATENCY_PASSIVE : float = 1.5
        
    def run(self) -> None:
        while True:

            # Recognize.
            env: Image = dbg_profile(screen_cap, 2, True, False) # 30~50ms
            sts1, grid = dbg_profile(detect_grid, env) # 5~7ms
            if not sts1:
                sleep(self.LATENCY_PASSIVE)
                continue
            sts2, digits = dbg_profile(detect_digits, grid)
            if not sts2:
                sleep(self.LATENCY_PASSIVE)
                continue
            sts3, g_state = dbg_profile(get_state, digits)
               
            
            sleep(self.LATENCY_ACTIVE)
