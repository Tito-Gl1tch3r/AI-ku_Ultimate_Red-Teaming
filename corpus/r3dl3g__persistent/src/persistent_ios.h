/**
* @copyright (c) 2015-2021 Ing. Buero Rothfuss
*                          Riedlinger Str. 8
*                          70327 Stuttgart
*                          Germany
*                          http://www.rothfuss-web.de
*
* @author    <a href="mailto:armin@rothfuss-web.de">Armin Rothfuss</a>
*
* Project    persistent lib
*
* @brief     C++ struct persistence
*
* @license   MIT license. See accompanying file LICENSE.
*/

#pragma once

// --------------------------------------------------------------------------
//
// Common includes
//
#include <iostream>
#include <iomanip>

// --------------------------------------------------------------------------
//
// Project includes
//
#include "persistent_io.h"


namespace persistent {

  namespace io {

    // --------------------------------------------------------------------------
    //
    // specializations for ostream
    //
    template<>
    struct formatter<std::ostream> {

      static void write_list_element_init (std::ostream& os, int num) {
        if (num) {
          os << ',';
        }
      }

      static void write_list_element_finish (std::ostream&) {}

      static void write_members_delemiter (std::ostream& os) {
        os << ',';
      }

      static void write_list_start (std::ostream& os) {
        os << '[';
      }

      static void write_list_end (std::ostream& os) {
        os << ']';
      }

      static void write_property_init (std::ostream& os, const std::string& key) {
        os << key << ':';
      }

      static void write_property_finish (std::ostream&, const std::string&) {
      }

      static void write_struct_start (std::ostream& os) {
        os << '{';
      }

      static void write_struct_end (std::ostream& os) {
        os << '}';
      }

      static void write_empty_ptr (std::ostream&) {
      }

    };

    template<>
    struct write_value_t<std::ostream, const std::string> {
      static void to (std::ostream& os, const std::string& t) {
        os << std::quoted(t);
      }
    };

    template<>
    struct write_value_t<std::ostream, const char*> {
      static void to (std::ostream& os, const char* t) {
        os << std::quoted(t);
      }
    };

    template<>
    struct write_value_t<std::ostream, const char> {
      static void to (std::ostream& os, const char t) {
        char buffer[2] = { t, 0 };
        os << std::quoted(buffer);
      }
    };

    template<>
    struct write_value_t<std::ostream, const unsigned char> {
      static void to (std::ostream& os, const unsigned char t) {
        os << +t;
      }
    };

    template<>
    struct write_value_t<std::ostream, const signed char> {
      static void to (std::ostream& os, const signed char t) {
        os << +t;
      }
    };

    template<typename T>
    struct write_value_t<std::ostream, T> {
      static void to (std::ostream& os, const T& t) {
        os << t;
      }
    };

    template<typename T>
    void write_stream (std::ostream& os, const T& t) {
      write(os, t);
    }


    // --------------------------------------------------------------------------
    //
    // specializations for formatted ostream
    //
    struct ios_formatter_context {

      ios_formatter_context (std::ostream& os, bool beautify = true)
        : os(os)
        , beautify(beautify)
      {}

      std::ostream& os;

      int deepth = 0;
      bool multi_line = false;
      bool beautify;

      inline ios_formatter_context& inc () {
        ++deepth;
        return *this;
      }

      inline ios_formatter_context& dec () {
        --deepth;
        return *this;
      }

      ios_formatter_context& fill () {
        if (beautify && multi_line) {
          for (int i = 0; i < deepth; ++i) {
            os << "  ";
          }
          multi_line = false;
        }
        return *this;
      }

      ios_formatter_context& endl () {
        if (beautify) {
          os << std::endl;
          multi_line = true;
        }
        return *this;
      }

    };

    template<>
    struct formatter<ios_formatter_context> {

      static void write_list_element_init (ios_formatter_context& out, int num) {
        if (num) {
          out.os << ',';
          out.endl().fill();
        }
      }

      static void write_list_element_finish (ios_formatter_context&) {}

      static void write_members_delemiter (ios_formatter_context& out) {
        out.os << ',';
        out.endl().fill();
      }

      static void write_list_start (ios_formatter_context& out) {
        out.os << "[";
        out.endl().inc().fill();
      }

      static void write_list_end (ios_formatter_context& out) {
        out.endl().dec().fill().os << "]";
      }

      static void write_property_init (ios_formatter_context& out, const std::string& key) {
        out.os << key << ": ";
      }

      static void write_property_finish (ios_formatter_context& out, const std::string&) {
      }

      static void write_struct_start (ios_formatter_context& out) {
        out.os << '{';
        out.endl().inc().fill();
      }

      static void write_struct_end (ios_formatter_context& out) {
        out.endl().dec().fill().os << '}';
      }

