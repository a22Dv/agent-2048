#include <algorithm>
#include <array>
#include <cstdint>

extern "C" {

__declspec(dllexport) int expectimax(int *state);

__declspec(dllexport) int rule_based(int *state);
}

enum class Move : int { UP, DOWN, LEFT, RIGHT };

constexpr const std::size_t boardSideLength = 4;
constexpr const std::size_t boardCellCount = boardSideLength * boardSideLength;

int expectimax(int *state) {
  std::array<std::uint32_t, boardCellCount> board{};
  std::copy_n(state, boardCellCount, board.begin());
  return static_cast<int>(Move::UP);
}

int rule_based(int *state) {
  std::array<std::uint32_t, boardCellCount> board{};
  std::copy_n(state, boardCellCount, board.begin());
  return static_cast<int>(Move::DOWN);
}