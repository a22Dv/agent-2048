#include <array>
#include <cstdint>
#include <random>
#include <thread>
#include <vector>
#include <x86intrin.h>

enum class Move : int { UP, DOWN, LEFT, RIGHT };
constexpr const std::size_t boardSideLength = 4;
constexpr const std::size_t boardCellCount = boardSideLength * boardSideLength;
constexpr const std::size_t byteSize = 8;
constexpr const std::size_t boardIntegerCount = 2;
constexpr const std::size_t boardRowBits = 32;
constexpr const std::size_t lutCellBits = 5;

extern "C" {
__declspec(dllexport) int expectimax(int *state);
__declspec(dllexport) int mcts(int *state);
}

struct alignas(16) Board {
  std::array<std::uint64_t, boardIntegerCount> data{};
  Board() {};
  Board(int *state);
  inline std::uint8_t at(const std::size_t i) const;
  inline std::uint8_t at(const std::size_t x, const std::size_t y) const;
  inline void set(const std::size_t i, const std::uint8_t val);
  inline void set(const std::size_t x, const std::size_t y,
                  const std::uint8_t val);
  inline bool isFull() const;
  inline bool hasEnded() const;
  inline std::uint32_t atRow(const std::size_t r) const;
  inline void setRow(const std::size_t r, const uint32_t v);
  inline void moveUp();
  inline void moveDown();
  inline void moveLeft();
  inline void moveRight();
  inline void transpose();
  bool operator==(const Board &rhs) const { return data == rhs.data; }
};

Board::Board(int *state) {
  for (std::size_t i{0}; i < boardCellCount; ++i) {
    data[i >> 3] |= static_cast<std::uint64_t>(
                        state[i] == 0 ? 0 : (__bsfd(state[i]) & 0xFF))
                    << ((i & 7) * byteSize);
  }
}

inline std::uint8_t Board::at(const std::size_t i) const {
  return static_cast<std::uint8_t>((data[i / 8] >> ((i % 8) * byteSize)) &
                                   0xFF);
}

inline std::uint8_t Board::at(const std::size_t x, const std::size_t y) const {
  return at(y * boardSideLength + x);
}

inline void Board::set(const std::size_t i, const std::uint8_t val) {
  data[i / 8] = (data[i / 8] &
                 ~(static_cast<std::uint64_t>(0xFF) << ((i % 8) * byteSize))) |
                (static_cast<std::uint64_t>(val) << ((i % 8) * byteSize));
}

inline void Board::set(const std::size_t x, const std::size_t y,
                       const std::uint8_t val) {
  return set(y * boardSideLength + x, val);
}

