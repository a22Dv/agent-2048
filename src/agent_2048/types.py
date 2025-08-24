import numpy as np
from typing import Any, Tuple
from enum import IntEnum

type Image = np.ndarray[Any, Any]
type Template = Tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]

class Move(IntEnum):
    UP = 0
    DOWN = 1
    LEFT= 2
    RIGHT = 3
    NULL = 4
    