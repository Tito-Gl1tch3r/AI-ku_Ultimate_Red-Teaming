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
// Project includes
//
#include "persistent_ios.h"


namespace persistent {

  namespace io {

    // --------------------------------------------------------------------------
    //
    // specializations for json formatted ostream
    //
    struct json_formatter_context : public ios_formatter_context {
      json_formatter_context (std::ostream& os, bool beautify = true)
        : ios_formatter_context(os, beautify)
      {}
    };

    template<>
    struct formatter<json_formatter_context> : public formatter<ios_formatter_context> {

      static void write_property_init (json_formatter_context& out, const std::string& key) {
        out.os << std::quoted(key) << (out.beautify ? ": " : ":");
      }

      static void write_empty_ptr (json_formatter_context& out) {
        out.os << "null";
      }

    };

    template<typename T>
    struct write_value_t<json_formatter_context, T> {
      static void to (json_formatter_context& out, const T& t) {
        out.os << t;
      }
    };

    template<>
    struct write_value_t<json_formatter_context, const std::string> {
      static void to (json_formatter_context& out, const std::string& t) {
        out.os << '"' << t << '"';
      }
    };

    template<>
    struct write_value_t<json_formatter_context, const bool> {
      static void to (json_formatter_context& out, const bool& t) {
        out.os << (t ? "true" : "false");
      }
    };

    template<>
    struct write_value_t<json_formatter_context, const char*> {
      static void to (json_formatter_context& out, const char*& t) {
        out.os << '"' << t << '"';
      }
    };

    template<std::size_t T>
    struct write_value_t<json_formatter_context, const char[T]> {
      static void to (json_formatter_context& out, const char(&t)[T]) {
        out.os << '"' << t << '"';
      }
    };

    template<typename T>
    void inline write_json (std::ostream& os, const T& t, bool beautify = true) {
      json_formatter_context out(os, beautify);
      write_any(out, t);
    }

    // --------------------------------------------------------------------------
    //
    // specializations for json formatted istream
    //
    struct json_parser_context {
      json_parser_context (std::istream& is)
        : is(is)
      {}

      auto tellg () const {
        return is.tellg();
      }

      std::istream& is;
    };

    template<>
    struct parser<json_parser_context> {
      static bool read_list_start (json_parser_context& in) {
        return parser<std::istream>::read_list_start(in.is);
      }

      static bool read_list_element_init (json_parser_context& in, int num) {
        return parser<std::istream>::read_list_element_init(in.is, num);
      }

      static void read_list_element_finish (json_parser_context& in) {
        parser<std::istream>::read_list_element_finish(in.is);
      }

      static void read_list_end (json_parser_context& in) {
        parser<std::istream>::read_list_end(in.is);
      }

      static void read_property_init (json_parser_context& in, std::string& key) {
        in.is >> std::ws >> std::quoted(key);
        parser<std::istream>::read_char(in.is, ':');
      }

      static void read_property_finish (json_parser_context&, const std::string&) {
      }

      static bool read_next_struct_element (json_parser_context& in, std::string& key) {
        char delim = 0;
        in.is >> std::ws >> delim >> std::ws;
        if ((delim != ',') && (delim != '{') && (delim != '}')) {
          throw std::runtime_error(msg_fmt() << "Expected coma ',' or curly bracket '{' or '}' but got '"
                                             << delim << "' for key: '" << key
                                             << "' at position " << in.tellg());
        }
        if (in.is.good() && (delim == '{') && (in.is.peek() == '}')) {
          in.is >> delim;
        }
        if (in.is.good() && (delim != '}')) {
          read_property_init(in, key);
          return true;
        }
        return false;
      }

      static void read_struct_element_finish (json_parser_context&, const std::string&) {}

      static bool is_ptr_empty (json_parser_context& in) {
        in.is >> std::ws;
        if (in.is.peek() != 'n') {
          return false;
        }
        char n, u, l1, l2;
        in.is >> n >> u >> l1 >> l2;
        if ((n != 'n') || (u != 'u') || (l1 != 'l') || (l2 != 'l')) {
          throw std::runtime_error(msg_fmt() << "Expected 'null' but got '" << n << u << l1 << l2
                                             << "' at position " << in.tellg());
        }
        return true;
      }

    };

    template<typename T>
    struct read_value_t<json_parser_context, T> {
      static bool from (json_parser_context& in, T& t) {
        in.is >> std::ws;
        return read_value_t<std::istream, T>::from(in.is, t);
      }
    };

    template<>
    struct read_value_t<json_parser_context, std::string> {
      static bool from (json_parser_context& in, std::string& t) {
        in.is >> std::ws;
        if ((in.is.peek() != '"') && (in.is.peek() != '\'')) {
          return false;
        }
        char delim;
        in.is >> delim;
        return std::getline(in.is, t, delim).good();
      }
    };

    template<>
    struct read_value_t<json_parser_context, bool> {
      static bool from (json_parser_context& in, bool& t) {
        in.is >> std::ws;
        if (in.is.peek() == 't') {
          in.is.ignore(4);
          t = true;
        } else if (in.is.peek() == 'f') {
          in.is.ignore(5);
          t = false;
        } else {
          return false;
        }
        return in.is.good();
      }
    };

    template<typename T>
    inline bool read_json (std::istream& is, T& t) {
      json_parser_context f(is);
      return read(f, t);
    }


  } // namespace io

} // namespace persistent

// --------------------------------------------------------------------------
