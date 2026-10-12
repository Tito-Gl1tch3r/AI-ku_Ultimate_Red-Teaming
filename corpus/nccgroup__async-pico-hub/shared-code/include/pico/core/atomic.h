#pragma once

#include <Windows.h>

namespace pic {

    template<typename T>
    class atomic
    {
    public:

        atomic() = default;

        explicit atomic(T value)
            : value_(static_cast<LONG>(value))
        {
        }

        atomic(const atomic&) = delete;
        atomic& operator=(const atomic&) = delete;

        [[nodiscard]]
        T load() const
        {
            return static_cast<T>(
                InterlockedCompareExchange(
                    const_cast<volatile LONG*>(&value_),
                    0,
                    0));
        }

        void store(T value)
        {
            InterlockedExchange(
                &value_,
                static_cast<LONG>(value));
        }

        [[nodiscard]]
        bool compare_exchange(
            T expected,
            T desired)
        {
            const auto previous =
                InterlockedCompareExchange(
                    &value_,
                    static_cast<LONG>(desired),
                    static_cast<LONG>(expected));

            return previous ==
                static_cast<LONG>(expected);
        }

        bool operator==(T rhs) const
        {
            return load() == rhs;
        }

        T fetch_add(T delta)
        {
            return static_cast<T>(
                InterlockedExchangeAdd(
                    &value_,
                    static_cast<LONG>(delta)));
        }

        T fetch_sub(T delta)
        {
            return fetch_add(-delta);
        }

        atomic& operator=(T value)
        {
            store(value);
            return *this;
        }

    private:

        volatile LONG value_ = 0;
    };

}