#include "eval.hpp"
#include <array>
#include <immintrin.h>
#include <random>
#include <x86intrin.h>

namespace eval2048 {

Move evaluate(const std::array<std::uint16_t, cellCount> rstate, const std::uint8_t type) {
    std::array<std::uint16_t, cellCount> state{[&] {
        std::array<std::uint16_t, cellCount> out{};
        for (std::size_t i{0}; i < cellCount; ++i) {
            out[i] = rstate[i] != 0 ? __bsfd(rstate[i]) : 0;
        }
        return out;
    }()};
    return monteCarlo(State{state});
}

namespace detail {

std::uint32_t xorShift32() {
    static std::random_device rd{};
    static std::uint32_t st{rd()};
    st ^= st << 13;
    st ^= st >> 17;
    st ^= st << 5;
    return st;
}
consteval std::array<std::uint64_t, UINT16_MAX + 1> initRLut() {
    std::array<std::uint64_t, UINT16_MAX + 1> out{};
    for (std::uint64_t e{0}; e < UINT16_MAX + 1; ++e) {
        std::size_t offset{0};
        for (std::uint64_t i{0}; i < cellCount; ++i) {
            if (((e >> i) & 0x1) == 1) {
                out[e] |= i << offset;
                offset += 4;
            }
        }
    }
    return out;
}
constexpr std::array<std::uint64_t, UINT16_MAX + 1> rLut{initRLut()};
State randTile(const State in) {
    const std::uint64_t t{xorShift32() % 10 == 9 ? 2ull : 1ull};
    constexpr std::uint64_t m4{0xCCCC'CCCC'CCCC'CCCC};
    constexpr std::uint64_t m2{0xAAAA'AAAA'AAAA'AAAA};
    constexpr std::uint64_t mLsb{0x1111'1111'1111'1111};
    const std::uint64_t i4{in.data | ((in.data & m4) >> 2)};
    const std::uint64_t r{(~(i4 | ((i4 & m2) >> 1)) & mLsb)};
    if (r == 0) {
        return in;
    }
    const std::uint64_t lutIdx{_pext_u64(r, mLsb)};
    const std::uint64_t cnt{static_cast<std::uint64_t>(_mm_popcnt_u64(lutIdx))};
    const std::uint64_t loc{xorShift32() % cnt};
    return State{in.data | t << (((rLut[lutIdx] >> (loc * 4)) & 0xF) * 4)};
}

} // namespace detail

Move monteCarlo(const State state) {
    static std::array<float, 2> weights{0.5f, 2.0f};
    constexpr std::size_t simulations{200'000};
    constexpr std::array<Move, 4> moves{Move::UP, Move::DOWN, Move::LEFT, Move::RIGHT};
    std::array<std::uint64_t, 4> simCounts{};
    std::array<std::uint64_t, 4> steps{};
    std::array<std::uint64_t, 4> scores{};
    if (state.ended()) {
        return Move::NONE;
    }
    for (std::size_t s{0}; s < simulations; ++s) {
        State st{state};
        Move imv{moves[detail::xorShift32() % 4]};
        State imvst = detail::move(st, imv, scores[static_cast<std::size_t>(imv)]);
        if (st.data == imvst.data) {
            continue;
        }
        imvst = detail::randTile(imvst);
        while (!imvst.ended()) {
            steps[static_cast<std::size_t>(imv)]++;
            Move mv{moves[detail::xorShift32() % 4]};
            State ost{imvst};
            imvst = detail::move(imvst, mv, scores[static_cast<std::size_t>(imv)]);
            if (imvst.data == ost.data) {
                continue;
            }
            imvst = detail::randTile(imvst);
        }
        simCounts[static_cast<std::size_t>(imv)]++;
    };
    float ssc{};
    float sst{};
    std::array<float, 4> avgSc{};
    std::array<float, 4> avgSt{};
    std::array<float, 4> fRate{};
    for (std::size_t i{}; i < 4; ++i) {
        if (simCounts[i] == 0) {
            continue;
        }
        avgSc[i] = static_cast<float>(scores[i]) / simCounts[i];
        avgSt[i] = static_cast<float>(steps[i]) / simCounts[i];
        ssc += avgSc[i];
        sst += avgSt[i];
    }
    for (std::size_t i{}; i < 4; ++i) {
        fRate[i] = (avgSc[i] / ssc) * weights[0] + (avgSt[i] / sst) * weights[1];
    }
    Move mxMv{Move::NONE};
    float mxSc{-1.0f};
    for (std::size_t i{0}; i < 4; ++i) {
        if (fRate[i] > mxSc) {
            mxMv = moves[i];
            mxSc = fRate[i];
        }
    }
    return mxMv;
}

} // namespace eval2048