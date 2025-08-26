#pragma once

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <array>
#include <cstdint>

namespace eval2048 {

enum class Evaluation : std::uint8_t { AUTO = 0, MC = 1, MCTS = 2, EXPMAX = 3 };
enum class Move : std::uint8_t {
    UP = 0,
    DOWN = 1,
    LEFT = 2,
    RIGHT = 3,
    NONE = 4,
};
constexpr std::size_t cellCount{16};
constexpr std::size_t lutEntries{UINT16_MAX + 1};

struct LutEntry {
    std::uint16_t score{};
    std::uint16_t out{};
    constexpr LutEntry() {};
    constexpr explicit LutEntry(std::uint16_t sc, std::uint16_t out) : score{sc}, out{out} {};
};

struct State {
    std::uint64_t data{};
    constexpr explicit State() {};
    constexpr explicit State(const std::uint64_t data) : data{data} {};
    constexpr explicit State(const std::array<std::uint16_t, cellCount> &st) {
        for (std::size_t i{0}; i < cellCount; ++i) {
            data |= static_cast<std::uint64_t>(st[i]) << (i * 4);
        }
    }
    constexpr std::uint64_t getDataAsUint() const { return data; }
    constexpr std::array<std::uint16_t, cellCount> getDataAsExpanded() const {
        std::uint64_t m{0xF};
        std::array<std::uint16_t, cellCount> out{};
        for (std::size_t i{0}; i < cellCount; ++i) {
            out[i] = (data >> (i * 4)) & m;
        }
        return out;
    }
    constexpr bool ended() const {
        /*
            Check for empty tiles. Most of the time there will be an empty tile anyways.
            This will provide a quick escape hatch for most cases. Only resorting to
            "slower" methods by checking for possible merges when the board is packed.
            Order is important here. The latter checks will give garbage results if
            T4 is 0 in [T4, T3, T2, T1] per 16-bit word during a XOR op.
        */
        constexpr std::uint64_t m4{0xCCCC'CCCC'CCCC'CCCC};
        constexpr std::uint64_t m2{0xAAAA'AAAA'AAAA'AAAA};
        constexpr std::uint64_t mLsb{0x1111'1111'1111'1111};
        const std::uint64_t i4{data | ((data & m4) >> 2)};
        const std::uint64_t r{(~(i4 | ((i4 & m2) >> 1)) & mLsb)};
        if (r != 0) {
            return false;
        }
        const std::uint64_t diffX{data ^ (data >> 4)};
        const std::uint64_t ix{diffX | ((diffX & m4) >> 2)};
        const std::uint64_t rx{(~(ix | ((ix & m2) >> 1)) & mLsb)};
        if (rx != 0) {
            return false;
        }
        const std::uint64_t diffY{data ^ (data >> 16)};
        const std::uint64_t iy{diffY | ((diffY & m4) >> 2)};
        const std::uint64_t ry{(~(iy | ((iy & m2) >> 1)) & mLsb)};
        return ry == 0;
    }
};

namespace detail {

constexpr State reverse(const State s) {
    constexpr std::uint64_t m8{0x00FF'00FF'00FF'00FF};
    constexpr std::uint64_t m4{0x0F0F'0F0F'0F0F'0F0F};
    const std::uint64_t diff8{((s.data ^ (s.data >> 8)) & m8)};
    const std::uint64_t rv8{(s.data ^ diff8) ^ (diff8 << 8)};
    const std::uint64_t diff4{(rv8 ^ (rv8 >> 4)) & m4};
    const std::uint64_t rv4{(rv8 ^ diff4) ^ (diff4 << 4)};
    return State{rv4};
}

constexpr State transpose(const State s) {
    constexpr std::uint64_t m2x2{0x0000'FF00'0000'FF00};
    constexpr std::uint64_t m16{0x0000'0000'FFFF'0000};
    constexpr std::uint64_t m4{0x00F0'00F0'00F0'00F0};
    const std::uint64_t diff2x2{(s.data ^ (s.data >> 8)) & m2x2};
    const std::uint64_t tr2x2{(s.data ^ diff2x2) ^ (diff2x2 << 8)};
    const std::uint64_t diff16{(tr2x2 ^ (tr2x2 >> 16)) & m16};
    const std::uint64_t tr16{(tr2x2 ^ diff16) ^ (diff16 << 16)};
    const std::uint64_t diff4{(tr16 ^ (tr16 >> 4)) & m4};
    const std::uint64_t tr4{(tr16 ^ diff4) ^ (diff4 << 4)};
    const std::uint64_t diff42x2{(tr4 ^ (tr4 >> 8)) & m2x2};
    const std::uint64_t tr42x2{(tr4 ^ diff42x2) ^ (diff42x2 << 8)};
    return State{tr42x2};
}

constexpr State merge(const State s) {
    std::array<std::uint16_t, cellCount> sa{s.getDataAsExpanded()};
    for (std::size_t i{1}; i < 4; ++i) {
        if (sa[i - 1] == sa[i] && sa[i] != 0) {
            sa[i - 1]++;
            sa[i] = 0;
        }
    }
    return State{sa};
}

constexpr State slide(const State s) {
    // We really only need to iterate the first row as this will only
    // be called by the LUT init function.
    std::array<std::uint16_t, cellCount> sa{s.getDataAsExpanded()};
    for (std::size_t i{1}; i < 4; ++i) {
        for (std::size_t j{i}; j > 0; --j) {
            if (sa[j - 1] == 0) {
                sa[j - 1] = sa[j];
                sa[j] = 0;
            }
        }
    }
    return State{sa};
}

} // namespace detail

constexpr std::array<LutEntry, lutEntries> initLut() {
    std::array<LutEntry, lutEntries> lut{};
    for (std::uint32_t r{0}; r <= UINT16_MAX; ++r) {
        /*
            Since s.data is placed on the lower bits, this can safely
            be cast back to std::uint16_t later.
        */
        State s{static_cast<uint64_t>(r)};
        State ss{detail::slide(s)};
        std::uint16_t sc{};
        std::uint64_t maskSc{0xFF};
        bool tg{false};
        for (std::uint8_t i{0}; i < 3; ++i) {
            if (tg) {
                tg = false;
                maskSc <<= 4;
                continue;
            }
            std::uint64_t mData{(ss.data & maskSc) >> (i * 4)};
            if ((mData & 0xF) == ((mData >> 4) & 0xF) && ((mData & 0xF) != 0)) {
                sc += 0x1 << ((mData & 0xF) + 1);
                tg = true;
            }
            maskSc <<= 4;
        }
        State ms{detail::merge(ss)};
        State sms{detail::slide(ms)};
        lut[r] = LutEntry{sc, static_cast<std::uint16_t>(sms.data)};
    }
    return lut;
}

constexpr std::array<LutEntry, lutEntries> lut{initLut()};

namespace detail {

constexpr State mvL(const State s, ) {

    // TODO: Get score.
    constexpr std::uint64_t m{0xFFFF};
    constexpr std::uint64_t sc{};
    const std::uint64_t mvr1{lut[s.data & m].out};
    sc += lut[s.data & m].score;
    const std::uint64_t mvr2{lut[(s.data >> 16) & m].out};
    sc += lut[(s.data >> 16) & m].score;
    const std::uint64_t mvr3{lut[(s.data >> 32) & m].out};
    sc += lut[(s.data >> 32) & m].score;
    const std::uint64_t mvr4{lut[(s.data >> 48) & m].out};
    sc += lut[(s.data >> 48) & m].score;
    return State{(mvr4 << 48) | (mvr3 << 32) | (mvr2 << 16) | (mvr1)};
}

constexpr State mvR(const State s) { return reverse(mvL(reverse(s))); }

constexpr State mvU(const State s) { return transpose(mvL(transpose(s))); }

constexpr State mvD(const State s) { return transpose(reverse(mvL(reverse(transpose(s))))); }

constexpr State move(const State s, const Move m) {
    switch (m) {
    case Move::LEFT: 
        return mvL(s);
    case Move::RIGHT: 
    return mvR(s);
    case Move::UP: 
    return mvU(s);
    case Move::DOWN: 
    return mvD(s);
    case Move::NONE: 
    return State{0};
    };
}

} // namespace detail

Move evaluate(std::array<std::uint16_t, cellCount> state, std::uint8_t type);
Move mc(const State state);
Move mcts(const State state);
Move expmax(const State state);

} // namespace eval2048