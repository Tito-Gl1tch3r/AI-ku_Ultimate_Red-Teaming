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
#include <vector>
#include <map>
#include <sstream>
#include <memory>

// --------------------------------------------------------------------------
//
// Project includes
//
#include "persistent.h"


namespace persistent {

  namespace io {

    struct msg_fmt {
      template <typename T>
      inline msg_fmt& operator<< (T const& value) {
        buffer << value;
        return *this;
      }

      inline operator std::string () const {
        return buffer.str();
      }

    private:
      std::ostringstream buffer;
    };

    // --------------------------------------------------------------------------
    //
    // write
    //
    // --------------------------------------------------------------------------

    /**
     * traits to allow target specific prefix and suffixes.
     */
    template<typename Target>
    struct formatter {
      static void write_list_start (Target&) {}
      static void write_list_element_init (Target&, int num) {}
      static void write_list_element_finish (Target&) {}
      static void write_list_end (Target&) {}

      static void write_members_delemiter (Target&) {}

      static void write_property_init (Target&, const std::string&) {}
      static void write_property_finish (Target&, const std::string&) {}

      static void write_struct_start (Target&) {}
      static void write_struct_end (Target&) {}

      static void write_empty_ptr (Target&) {}
    };

    /**
    * write plain value
    * Allows specialized implementations.
    */
    template<typename Target, typename T>
    struct write_value_t {
      static void to (Target& out, const T& t);
    };

    template<typename Target, typename T>
    void write_value (Target& out, T& t) {
      write_value_t<Target, T>::to(out, t);
    }

    /**
    * write any type
    * type will be detected in later specializations
    */
    template<typename Target, typename T, typename Enable = void>
    struct write_any_t {
      static void to (Target& out, const T& t) {
        write_value(out, t);
      }
    };

    template<typename Target, typename T>
    void write_any (Target& out, const T& t) {
      write_any_t<Target, T>::to(out, t);
    }

    /**
     *  write named property
     */
    template<typename Target, typename T>
    struct write_attribute_t {
      static void to (Target& out, const T& t) {
        formatter<Target>::write_property_init(out, get_property_name(t));
        write_any(out, get_property_value(t));
        formatter<Target>::write_property_finish(out, get_property_name(t));
      }
    };

    template<typename Target, typename T>
    void write_attribute (Target& out, const T& t) {
      write_attribute_t<Target, T>::to(out, t);
    }

    /// write vector and array values
    template<typename Target, typename T, typename V>
    struct writeList_t {
      static void to (Target& out, const V& v) {
        formatter<Target>::write_list_start(out);
        int num = 0;
        for (const T& t : v) {
          formatter<Target>::write_list_element_init(out, num++);
          write_any(out, t);
          formatter<Target>::write_list_element_finish(out);
        }
        formatter<Target>::write_list_end(out);
      }
    };

    /// write vector values
    template<typename Target, typename T, typename V>
    struct write_vector_t {
      static void to (Target& out, const V& t) {
        writeList_t<Target, T, V>::to(out, t);
      }
    };

    template<typename Target, typename T, typename A>
    void write_vector (Target& out, const std::vector<T, A>& t) {
      write_vector_t<Target, T, std::vector<T, A>>::to(out, t);
    }

    /// write array values
    template<typename Target, typename T, size_t S>
    struct write_array_t {
      static void to (Target& out, const std::array<T, S>& t) {
        writeList_t<Target, T, std::array<T, S>>::to(out, t);
      }
    };

    template<typename Target, typename T, size_t S>
    void write_array (Target& out, const std::array<T, S>& t) {
      write_array_t<Target, T, S>::to(out, t);
    }

    /// write key/value pair map
    template<typename Target, typename K, typename V, typename C, typename A>
    struct write_map_t {
      static void to (Target& out, const std::map<K, V, C, A>& m) {
        formatter<Target>::write_struct_start(out);
        bool first = true;
        for (const auto& e : m) {
          if (first) {
            first = false;
          } else {
            formatter<Target>::write_members_delemiter(out);
          }
          auto key = convert<K>::key_to_string(e.first);
          formatter<Target>::write_property_init(out, key);
          write_any(out, e.second);
          formatter<Target>::write_property_finish(out, key);
        }
        formatter<Target>::write_struct_end(out);
      }
    };

