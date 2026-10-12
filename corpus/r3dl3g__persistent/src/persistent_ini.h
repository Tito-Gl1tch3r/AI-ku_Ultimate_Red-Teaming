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
#include <limits>
#include <algorithm>

// --------------------------------------------------------------------------
//
// Project includes
//
#include "persistent_ios.h"


namespace persistent {

  namespace io {

    struct ini_path {

      std::ostream& print (std::ostream& os) const {
        bool first = true;
        for (const auto& p : path) {
          if(first) {
            first = false;
          } else {
            os << '.';
          }
          os << p;
        }
        return os;
      }

      void read_key (std::istream& is) {
        path.clear();
        char next = 0;
        is >> std::ws;
        while (is.good() && (next != '=')) {
          next = is.get();
          std::ostringstream part;
          while (is.good() && (next != '.') && (next != '=')) {
            part.put(next);
            next = is.get();
          }
          std::string key = part.str();
          key.erase(key.find_last_not_of(" \t\n\r") + 1);
          path.push_back(key);
        }
      }

      inline bool match (const ini_path& rhs) const {
        return (this == &rhs) || rhs.path == path;
      }

      inline bool operator== (const ini_path& rhs) const {
        return match(rhs);
      }

      const inline std::string& element (std::size_t i) const {
        return path.at(i);
      }

      inline std::size_t size () const {
        return path.size();
      }

      bool is_parent_of (const ini_path& key) const {
        typedef std::vector<std::string>::const_iterator it;
        const it ke = key.path.end();
        const it pe = path.end();
        it p = path.begin();
        it k = key.path.begin();
        for (; (k < ke) && (p < pe); k++, p++) {
          if (*k != *p) {
            return false;
          }
        }
        return (p == pe) && (k != ke);
      }

      inline void push (const std::string& element) {
        path.push_back(element);
      }

      inline void pop () {
        path.pop_back();
      }

    private:
      std::vector<std::string> path;
    };

    // --------------------------------------------------------------------------
    inline std::ostream& operator<< (std::ostream& os, const ini_path& p) {
      return p.print(os);
    }

    // --------------------------------------------------------------------------
    //
    // specializations for ini formatted ostream
    //
    struct ini_formatter_context {
      ini_formatter_context (std::ostream& os)
        : os(os)
      {}

      ini_path path;

      std::ostream& print_path () {
        return path.print(os) << '=';
      }

      void endl () {
        os << std::endl;
      }

      std::ostream& os;
    };

    template<>
    struct formatter<ini_formatter_context> {

      static void write_property_init (ini_formatter_context& out, const std::string& key) {
        out.path.push(key);
      }

      static void write_property_finish (ini_formatter_context& out, const std::string&) {
        out.path.pop();
      }

      static void write_struct_start (ini_formatter_context& out) {
      }

      static void write_struct_end (ini_formatter_context& out) {
      }

      static void write_members_delemiter (ini_formatter_context& out) {
      }

      static void write_list_element_init (ini_formatter_context& out, int num) {
        out.path.push(std::to_string(num));
      }

      static void write_list_element_finish (ini_formatter_context& out) {
        out.path.pop();
      }

      static void write_list_start (ini_formatter_context& out) {
      }

      static void write_list_end (ini_formatter_context& out) {
      }

      static void write_empty_ptr (ini_formatter_context& out) {
        out.print_path();
        out.endl();
      }
    };

    template<typename T>
    struct write_value_t<ini_formatter_context, T> {
      static void to (ini_formatter_context& out, const T& t) {
        write_value(out.print_path(), t);
        out.endl();
      }
    };

    template<>
    struct write_value_t<ini_formatter_context, const char*> {
      static void to (ini_formatter_context& out, const char* t) {
        out.print_path();
        out.os << t;
        out.endl();
      }
    };

    template<>
    struct write_value_t<ini_formatter_context, const std::string> {
      static void to (ini_formatter_context& out, const std::string& t) {
        out.print_path();
        out.os << t;
        out.endl();
      }
    };

    template<typename T>
    void write_ini (std::ostream& os, const T& t) {
      ini_formatter_context out(os);
      write(out, t);
    }

    // --------------------------------------------------------------------------
    //
    // specializations for ini formatted istream
    //
    struct ini_parser_context {
      ini_parser_context (std::istream& is)
        : is(is)
      {}

      ini_path path;
      ini_path key;
      std::istream& is;

      bool match() const {
        return path == key;
      }

      void skip_to_eol () {
        is.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
      }

      void skip_blank () {
        while (::isblank(is.peek())) {
          is.get();
        }
      }

      auto tellg () const {
        return is.tellg();
      }
    };

    template<>
    struct parser<ini_parser_context> {
      static bool read_list_start (ini_parser_context&) {
        return false;
      }

      static bool read_list_element_init (ini_parser_context&, int) {
        return false;
      }

      static void read_list_element_finish (ini_parser_context&) {}
      static void read_list_end (ini_parser_context&) {}
      static void read_property_init (ini_parser_context&, std::string&) {}
      static void read_property_finish (ini_parser_context&, const std::string&) {}
      static bool read_next_struct_element (ini_parser_context&, std::string& n) {
        n.clear();
        return false;
      }

      static void read_struct_element_finish (ini_parser_context&, const std::string&) {}

      static bool is_ptr_empty (ini_parser_context& in) {
        in.skip_blank();
        const char next = in.is.peek();
        return (next == '\n') || (next == '\r');
      }

    };

