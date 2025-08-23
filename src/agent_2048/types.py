import numpy as np
from typing import Any, Tuple, Sequence

type Image = np.ndarray[Any, Any]
type Contours = Tuple[Sequence[np.ndarray[Any, Any]], np.ndarray[Any, Any]]
