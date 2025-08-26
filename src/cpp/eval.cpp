#include "eval.hpp"
#include <array>
#include <random>
#include <x86intrin.h>


namespace eval2048 {

Move evaluate(std::array<std::uint16_t, cellCount> rstate, std::uint8_t type) {
    std::array<std::uint16_t, cellCount> state{[&] {
        std::array<std::uint16_t, cellCount> out{};
        for (std::size_t i{0}; i < cellCount; ++i) {
            out[i] = rstate[i] != 0 ? __bsfd(rstate[i]) : 0;
        }
        return out;
    }()};
    switch (static_cast<Evaluation>(type)) {
    case Evaluation::AUTO: {
        const std::uint32_t empty{[&] {
            std::uint32_t emp{};
            for (std::uint16_t v : state) {
                if (v == 0) {
                    emp++;
                }
            }
            return emp;
        }()};
        const float fr{1 - static_cast<float>(empty) / 16};
        if (fr < 0.25) {
            return mc(State{state});
        } else if (fr < 0.75) {
            return mcts(State{state});
        } else {
            return expmax(State{state});
        }
    }
    case Evaluation::MC: return mc(State{state});
    case Evaluation::MCTS: return mcts(State{state});
    case Evaluation::EXPMAX: return expmax(State{state});
    }
}

Move mc(const State state) {
    constexpr std::size_t simulations{1'000'000};
    constexpr std::array<Move, 4> moves{Move::UP, Move::DOWN, Move::LEFT, Move::RIGHT};
    std::array<std::uint64_t, 4> scores{};
    std::random_device rd{};
    std::minstd_rand rand{};
    rand.seed(rd());
    std::uniform_int_distribution<int> dst{0, 4};
    if (state.ended()) {
        return Move::NONE;
    }
    for (std::size_t s{0}; s < simulations; ++s) {;
        State st{state};
        Move imv{moves[dst(rand)]};
        while (true) {
            Move mv{moves[dst(rand)]};
            st = detail::move(st, mv);
            scores[static_cast<std::size_t>(imv)] = 
        }
    };
}

Move mcts(const State state) { return Move::NONE; }

Move expmax(const State state) { return Move::NONE; }

} // namespace eval2048