    template<typename Target, typename K, typename V, typename C, typename A>
    void write_map (Target& out, const std::map<K, V, C, A>& m) {
      write_map_t<Target, K, V, C, A>::to(out, m);
    }

    /**
    * write recursive all elements of a tuple
    */
    template<std::size_t I, typename Target, typename... Types>
    struct write_attributes_t {
      static void to (Target& out, std::tuple<const Types...> const& t) {
        write_attributes_t<I - 1, Target, Types...>::to(out, t);
        formatter<Target>::write_members_delemiter(out);
        const auto& m = std::get<I>(t);
        write_any(out, m);
      }
    };

    /// end recursion at 0 elemnt.
    template<typename Target, typename... Types>
    struct write_attributes_t<0, Target, Types...> {
      static void to (Target& out, std::tuple<const Types...> const& t) {
        const auto& m = std::get<0>(t);
        write_any(out, m);
      }
    };

    /// write struct
    template<typename Target, typename ... Types>
    struct write_struct_t {
      static void to (Target& out, const std::tuple<Types...>& t) {
        formatter<Target>::write_struct_start(out);
        write_attributes_t<(sizeof...(Types)) - 1, Target, Types...>::to(out, t);
        formatter<Target>::write_struct_end(out);
      }
    };

    template<typename Target, typename... Types>
    void write_struct (Target& out, const std::tuple<Types...>& t) {
      write_struct_t<Target, Types...>::to(out, t);
    }

    /// write shared values
    template<typename Target, typename T>
    struct write_shared_t {
      static void to (Target& out, const std::shared_ptr<T>& t) {
        if (t) {
          write_any_t<Target, T>::to(out, *t.get());
        } else {
          formatter<Target>::write_empty_ptr(out);
        }
      }
    };

    template<typename Target, typename T>
    void write_shared (Target& out, const std::shared_ptr<T>& t) {
      write_shared_t<Target, T>::to(out, t);
    }

    /// write unique ptr
    template<typename Target, typename T, typename D>
    struct write_unique_t {
      static void to (Target& out, const std::unique_ptr<T, D>& t) {
        if (t) {
          write_any_t<Target, T>::to(out, *t.get());
        } else {
          formatter<Target>::write_empty_ptr(out);
        }
      }
    };

    template<typename Target, typename T, typename D>
    void write_unique (Target& out, const std::unique_ptr<T, D>& t) {
      write_unique_t<Target, T, D>::to(out, t);
    }

    /**
    * write recursive all elements of a tuple
    */
    template<std::size_t I, typename Target, typename... Types>
    struct write_tuple_element_t {
      static void to (Target& out, std::tuple<const Types...> const& t) {
        write_tuple_element_t<I - 1, Target, Types...>::to(out, t);
        formatter<Target>::write_members_delemiter(out);
        formatter<Target>::write_property_init(out, std::to_string(I));
        write_any(out, std::get<I>(t));
        formatter<Target>::write_property_finish(out, std::to_string(I));
      }
    };

    /// end recursion at 0 elemnt.
    template<typename Target, typename... Types>
    struct write_tuple_element_t<0, Target, Types...> {
      static void to (Target& out, std::tuple<const Types...> const& t) {
        formatter<Target>::write_property_init(out, "0");
        write_any(out, std::get<0>(t));
        formatter<Target>::write_property_finish(out, "0");
      }
    };

    template<typename Target, typename... Types>
    struct write_tuple_t {
      static void to (Target& out, const std::tuple<Types...>& t) {
        formatter<Target>::write_struct_start(out);
        write_tuple_element_t<(sizeof...(Types)) - 1, Target, Types...>::to(out, t);
        formatter<Target>::write_struct_end(out);
      }
    };

    template<typename Target, typename... Types>
    void write_tuple (Target& out, const std::tuple<Types...>& t) {
      write_tuple_t<Target, Types...>::to(out, t);
    }

    /// write pair
    template<typename Target, typename T1, typename T2>
    struct write_pair_t {
      static void to (Target& out, const std::pair<T1, T2>& t) {
        formatter<Target>::write_list_start(out);
        formatter<Target>::write_list_element_init(out, 0);
        write_any(out, t.first);
        formatter<Target>::write_list_element_finish(out);
        formatter<Target>::write_list_element_init(out, 1);
        write_any(out, t.second);
        formatter<Target>::write_list_element_finish(out);
        formatter<Target>::write_list_end(out);
      }
    };

