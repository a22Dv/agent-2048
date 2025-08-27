from __future__ import annotations
import collections.abc
import typing
__all__: list[str] = ['Evaluation', 'Move', 'evaluate']
class Evaluation:
    """
    Members:
    
      AUTO
    
      MC
    
      MCTS
    
      EXPMAX
    """
    AUTO: typing.ClassVar[Evaluation]  # value = <Evaluation.AUTO: 0>
    EXPMAX: typing.ClassVar[Evaluation]  # value = <Evaluation.EXPMAX: 3>
    MC: typing.ClassVar[Evaluation]  # value = <Evaluation.MC: 1>
    MCTS: typing.ClassVar[Evaluation]  # value = <Evaluation.MCTS: 2>
    __members__: typing.ClassVar[dict[str, Evaluation]]  # value = {'AUTO': <Evaluation.AUTO: 0>, 'MC': <Evaluation.MC: 1>, 'MCTS': <Evaluation.MCTS: 2>, 'EXPMAX': <Evaluation.EXPMAX: 3>}
    def __eq__(self, other: typing.Any) -> bool:
        ...
    def __getstate__(self) -> int:
        ...
    def __hash__(self) -> int:
        ...
    def __index__(self) -> int:
        ...
    def __init__(self, value: typing.SupportsInt) -> None:
        ...
    def __int__(self) -> int:
        ...
    def __ne__(self, other: typing.Any) -> bool:
        ...
    def __repr__(self) -> str:
        ...
    def __setstate__(self, state: typing.SupportsInt) -> None:
        ...
    def __str__(self) -> str:
        ...
    @property
    def name(self) -> str:
        ...
    @property
    def value(self) -> int:
        ...
class Move:
    """
    Members:
    
      UP
    
      DOWN
    
      LEFT
    
      RIGHT
    
      NONE
    """
    DOWN: typing.ClassVar[Move]  # value = <Move.DOWN: 1>
    LEFT: typing.ClassVar[Move]  # value = <Move.LEFT: 2>
    NONE: typing.ClassVar[Move]  # value = <Move.NONE: 4>
    RIGHT: typing.ClassVar[Move]  # value = <Move.RIGHT: 3>
    UP: typing.ClassVar[Move]  # value = <Move.UP: 0>
    __members__: typing.ClassVar[dict[str, Move]]  # value = {'UP': <Move.UP: 0>, 'DOWN': <Move.DOWN: 1>, 'LEFT': <Move.LEFT: 2>, 'RIGHT': <Move.RIGHT: 3>, 'NONE': <Move.NONE: 4>}
    def __eq__(self, other: typing.Any) -> bool:
        ...
    def __getstate__(self) -> int:
        ...
    def __hash__(self) -> int:
        ...
    def __index__(self) -> int:
        ...
    def __init__(self, value: typing.SupportsInt) -> None:
        ...
    def __int__(self) -> int:
        ...
    def __ne__(self, other: typing.Any) -> bool:
        ...
    def __repr__(self) -> str:
        ...
    def __setstate__(self, state: typing.SupportsInt) -> None:
        ...
    def __str__(self) -> str:
        ...
    @property
    def name(self) -> str:
        ...
    @property
    def value(self) -> int:
        ...
def evaluate(arg0: typing.Annotated[collections.abc.Sequence[typing.SupportsInt], "FixedSize(16)"], arg1: typing.SupportsInt) -> Move:
    ...
