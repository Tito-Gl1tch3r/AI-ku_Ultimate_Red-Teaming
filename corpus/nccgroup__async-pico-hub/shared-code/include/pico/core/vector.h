#pragma once
#include <pico/utils.h>
#include <cstddef> // for size_t
#include <new>     // for operator new/delete

namespace pic::priv {
    extern "C" {
        DFR(msvcrt, malloc);
        DFR(msvcrt, memset);
        DFR(msvcrt, free);
    }
}

namespace pic {
    template<typename T>
    class vector {
    private:
        T* data_;
        size_t size_;
        size_t capacity_;

        void reallocate(size_t new_capacity) {
            T* new_data = static_cast<T*>(priv::msvcrt$malloc(sizeof(T) * new_capacity));

            for (size_t i = 0; i < size_; ++i) {
                new (static_cast<void*>(new_data + i)) T(std::move(data_[i]));
                data_[i].~T();
            }
            priv::msvcrt$free(data_);
            data_ = new_data;
            capacity_ = new_capacity;
        }

    public:
        vector() : data_(nullptr), size_(0), capacity_(0) {}
        vector(size_t capacity) : capacity_(capacity), size_(0) {
            data_ = static_cast<T*>(priv::msvcrt$malloc(sizeof(T) * capacity));
            if (!data_) {
                return;
            }
        }

        vector(vector&& other) noexcept
            : data_(other.data_), size_(other.size_), capacity_(other.capacity_)
        {
            other.data_ = nullptr;
            other.size_ = 0;
            other.capacity_ = 0;
        }

        vector(const vector& other)
            : data_(nullptr), size_(0), capacity_(other.capacity_)
        {
            if (other.size_ == 0) return;

            data_ = static_cast<T*>(priv::msvcrt$malloc(sizeof(T) * other.size_));
            if (!data_) {
                return;
            }

            size_ = 0;
            capacity_ = other.size_;

            for (size_t i = 0; i < other.size_; ++i) {
                new (static_cast<void*>(data_ + i)) T(other.data_[i]);
                ++size_;
            }

        }

        ~vector() {
            clear();
            priv::msvcrt$free(data_);
            data_ = nullptr;
            capacity_ = 0;
        }

        void swap(vector& other) noexcept {
            T* tmp_data = data_;
            data_ = other.data_;
            other.data_ = tmp_data;

            size_t tmp_size = size_;
            size_ = other.size_;
            other.size_ = tmp_size;

            size_t tmp_capacity = capacity_;
            capacity_ = other.capacity_;
            other.capacity_ = tmp_capacity;
        }

        vector& operator=(vector other) {
            swap(other);
            return *this;
        }

        void push_back(const T& value) {
            if (size_ >= capacity_) {
                size_t new_capacity = capacity_ == 0 ? 1 : capacity_ * 2;
                reallocate(new_capacity);
            }
            new (static_cast<void*>(data_ + size_)) T(value);
            ++size_;
        }

        void pop_back() {
            if (size_ > 0) {
                --size_;
                data_[size_].~T();
            }
        }

        void clear() {
            for (size_t i = 0; i < size_; ++i) {
                data_[i].~T();
            }
            size_ = 0;
        }

        size_t size() const { return size_; }
        size_t capacity() const { return capacity_; }
        T* data() const { return data_;  }
        // Iterator support
        T* begin() { return data_; }
        T* end() { return data_ + size_; }

        const T* begin() const { return data_; }
        const T* end() const { return data_ + size_; }

        T& operator[](size_t index) { return data_[index]; }
        const T& operator[](size_t index) const { return data_[index]; }
    };

}