    template<typename Target, typename T1, typename T2>
    void write_pair (Target& out, const std::pair<T1, T2>& t) {
      write_pair_t<Target, T1, T2>::to(out, t);
    }

    /// detect attribute
    template<typename Target, typename T>
    struct write_any_t<Target, detail::attribute<T>> {
      static void to (Target& out, const detail::attribute<T>& t) {
        write_attribute(out, t);
      }
    };

    /// detect getter
    template<typename Target, typename T>
    struct write_any_t<Target, detail::getter<T>> {
      static void to (Target& out, const detail::getter<T>& t) {
        write_attribute(out, t);
      }
    };

    /// detect vector
    template<typename Target, typename T, typename A>
    struct write_any_t<Target, std::vector<T, A>> {
      static void to (Target& out, const std::vector<T, A>& t) {
        write_vector(out, t);
      }
    };

    /// detect array
    template<typename Target, typename T, std::size_t S>
    struct write_any_t<Target, std::array<T, S>> {
      static void to (Target& out, const std::array<T, S>& t) {
        write_array(out, t);
      }
    };

    /// detect map
    template<typename Target, typename K, typename V, typename C, typename A>
    struct write_any_t<Target, std::map<K, V, C, A>> {
      static void to (Target& out, const std::map<K, V, C, A>& m) {
        write_map(out, m);
      }
    };

    /// detect struct
    template<typename Target, typename T>
    struct write_any_t<Target, T, typename std::enable_if<is_persistent<T>::value>::type> {
      static void to (Target& out, const T& t) {
        write_struct(out, persistent::attributes(t));
      }
    };

    /// detect shared
    template<typename Target, typename T>
    struct write_any_t<Target, std::shared_ptr<T>> {
      static void to (Target& out, const std::shared_ptr<T>& t) {
        write_shared(out, t);
      }
    };

    /// detect unique
    template<typename Target, typename T, typename D>
    struct write_any_t<Target, std::unique_ptr<T, D>> {
      static void to (Target& out, const std::unique_ptr<T, D>& t) {
        write_unique(out, t);
      }
    };

    /// detect tuple
    template<typename Target, typename... Types>
    struct write_any_t<Target, std::tuple<Types...>> {
      static void to (Target& out, const std::tuple<Types...>& t) {
        write_tuple(out, t);
      }
    };

    /// detect pair
    template<typename Target, typename T1, typename T2>
    struct write_any_t<Target, std::pair<T1, T2>> {
      static void to (Target& out, const std::pair<T1, T2>& t) {
        write_pair(out, t);
      }
    };

    /// convenience helper
    template<typename Target, typename T>
    void inline write (Target& out, const T& t) {
      write_any(out, t);
    }

    // --------------------------------------------------------------------------
    //
    // read
    //
    // --------------------------------------------------------------------------

    /**
     * traits to allow source specific parsing.
     */
    template<typename Source>
    struct parser {
      static bool read_list_start (Source&) { return false; }
      static bool read_list_element_init (Source&, int) { return true; }
      static void read_list_element_finish (Source&) {}
      static void read_list_end (Source&) {}

      static void read_property_init (Source&, std::string&) {}
      static void read_property_finish (Source&, const std::string&) {}

      static bool read_next_struct_element (Source&, std::string& n) { 
        n.clear();
        return true;
      }
      static void read_struct_element_finish (Source&, const std::string&) {}

      static bool is_ptr_empty (Source&) { return true; }
    };

    /// read value
    template<typename Source, typename T>
    struct read_value_t {
      static bool from (Source& in, T& t);
    };

    template<typename Source, typename T>
    inline bool read_value (Source& in, T& t) {
      return read_value_t<Source, T>::from(in, t);
    }

    /// read property
    template<typename Source, typename T>
    struct read_property_t {
      static bool from (Source& in, T& t) {
        return read_value(in, t);
      }
    };

    /**
    * read any type
    * type will be detected in later specializations
    */
    template<typename Source, typename T, typename Enable = void>
    struct read_any_t {
      static inline bool from (Source& in, T& t) {
        return read_value(in, t);
      }
    };