    template<typename T>
    struct read_attribute_t<ini_parser_context, T> {
      static bool from (ini_parser_context& in, T& t) {
        in.path.push(get_property_name(t));
        const bool found = read_any(in, access_property_value(t));
        in.path.pop();
        return found;
      }
    };

    template<typename T>
    struct read_setter_t<ini_parser_context, T> {
      static bool from (ini_parser_context& in, T& t) {
        in.path.push(get_property_name(t));
        typename T::type v = {};
        bool found = read_any(in, v);
        if (found) {
          set_property_value(t, std::move(v));
        }
        in.path.pop();
        return found;
      }
    };

    template<typename T, typename V>
    struct read_vector_t<ini_parser_context, T, V> {
      static bool from (ini_parser_context& in, V& v) {
        if (in.path.is_parent_of(in.key)) {
          const std::string& index = in.key.element(in.path.size());
          if (std::all_of(index.begin(), index.end(), ::isdigit)) {
            in.path.push(index);
            const int idx = std::stoi(index);
            if (v.size() < idx + 1) {
              v.resize(idx + 1);
            }
            const bool found = read_any(in, v.at(idx));
            in.path.pop();
            return found;
          }
        }
        return false;
      }
    };

    template<typename T, typename A>
    struct read_array_t<ini_parser_context, T, A> {
      static bool from (ini_parser_context& in, A& a) {
        if (in.path.is_parent_of(in.key)) {
          const std::string& index = in.key.element(in.path.size());
          if (std::all_of(index.begin(), index.end(), ::isdigit)) {
            in.path.push(index);
            const int idx = std::stoi(index);
            const bool found = read_any(in, a.at(idx));
            in.path.pop();
            return found;
          }
        }
        return false;
      }
    };

    template<typename K, typename V, typename C, typename A>
    struct read_map_t<ini_parser_context, K, V, C, A> {
      static bool from (ini_parser_context& in, std::map<K, V, C, A>& m) {
        if (in.path.is_parent_of(in.key)) {
          const std::string& index = in.key.element(in.path.size());
          in.path.push(index);
          const bool found = read_any(in, m[index]);
          in.path.pop();
          return found;
        }
        return false;
      }
    };

    template<typename ... Types>
    struct read_struct_t<ini_parser_context, Types...> {
      static bool from (ini_parser_context& in, std::tuple<Types...>& t) {
        if (in.path.is_parent_of(in.key)) {
          const std::string& index = in.key.element(in.path.size());
          in.path.push(index);
          const bool found = read_attributes_t<sizeof...(Types), ini_parser_context, Types...>::property(in, index, t);
          in.path.pop();
          return found;
        }
        return false;
      }
    };

    template<typename T1, typename T2>
    struct read_pair_t<ini_parser_context, T1, T2> {
      static bool from (ini_parser_context& in, std::pair<T1, T2>& p) {
        if (in.path.is_parent_of(in.key)) {
          const std::string& index = in.key.element(in.path.size());
          if (std::all_of(index.begin(), index.end(), ::isdigit)) {
            in.path.push(index);
            const int idx = std::stoi(index);
            bool found = false;
            switch (idx) {
              case 0: found = read_any(in, p.first); break;
              case 1: found = read_any(in, p.second); break;
              default:
                throw std::runtime_error(msg_fmt() << "Unexpected index " << idx
                                                   << " for pair '" << in.key
                                                   << "' expected [0, 1] at position "
                                                   << in.tellg());
            }
            in.path.pop();
            return found;
          }
        }
        return false;
      }
    };

    template<typename T>
    struct read_value_t<ini_parser_context, T> {
      static bool from (ini_parser_context& in, T& t) {
        if (in.match()) {
          in.is >> std::ws;
          return read_value(in.is, t);
        }
        return false;
      }
    };

    template<>
    struct read_value_t<ini_parser_context, char> {
      static bool from (ini_parser_context& in, char& t) {
        if (in.match()) {
          in.is >> std::ws;
          t = in.is.get();
          return true;
        }
        return false;
      }
    };

    template<>
    struct read_value_t<ini_parser_context, std::string> {
      static bool from (ini_parser_context& in, std::string& t) {
        if (in.match()) {
          char next = in.is.peek();
          if ((next != '\n') && (next != '\r')) {
            std::getline(in.is, t);
            t.erase(std::find_if_not(t.rbegin(), t.rend(), [] (char c) {
              return (c == '\r') || (c == '\n');
            }).base(), t.end());
          }
          return true;
        }
        return false;
      }
    };

    template<typename T>
    bool read_ini (std::istream& is, T& t, const std::string& filename = {}) {
      ini_parser_context in(is);
      is >> std::ws;
      bool found = false;
      int line_no = 1;
      while (is.good()) {
        if (is.peek() == '#') {
          std::string comment;
          std::getline(is, comment);
        }
        in.key.read_key(is);
        if (!read(in, t)) {
          // nothing read -> unknown key
         std::cerr << "Key '";
         in.key.print(std::cerr);
         std::cerr << "' was not found at line " << line_no;
         if (!filename.empty()) {
           std::cerr << " in file '" << filename << "'";
         }
         std::cerr << std::endl;
         in.skip_to_eol();
        } else {
          found = true;
        }
        is >> std::ws;
        ++line_no;
      }
      return found;
    }


  } // namespace io

} // namespace persistent

// --------------------------------------------------------------------------
