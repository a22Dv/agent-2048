import numpy as np
from typing import Any, Tuple
from enum import IntEnum

type Image = np.ndarray[Any, Any]
type Template = Tuple[np.ndarray[Any, Any], ...]


class Move(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    NONE = 4


class Symbol(IntEnum):
    S0 = 0
    S1 = 1
    S2 = 2
    S3 = 3
    S4 = 4
    S5 = 5
    S6 = 6
    S7 = 7
    S8 = 8
    S9 = 9
    EMPTY = 10


class CTopology(IntEnum):
    NEXT = 0
    PREVIOUS = 1
    FIRST_CHILD = 2
    PARENT = 3
    NULL = -1


class RectLayout(IntEnum):
    X_COORD = 0
    Y_COORD = 1
    WIDTH = 2
    HEIGHT = 3


class Evaluation(IntEnum):
    AUTO = 0
    MC = 1
    MCTS = 2
    EXPMAX = 3