    template<typename Source, typename T>
    inline bool read_any (Source& in, T& t) {
      return read_any_t<Source, T>::from(in, t);
    }

    /// detect attribute property
    template<typename Source, typename T>
    struct read_property_t<Source, detail::attribute<T>> {
      static inline bool from (Source& in, detail::attribute<T>& t) {
        return read_any(in, access_property_value(t));
      }
    };

    /// detect setter property
    template<typename Source, typename T>
    struct read_property_t<Source, detail::setter<T>> {
      static inline bool from (Source& in, detail::setter<T>& t) {
        std::remove_const_t<std::remove_reference_t<T>> v = {};
        if (read_any(in, v)) {
          set_property_value(t, std::move(v));
          return true;
        }
        return false;
      }
    };

    template<typename Source, typename T>
    inline bool read_property (Source& in, T& t) {
      return read_property_t<Source, T>::from(in, t);
    }

    /// read vector
    template<typename Source, typename T, typename V>
    struct read_vector_t {
      static bool from (Source& in, V& v) {
        if (!parser<Source>::read_list_start(in)) {
          return false;
        }
        int num = 0;
        bool found = false;
        while (parser<Source>::read_list_element_init(in, num++)) {
          T t;
          found |= read_any(in, t);
          v.push_back(std::move(t));
          parser<Source>::read_list_element_finish(in);
        }
        parser<Source>::read_list_end(in);
        return found;
      }
    };

    template<typename Source, typename T, typename A>
    inline bool read_vector (Source& in, std::vector<T, A>& t) {
      return read_vector_t<Source, T, std::vector<T, A>>::from(in, t);
    }

    /// read array
    template<typename Source, typename T, typename A>
    struct read_array_t {
      static bool from (Source& in, A& a) {
        if (!parser<Source>::read_list_start(in)) {
          return false;
        }
        int num = 0;
        bool found = false;
        for (T& e : a) {
          parser<Source>::read_list_element_init(in, num++);
          found |= read_any(in, e);
          parser<Source>::read_list_element_finish(in);
        }
        parser<Source>::read_list_end(in);
        return found;
      }
    };

    template<typename Source, typename T, std::size_t S>
    inline bool read_array (Source& in, std::array<T, S>& t) {
      return read_array_t<Source, T, std::array<T, S>>::from(in, t);
    }

    /// read map
    template<typename Source, typename K, typename V, typename C, typename A>
    struct read_map_t {
      static bool from (Source& in, std::map<K, V, C, A>& m) {
        std::string name;
        bool found = false;
        try {
          while (parser<Source>::read_next_struct_element(in, name)) {
            found |= read_any<Source, V>(in, m[convert<K>::string_to_key(name)]);
            parser<Source>::read_struct_element_finish(in, name);
          }
        } catch (std::exception& ex) {
          throw std::runtime_error(msg_fmt() << ex.what() << " in map '" << typeid(m).name()
                                             << "' after key '" << name 
                                             << "' at position " << in.tellg());
        }
        return found;
      }
    };

    template<typename Source, typename K, typename V, typename C, typename A>
    inline bool read_map (Source& in, std::map<K, V, C, A>& m) {
      return read_map_t<Source, K, V, C, A>::from(in, m);
    }

    /// read element with name of a tuple
    template<std::size_t I, typename Source, typename ... Types>
    struct read_attributes_t {
      static bool property (Source& in, const std::string& name, std::tuple<Types...>& t) {
        bool found = read_attributes_t<I - 1, Source, Types...>::property(in, name, t);
        if (!found) {
          auto& f = std::get<I - 1>(t);
          if (name == get_property_name(f)) {
            found |= read_property(in, f);
          }
        }
        return found;
      }
    };

    /// Stop recoursion at element 0
    template<typename Source, typename ... Types>
    struct read_attributes_t<0, Source, Types...> {
      static inline bool property (Source&, const std::string& name, std::tuple<Types ...>&) {
        return false;
      }
    };