      static void write_empty_ptr (ios_formatter_context&) {
      }

    };

    template<typename T>
    struct write_value_t<ios_formatter_context, T> {
      static void to (ios_formatter_context& out, const T& t) {
        write_value(out.os, t);
      }
    };

    template<typename T>
    void write_formatted (std::ostream& os, const T& t, bool beautify = true) {
      ios_formatter_context out(os, beautify);
      write(out, t);
    }

    // --------------------------------------------------------------------------
    //
    // specializations for istream
    //
    template<>
    struct parser<std::istream> {
      static inline bool read_list_start (std::istream& is) {
        is >> std::ws;
        char delim = is.peek();
        if (delim != '[') {
          return false;
        }
        is >> delim;
        return true;
      }

      static inline bool read_list_element_init (std::istream& is, int) {
        is >> std::ws;
        char delim = is.peek();
        return is.good() && (delim != ']');
      }

      static inline void read_list_element_finish (std::istream& is) {
        is >> std::ws;
        char delim = is.peek();
        if ((delim != ',') && (delim != ']')) {
          throw std::runtime_error(msg_fmt() << "Expected coma ',' or array close bracket ']' but got '"
                                             << delim << "' at position " << is.tellg());
        }
        if (delim == ',') {
          is >> delim;
        }
      }

      static inline void read_list_end (std::istream& is) {
        read_char(is >> std::ws, ']');
      }

      static inline void read_property_init (std::istream& is, std::string& key) {
        key.clear();
        std::getline(is >> std::ws, key, ':');
        key.erase(key.find_last_not_of(" \t\n\r") + 1);
      }

      static inline void read_property_finish (std::istream&, const std::string&) {}

      static inline bool read_next_struct_element (std::istream& is, std::string& key) {
        char delim = 0;
        is >> std::ws >> delim >> std::ws;
        if ((delim != ',') && (delim != '{') && (delim != '}')) {
          throw std::runtime_error(msg_fmt() << "Expected coma ',' or curly bracket '{' or '}' but got '"
                                             << delim << "' at position " << is.tellg());
        }
        if (is.good() && (delim == '{') && (is.peek() == '}')) {
          is >> delim;
        }
        if (is.good() && (delim != '}')) {
          read_property_init(is, key);
          return true;
        }
        return false;
      }

      static inline void read_struct_element_finish (std::istream&, std::string&) {}

      static inline char read_char (std::istream& is, const char expected) {
        char delim = 0;
        is >> std::ws >> delim;
        if (delim != expected) {
          throw std::runtime_error(msg_fmt() << "Expected character '" << expected
                                             << "' but got '" << delim
                                             << "' at position " << is.tellg());
        }
        return delim;
      }

      static inline bool is_next_delimiter (std::istream& is) {
        is >> std::ws;
        char delim = is.peek();
        return (delim == '[') || (delim == '{') || (delim == ']') || (delim == '}') || (delim == ':') || (delim == ',');
      }

      static bool is_ptr_empty (std::istream& is) {
        is >> std::ws;
        char delim = is.peek();
        return (delim == ']') || (delim == '}') || (delim == ',');
      }

    };

    template<typename T>
    struct read_value_t<std::istream, T> {
      static bool from (std::istream& is, T& t) {
        if (parser<std::istream>::is_next_delimiter(is)) {
          return false;
        }
        is >> t;
        return true;
      }
    };

    template<>
    struct read_value_t<std::istream, std::string> {
      static bool from (std::istream& is, std::string& t) {
        is >> std::ws;
        if (is.peek() != '"') {
          return false;
        }
        is >> std::quoted(t);
        return true;
      }
    };

    template<>
    struct read_value_t<std::istream, char> {
      static bool from (std::istream& is, char& c) {
        if (parser<std::istream>::is_next_delimiter(is)) {
          return false;
        }
        if (is.peek() != '"') {
          return false;
        }
        std::string t;
        is >> std::quoted(t);
        c = (t.size() > 0 ? static_cast<char>(t[0]) : 0);
        return true;
      }
    };

    template<>
    struct read_value_t<std::istream, unsigned char> {
      static bool from (std::istream& is, unsigned char& t) {
        if (parser<std::istream>::is_next_delimiter(is)) {
          return false;
        }
        int i;
        is >> i;
        t = static_cast<unsigned char>(i);
        return true;
      }
    };

    template<>
    struct read_value_t<std::istream, signed char> {
      static bool from (std::istream& is, signed char& t) {
        if (parser<std::istream>::is_next_delimiter(is)) {
          return false;
        }
        int i;
        is >> i;
        t = static_cast<signed char>(i);
        return true;
      }
    };

    template<typename T>
    inline bool read_stream (std::istream& is, T& t) {
      return read(is, t);
    }


    // --------------------------------------------------------------------------
  } // namespace io

} // namespace persistent
