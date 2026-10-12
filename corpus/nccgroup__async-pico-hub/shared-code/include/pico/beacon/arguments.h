#pragma once

namespace pic {
    enum ArgumentType
    {
        arg_binary,
        arg_int32,
        arg_int16,
        arg_string,
        arg_wstring
    };

    struct BinaryData
    {
        void* data;
        int size;
    };

    struct Argument
    {
        ArgumentType type;

        union
        {
            BinaryData binary;

            int int32_value;
            short int16_value;

            pic::string<char> string_value;
            pic::string<wchar_t> wstring_value;
        };

        Argument()
        {
            type = arg_int32;
            int32_value = 0;
        }

        ~Argument() {
            if (type == arg_string) {
                string_value.~string();
            }
            else if (type == arg_wstring) {
                wstring_value.~string();
            }
        }

        Argument(Argument&& other) noexcept : type(other.type) {
            if (type == arg_int32) {
                int32_value = other.int32_value;
            }
            else if (type == arg_int16) {
                int16_value = other.int16_value;
            }
            else if (type == arg_string) {
                new(&string_value) pic::string<char>(std::move(other.string_value));
            }
            else if (type == arg_wstring) {
                new(&wstring_value) pic::string<wchar_t>(std::move(other.wstring_value));
            }
        }

        Argument(const Argument& other) : type(other.type) {
            if (type == arg_int32) {
                int32_value = other.int32_value;
            }
            else if (type == arg_int16) {
                int16_value = other.int16_value;
            }
            else if (type == arg_string) {
                new(&string_value) pic::string<char>(other.string_value);
            }
            else if (type == arg_wstring) {
                new(&wstring_value) pic::string<wchar_t>(other.wstring_value);
            }
        }

        // primary template — will cause a compile error for unsupported types
        template<ArgumentType arg_type, typename T>
        static Argument make(T value) = delete;

        // specializations
        template<>
        Argument make<arg_int32>(int32_t value)
        {
            Argument arg;
            arg.type = arg_int32;
            arg.int32_value = value;
            return arg;
        }

        template<>
        Argument make<arg_int16>(int16_t value)
        {
            Argument arg;
            arg.type = arg_int16;
            arg.int16_value = value;
            return arg;
        }

        template<>
        Argument make<arg_string>(pic::string<char> value)
        {
            Argument arg;
            arg.type = arg_string;
            new(&arg.string_value) pic::string<char>(std::move(value));
            return arg;
        }

        template<>
        Argument make<arg_wstring>(pic::string<wchar_t> value)
        {
            Argument arg;
            arg.type = arg_wstring;
            new(&arg.wstring_value) pic::string<wchar_t>(std::move(value));
            return arg;
        }

        static Argument make_binary(void* data, int size)
        {
            Argument arg;

            arg.type = arg_binary;

            arg.binary.data = data;
            arg.binary.size = size;

            return arg;
        }
    };
}