    /// read tuple
    template<typename Source, typename ... Types>
    struct read_struct_t {
      static bool from (Source& in, std::tuple<Types...>& t) {
        std::string name;
        bool found = false;
        try {
          while (parser<Source>::read_next_struct_element(in, name)) {
            found |= read_attributes_t<sizeof...(Types), Source, Types...>::property(in, name, t);
            parser<Source>::read_struct_element_finish(in, name);
          }
        } catch (std::exception& ex) {
          throw std::runtime_error(msg_fmt() << ex.what() << " in struct '" << typeid(t).name()
                                             << "' after key '" << name
                                             << "' at position " << in.tellg());
        }
        return found;
      }
    };

    template<typename Source, typename ... Types>
    inline bool read_struct (Source& in, std::tuple<Types...>& t) {
      return read_struct_t<Source, Types...>::from(in, t);
    }

    /// read property as attribute
    template<typename Source, typename T>
    struct read_attribute_t {
      static bool from (Source& in, T& t) {
        std::string name;
        try {
          parser<Source>::read_property_init(in, name);
          const bool found = read_any(in, access_property_value(t));
          parser<Source>::read_property_finish(in, name);
          return found;
        } catch (std::exception& ex) {
          throw std::runtime_error(msg_fmt() << ex.what() << " for property '" << name
                                             << "' of type '" << typeid(t).name()
                                             << "' at position " << in.tellg());
        }
      }
    };

    template<typename Source, typename T>
    inline bool read_attribute (Source& in, T& t) {
      return read_attribute_t<Source, T>::from(in, t);
    }

    /// read property as setter
    template<typename Source, typename T>
    struct read_setter_t {
      static bool from (Source& in, T& t) {
        std::string name;
        try {
          parser<Source>::read_property_init(in, name);
          typename T::type v = {};
          bool found = read_any(in, v);
          if (found) {
            set_property_value(t, std::move(v));
          }
          parser<Source>::read_property_finish(in, name);
          return found;
        } catch (std::exception& ex) {
          throw std::runtime_error(msg_fmt() << ex.what() << " for property '" << name
                                             << "' of type '" << typeid(t).name()
                                             << "' at position " << in.tellg());
        }
      }
    };

    template<typename Source, typename T>
    inline bool read_setter (Source& in, T& t) {
      return read_setter_t<Source, T>::from(in, t);
    }

    /// read shared
    template<typename Source, typename T>
    struct read_shared_t {
      static bool from (Source& in, std::shared_ptr<T>& v) {
        if (parser<Source>::is_ptr_empty(in)) {
          return false;
        }
        if (!v) {
          v = std::make_shared<T>();
        }
        T& t = *v;
        return read_any(in, t);
      }
    };

    template<typename Source, typename T>
    inline bool read_shared (Source& in, std::shared_ptr<T>& t) {
      return read_shared_t<Source, T>::from(in, t);
    }

    /// read unique
    template<typename Source, typename T, typename D>
    struct read_unique_t {
      static bool from (Source& in, std::unique_ptr<T, D>& v) {
        if (parser<Source>::is_ptr_empty(in)) {
          return false;
        }
        if (!v) {
          v = std::make_unique<T>();
        }
        T& t = *v;
        return read_any(in, t);
      }
    };

    template<typename Source, typename T, typename D>
    inline bool read_unique (Source& in, std::unique_ptr<T, D>& t) {
      return read_unique_t<Source, T, D>::from(in, t);
    }

    /// read element with name of a tuple
    template<std::size_t I, typename Source, typename ... Types>
    struct read_tuple_element_t {
      static bool property (Source& in, const std::string& name, std::tuple<Types...>& t) {
        bool found = read_tuple_element_t<I - 1, Source, Types...>::property(in, name, t);
        if (!found) {
          auto& f = std::get<I - 1>(t);
          auto n = std::to_string(I - 1);
          if (name == n) {
            found |= read_property(in, f);
          }
        }
        return found;
      }
    };

    /// Stop recoursion at element 0
    template<typename Source, typename ... Types>
    struct read_tuple_element_t<0, Source, Types...> {
      static inline bool property (Source&, const std::string& name, std::tuple<Types ...>&) {
        return false;
      }
    };

