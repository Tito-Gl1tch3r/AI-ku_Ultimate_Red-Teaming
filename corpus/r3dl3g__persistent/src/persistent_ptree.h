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
// Library includes
//
#include <boost/property_tree/ptree.hpp>

// --------------------------------------------------------------------------
//
// Project includes
//
#include "persistent_io.h"


namespace persistent {

  namespace io {

    typedef boost::property_tree::ptree ptree;

    // --------------------------------------------------------------------------
    //
    // write
    //
    // --------------------------------------------------------------------------

    /// write value
    template<typename T>
    struct write_value_t<ptree, T> {
      static void to (ptree& pt, const T& t) {
        pt.put_value(t);
      }
    };

    /// write property
    template<typename T>
    struct write_attribute_t<ptree, T> {
      static void to (ptree& p, const attribute<T>& t) {
        ptree child;
        write_any(child, get_property_value(t));
        p.add_child(get_property_name(t), child);
      }
    };

    /// write vector and array values
    template<typename T, typename V>
    struct writeList_t<ptree, T, V> {
      static void to (ptree& p, const V& v) {
        for (const T& t : v) {
          ptree pt;
          write_any(pt, t);
          p.push_back(std::make_pair("", pt));
        }
      }
    };

    /// write pair
    template<typename T1, typename T2>
    struct write_pair_t<ptree, T1, T2> {
      static void to (ptree& p, const std::pair<T1, T2>& v) {
        ptree pt;
        write_any(pt, v.first);
        p.push_back(std::make_pair("", pt));
        pt.clear();
        write_any(pt, v.second);
        p.push_back(std::make_pair("", pt));
      }
    };

    // --------------------------------------------------------------------------
    //
    // read
    //
    // --------------------------------------------------------------------------

    /// read value
    template<typename T>
    struct read_value_t<ptree, T> {
      static bool from (ptree& p, T& t) {
        t = p.get_value<T>(T());
        return true;
      }
    };

    /// read vector
    template<typename T>
    struct read_vector_t<ptree, T, typename V> {
      static bool from (ptree& p, V& v) {
        int i = 0;
        v.resize(p.size());
        for (auto& item : p) {
          read_any(item.second, v[i++]);
        }
        return true;
      }
    };

    /// read array
    template<typename T, typename A>
    struct read_array_t<ptree, T, A> {
      static bool from (ptree& p, A& a) {
        int i = 0;
        for (auto& item : p) {
          read_any(item.second, a[i++]);
        }
        return true;
      }
    };

    /// read pair
    template<typename T1, typename T2>
    struct read_pair_t<ptree, T1, T2> {
      static bool from (ptree& p, std::pair<T1, T2>& v) {
        if (p.size() != 2) {
          throw std::runtime_error(msg_fmt() << "Expected to have 2 childs for pair but got " << p.size());
        }
        read_any(p.front(), v.first);
        read_any(p.back(), v.second);
        return true;
      }
    };

    /// read tuple
    template<typename ... Types>
    struct read_struct_t<ptree, Types...> {
      static bool from (ptree& p, std::tuple<Types&...> t) {
        bool found = true;
        for (auto& item : p) {
          found |= read_attributes_t<sizeof...(Types), ptree, Types...>::property(item.second, item.first, t);
        }
        return found;
      }
    };

  } // namespace io

  // --------------------------------------------------------------------------
  struct ptree_struct : public persistent_struct {
    typedef persistent_struct super;

    void write (io::ptree& pt) const {
      io::write(pt, *this);
    }

    bool read (io::ptree& pt) {
      return io::read(pt, *this);
    }

  };

} // namespace persistent

// --------------------------------------------------------------------------
