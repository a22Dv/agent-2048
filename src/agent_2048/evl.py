from typing import Tuple, List
from random import choice
from copy import copy
from .eval import evaluate, Move, Evaluation

GRID_SIDE_LENGTH: int = 4
GRID_CLL_COUNT: int = 16

def _transpose(state: List[int], mv: Move) -> List[int]:
    nstate: List[int] = [0 for _ in state]
    if mv == Move.UP or mv == Move.DOWN:
        for y in range(GRID_SIDE_LENGTH):
            for x in range(GRID_SIDE_LENGTH):
                nstate[x * GRID_SIDE_LENGTH + y] = state[y * GRID_SIDE_LENGTH + x]
        return nstate
    return copy(state)

def _reverse(state: List[int], mv: Move) -> List[int]:
    nstate: List[int] = [0 for _ in state]
    if mv == Move.DOWN or mv == Move.RIGHT:
        for y in range(0, GRID_CLL_COUNT, GRID_SIDE_LENGTH):
            for x in range(GRID_SIDE_LENGTH):
                nstate[y + x] = state[y + (GRID_SIDE_LENGTH - x - 1)]
        return nstate
    return copy(state)

def _slide(state: List[int]) -> List[int]:
    sstate: List[int] = []
    for i in range(GRID_SIDE_LENGTH):
        offset: int =  i * GRID_SIDE_LENGTH
        nonzero: List[int] = [n for n in state[offset: offset + GRID_SIDE_LENGTH] if n != 0]
        slstate: List[int] = [0 for _ in range(GRID_SIDE_LENGTH)]
        slstate[0:len(nonzero)] = nonzero
        sstate.extend(slstate)
    return sstate

def _merge(state: List[int]) -> List[int]:
    nstate: List[int] = copy(state)
    for i in range(0, GRID_CLL_COUNT, 4):
        for j in range(1, GRID_SIDE_LENGTH):
            cIdx: int = i + j - 1
            fIdx: int = i + j
            if nstate[fIdx] == nstate[cIdx] and nstate[fIdx] != 0:
                nstate[cIdx] *= 2
                nstate[fIdx] = 0
    return nstate

def get_nstate(state: Tuple[Tuple[int, float], ...], mv: Move) -> Tuple[int, ...]:
    nstate: List[int] = _reverse(_transpose(list(s[0] for s in state), mv), mv)
    tstate: List[int] = _slide(_merge(_slide(nstate)))
    return tuple(_transpose(_reverse(tstate, mv), mv))


def get_move(
    state: Tuple[Tuple[int, float], ...],
) -> Tuple[bool, Move, Tuple[int, ...]]:
    
    for n, _ in state:
        if (n & (n - 1)) != 0:
            return (False, Move.NONE, ())
    rst: Tuple[int, ...] = tuple([s[0] for s in state])
    mvs: Tuple[Move, ...] = (Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT, Move.NONE)
    states: List[Tuple[int, ...]] = [get_nstate(state, m) for m in mvs]
    mv: Move = Move(evaluate(rst, Evaluation.MC))
    return (True, mv, states[mvs.index(mv)])
    # if vmvs:
    #     rmv: Move = choice(vmvs)
    #     return (True, rmv, states[mvs.index(rmv)])
    # return (False, Move.NONE, ())
    