    /// read tuple
    template<typename Source, typename ... Types>
    struct read_tuple_t {
      static bool from (Source& in, std::tuple<Types...>& t) {
        std::string name;
        bool found = false;
        try {
          while (parser<Source>::read_next_struct_element(in, name)) {
            found |= read_tuple_element_t<sizeof...(Types), Source, Types...>::property(in, name, t);
            parser<Source>::read_struct_element_finish(in, name);
          }
        } catch (std::exception& ex) {
          throw std::runtime_error(msg_fmt() << ex.what() << " in tuple '" << typeid(t).name()
                                             << "' after key '" << name
                                             << "' at position " << in.tellg());
        }
        return found;
      }
    };

    template<typename Source, typename ... Types>
    inline bool read_tuple(Source& in, std::tuple<Types...>& t) {
      return read_tuple_t<Source, Types...>::from(in, t);
    }

    /// read pair
    template<typename Source, typename T1, typename T2>
    struct read_pair_t {
      static bool from (Source& in, std::pair<T1, T2>& p) {
        if (!parser<Source>::read_list_start(in)) {
          return false;
        }
        parser<Source>::read_list_element_init(in, 0);
        if (!read_any(in, p.first)) {
          throw std::runtime_error(msg_fmt() << "Could not read first pair element at position " << in.tellg());
        }
        parser<Source>::read_list_element_finish(in);
        parser<Source>::read_list_element_init(in, 1);
        if (!read_any(in, p.second)) {
          throw std::runtime_error(msg_fmt() << "Could not read second pair element at position " << in.tellg());
        }
        parser<Source>::read_list_element_finish(in);
        parser<Source>::read_list_end(in);
        return true;
      }
    };

    template<typename Source, typename T1, typename T2>
    inline bool read_pair (Source& in, std::pair<T1, T2>& t) {
      return read_pair_t<Source, T1, T2>::from(in, t);
    }

    /// detect attribute
    template<typename Source, typename T>
    struct read_any_t<Source, detail::attribute<T>> {
      static inline bool from (Source& in, detail::attribute<T>& t) {
        return read_attribute(in, t);
      }
    };

    /// detect setter
    template<typename Source, typename T>
    struct read_any_t<Source, detail::setter<T>> {
      static inline bool from (Source& in, detail::setter<T>& t) {
        return read_setter(in, t);
      }
    };

    /// detect vector
    template<typename Source, typename T, typename A>
    struct read_any_t<Source, std::vector<T, A>> {
      static inline bool from (Source& in, std::vector<T, A>& t) {
        return read_vector(in, t);
      }
    };

    /// detect array
    template<typename Source, typename T, std::size_t S>
    struct read_any_t<Source, std::array<T, S>> {
      static inline bool from (Source& in, std::array<T, S>& t) {
        return read_array(in, t);
      }
    };

    /// detect map
    template<typename Source, typename K, typename V, typename C, typename A>
    struct read_any_t<Source, std::map<K, V, C, A>> {
      static inline bool from (Source& in, std::map<K, V, C, A>& m) {
        return read_map(in, m);
      }
    };

    /// detect struct
    template<typename Source, typename T>
    struct read_any_t<Source, T, typename std::enable_if<is_persistent<T>::value>::type> {
      static inline bool from (Source& in, T& t) {
        auto attr = persistent::attributes(t);
        return read_struct(in, attr);
      }
    };

    /// detect shared
    template<typename Source, typename T>
    struct read_any_t<Source, std::shared_ptr<T>> {
      static inline bool from (Source& in, std::shared_ptr<T>& t) {
        return read_shared(in, t);
      }
    };

    /// detect unique
    template<typename Source, typename T, typename D>
    struct read_any_t<Source, std::unique_ptr<T, D>> {
      static inline bool from (Source& in, std::unique_ptr<T, D>& t) {
        return read_unique(in, t);
      }
    };

    /// detect tuple
    template<typename Source, typename... Types>
    struct read_any_t<Source, std::tuple<Types...>> {
      static inline bool from (Source& in, std::tuple<Types...>& t) {
        return read_tuple(in, t);
      }
    };

    /// detect pair
    template<typename Source, typename T1, typename T2>
    struct read_any_t<Source, std::pair<T1, T2>> {
      static inline bool from (Source& in, std::pair<T1, T2>& t) {
        return read_pair(in, t);
      }
    };

    /// convenience helper
    template<typename Source, typename T>
    inline bool read (Source& in, T& t) {
      return read_any(in, t);
    }

  } // namespace io

} // namespace persistent

// --------------------------------------------------------------------------