inline bool Board::isFull() const {
  /*
      We smear the bits again and again in halves such that
      any non-zero bit will eventually trigger
      the LSB at the end.
  */
  std::uint64_t nSm0{(data[0] | (data[0] >> 4))};
  std::uint64_t nSm1{(data[1] | (data[1] >> 4))};
  nSm0 |= (nSm0 >> 2);
  nSm1 |= (nSm1 >> 2);
  nSm0 |= (nSm0 >> 1);
  nSm1 |= (nSm1 >> 1);
  return (nSm0 & 0x01010101'01010101) == 0x01010101'01010101 &&
         (nSm1 & 0x01010101'01010101) == 0x01010101'01010101;
};

inline bool Board::hasEnded() const {
  if (!isFull()) {
    return false;
  }
  Board tL{*this}, tR{*this}, tU{*this}, tD{*this};
  tL.moveLeft();
  tR.moveRight();
  tU.moveUp();
  tD.moveDown();
  return tL == tR && tR == tU && tU == tD;
}

inline std::uint32_t Board::atRow(const std::size_t r) const {
  return (data[r >> 1] >> ((r & 1) * boardRowBits)) & UINT32_MAX;
}

inline void Board::setRow(const std::size_t r, const std::uint32_t v) {
  data[r >> 1] &=
      ~(static_cast<std::uint64_t>(UINT32_MAX) << ((r & 1) * boardRowBits));
  data[r >> 1] |= static_cast<std::uint64_t>(v) << ((r & 1) * boardRowBits);
}

inline void slide(std::array<std::uint8_t, boardSideLength> &row) {
  for (std::size_t i{1}; i < boardSideLength; ++i) {
    for (std::size_t j{i}; j > 0; --j) {
      if (row[j - 1] == 0) {
        row[j - 1] = row[j];
        row[j] = 0;
      }
    }
  }
}

inline void merge(std::array<std::uint8_t, boardSideLength> &row) {
  for (std::size_t i{1}; i < boardSideLength; ++i) {
    if (row[i] == row[i - 1] && row[i] != 0) {
      row[i - 1]++; // Increment as we are storing exponents.
      row[i] = 0;
    }
  }
}

inline std::uint32_t convToLut(const std::uint32_t rowIn) {
  std::uint32_t out{};
  out |= rowIn & 0x1F;
  out |= ((rowIn >> byteSize) & 0x1F) << lutCellBits;
  out |= ((rowIn >> (byteSize * 2)) & 0x1F) << (lutCellBits * 2);
  out |= ((rowIn >> (byteSize * 3)) & 0x1F) << (lutCellBits * 3);
  return out;
}

inline std::uint32_t lut(const std::uint32_t in) {
  // Entries required. 32 possible numbers per cell (18 valid), 4 cells each
  // row, 32 ^ 4.
  static const std::vector<std::uint32_t> table{[] {
    std::vector<std::uint32_t> out(32 * 32 * 32 * 32, 0);
    const std::uint32_t maxR{static_cast<std::uint32_t>(out.size())};
    std::array<std::uint8_t, boardSideLength> row{};
    for (std::uint32_t r{0}; r < maxR; ++r) {
      // Unpack the representation.
      for (std::size_t i{0}; i < boardSideLength; ++i) {
        row[i] = (r >> (i * lutCellBits)) & 0x1F;
      }
      slide(row);
      merge(row);
      slide(row);
      // Repack representation.
      std::uint32_t repr{0};
      for (std::size_t i{0}; i < boardSideLength; ++i) {
        repr |= (row[i] & 0x1F) << (i * byteSize);
      }
      out[r] = repr;
    }
    return out;
  }()};
  return table[convToLut(in)];
};

inline std::uint32_t reverseRow(const std::uint32_t r) {
  std::uint32_t out{0};
  out |= (r & 0xFF00'0000) >> (byteSize * 3);
  out |= (r & 0x00FF'0000) >> (byteSize * 1);
  out |= (r & 0x0000'FF00) << (byteSize * 1);
  out |= (r & 0x0000'00FF) << (byteSize * 3);
  return out;
}

inline void Board::transpose() {
  std::uint64_t a{data[0]};
  std::uint64_t b{data[1]};

  /*
    We take the difference of the top and bottom bits, then mask it out.
    Then we make it so that we take the difference of the bottom and top to
    extract the top. Then, we do another shift to the top and extract the bottom
    from the difference. As the top location will still hold the top value then
    and there.
  */

  // We swap 0x000000FF'0000FF00.
  std::uint64_t m{0x00000000'0000FF00};
  std::uint64_t t{(a ^ (a >> 24)) & m};
  a = (a ^ t) ^ (t << 24);

  // We swap 0x00FF0000'FF000000.
  m = 0x00000000'FF000000;
  t = ((b ^ (b >> 24)) & m);
  b = (b ^ t) ^ (t << 24);

  // Swap the 2x2 blocks of a and b. top-right and lower-left.
  m = 0xFFFF0000'FFFF0000;
  t = a & m;
  a = (a & ~m) | ((b << 16) & m);
  b = (b & m) | (t >> 16);

  // We swap 0x00FF0000'FF000000.
  m = 0x00000000'FF000000;
  t = ((a ^ (a >> 24)) & m);
  a = (a ^ t) ^ (t << 24);

  // We swap 0x000000FF'0000FF00.
  m = 0x00000000'0000FF00;
  t = ((b ^ (b >> 24)) & m);
  b = (b ^ t) ^ (t << 24);

  data[0] = a;
  data[1] = b;
}

inline void Board::moveUp() {
  transpose();
  for (std::size_t r{0}; r < boardSideLength; ++r) {
    setRow(r, lut(atRow(r)));
  }
  transpose();
}

inline void Board::moveDown() {
  transpose();
  for (std::size_t r{0}; r < boardSideLength; ++r) {
    setRow(r, reverseRow(lut(reverseRow(atRow(r)))));
  }
  transpose();
}

inline void Board::moveLeft() {
  for (std::size_t r{0}; r < boardSideLength; ++r) {
    setRow(r, lut(atRow(r)));
  }
}

inline void Board::moveRight() {
  for (std::size_t r{0}; r < boardSideLength; ++r) {
    setRow(r, reverseRow(lut(reverseRow(atRow(r)))));
  }
}

int expectimax(int *state) {
  Board board{state};
  /// TODO: Finish implementation.
  return static_cast<int>(Move::UP);
}

constexpr const std::size_t threadCount{4};
constexpr const std::size_t rollouts{5000};

struct McThreadParam {
  Board board{};
  Move initMove{};
  std::minstd_rand &rdEng;
  std::array<std::int32_t, threadCount> &scores;
  McThreadParam();
  McThreadParam(const Board board, const Move initMove,
                std::array<std::int32_t, threadCount> &scores,
                std::minstd_rand &rdEng)
      : board{board}, initMove{initMove}, scores{scores}, rdEng{rdEng} {};
};

void move(Board &b, const Move code) {
  switch (code) {
  case Move::LEFT:
    b.moveLeft();
    break;
  case Move::RIGHT:
    b.moveRight();
    break;
  case Move::UP:
    b.moveUp();
    break;
  case Move::DOWN:
    b.moveDown();
    break;
  }
}

void tile(Board &b, std::uniform_int_distribution<int> &dst0To99,
          std::minstd_rand &eng) {
  const std::uint8_t val{static_cast<std::uint8_t>(dst0To99(eng) < 10 ? 2 : 1)};
  if (b.isFull()) {
    return;
  }
  std::array<std::size_t, boardCellCount> validIdx{};
  std::size_t vIdx{0};
  for (std::size_t i{0}, j{0}; i < boardCellCount; ++i) {
    const bool bV = b.at(i) == 0;
    if (bV) {
      validIdx[vIdx] = i;
      ++vIdx;
    }
  }
  std::size_t loc{static_cast<std::size_t>(dst0To99(eng) % vIdx)};
  b.set(validIdx[loc], val);
}

void mctsThread(McThreadParam param) {
  std::uniform_int_distribution<int> dstMove{0, 3};
  std::uniform_int_distribution<int> dstTile{0, 99};
  std::size_t idx{static_cast<std::size_t>(param.initMove)};
  std::int32_t endSc{-1000};

  Board b{param.board};
  if (b.hasEnded()) {
    param.scores[idx] = INT32_MIN;
    return;
  }
  move(b, param.initMove);
  if (b == param.board) {
    param.scores[idx] = INT32_MIN;
    return;
  }
  for (std::size_t i{0}; i < rollouts; ++i) {
    Board c = b;
    tile(c, dstTile, param.rdEng);
    std::size_t dp{0};
    while (true) {
      move(c, static_cast<Move>(dstMove(param.rdEng)));
      
      if (c.hasEnded()) {
        param.scores[idx] += (endSc + dp);
        break;
      }
      tile(c, dstTile, param.rdEng);
      dp++;
    }
  }
}

int mcts(int *state) {
  /**
    NOTE: This is not Monte Carlo Tree Search. It's currently just Pure Monte
    Carlo. Just to have something working.
  */
  static std::array<std::minstd_rand, threadCount> engines{[] {
    std::array<std::minstd_rand, threadCount> out{};
    std::random_device rd{};
    for (std::minstd_rand &eng : out) {
      eng.seed(rd());
    }
    return out;
  }()};

  Board board{state};
  std::array<std::int32_t, threadCount> scores{};
  std::array<std::thread, threadCount> threads{[&] {
    std::array<std::thread, threadCount> out{};
    int mv{0};
    for (std::thread &th : out) {
      th = std::thread([mv, &board, &scores] {
        mctsThread(
            McThreadParam(board, static_cast<Move>(mv), scores, engines[mv]));
      });
      mv++;
    }
    return out;
  }()};

  // Wait till evaluation finishes.
  for (std::thread &th : threads) {
    th.join();
  }

  std::size_t maxIdx{0};
  std::int32_t maxScore{INT32_MIN};
  for (std::size_t i{0}; i < threadCount; ++i) {
    if (maxScore < scores[i]) {
      maxIdx = i;
      maxScore = scores[i];
    }
  }
  return maxIdx;
}