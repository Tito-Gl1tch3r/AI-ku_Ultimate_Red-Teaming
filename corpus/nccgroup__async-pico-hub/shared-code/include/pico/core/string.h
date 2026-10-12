#pragma once

#include <cstddef>
#include <pico/core/vector.h>

namespace pic {

    template<typename CharT>
    class string {
    private:
        vector<CharT> data_;

    public:
        string() = default;

        // construct from C-string
        string(const CharT* str) {
            append(str);
        }

        string(const string& other) {
            data_ = other.data_;
        }

        // append C-string
        void append(const CharT* str) {
            if (!str) return;

            while (*str != CharT(0)) {
                data_.push_back(*str);
                ++str;
            }
        }

        // append another SimpleString
        void append(const string& other) {
            for (size_t i = 0; i < other.size(); ++i) {
                data_.push_back(other.data_[i]);
            }
        }

        // append single character
        void push_back(CharT ch) {
            data_.push_back(ch);
        }

        // operator += for single character
        string& operator+=(CharT ch) {
            push_back(ch);
            return *this;
        }

        // operator +=
        string& operator+=(const CharT* str) {
            append(str);
            return *this;
        }

        string& operator+=(const string& other) {
            append(other);
            return *this;
        }

        bool operator==(const string& other) const {

            if (other.size() != size()) {
                return false;
            }

            for (unsigned i = 0; i < size(); ++i) {
                if (data_[i] != other.data_[i]) {
                    return false;
                }
            }

            return true;
        }

        // operator +
        string operator+(const string& other) const {
            string result = *this;
            result.append(other);
            return result;
        }

        // access
        CharT& operator[](size_t i) {
            return data_[i];
        }

        const CharT& operator[](size_t i) const {
            return data_[i];
        }

        size_t size() const {
            return data_.size();
        }

        bool empty() const {
            return size() == 0;
        }

        void clear() {
            data_.clear();
        }

        // null-terminated access
        const CharT* c_str() {
            data_.push_back(CharT(0)); // add null terminator
            data_.pop_back();          // keep size unchanged
            return &data_[0];
        }
    };


}