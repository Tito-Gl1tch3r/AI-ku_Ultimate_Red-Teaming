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
#include <string>
#include <functional>
#include <sstream>

// --------------------------------------------------------------------------
//
// Project includes
//


namespace persistent {

  // --------------------------------------------------------------------------
  //
  // Trivial base class for easier template specialization
  //
  struct persistent_struct {};

  template <typename T, typename S = void>
  struct is_persistent : std::false_type {};

  template <typename T>
  struct is_persistent<T, typename std::enable_if<std::is_base_of<persistent_struct, T>::value>::type> : std::true_type {};

  // --------------------------------------------------------------------------
  template<typename T>
  struct attribute_extractor {
    static auto get (T& t) {
        return t.attributes();
    }
  };

  template<typename T>
  inline auto attributes (T& t) {
    return attribute_extractor<T>::get(t);
  }

  template<typename T>
  struct attribute_extractor<const T> {
    static auto get (const T& t) {
        return attributes<T>(const_cast<T&>(t));
    }
  };

  template<typename T>
  inline auto attributes (const T& t) {
    return attribute_extractor<const T>::get(t);
  }

  // --------------------------------------------------------------------------
  template<typename... Ts>
  inline auto make_attributes (Ts... a) {
    return std::make_tuple(a...);
  }

  namespace detail {

    struct property {
      inline property (const std::string& name)
        :name(name)
      {}

      const std::string name;   /// The name of the property
    };
    // --------------------------------------------------------------------------
    //
    // Wrapper for a named attribute of a persistent struct.
    //
    template<typename T>
    struct attribute : public property {
      typedef T type;

      inline attribute (T& value, const std::string& name)
        : property(name)
        , value(value)
      {}

      T& value;           /// The attribute to read/write
    };

    // --------------------------------------------------------------------------
    //
    // Wrapper for a named attribute of a persistent struct.
    //
    template<typename T>
    struct getter : public property {
      typedef T type;

      inline getter (T value, const std::string& name)
        : property(name)
        , value(value)
      {}

      T value;    /// The attribute to read
    };

    // --------------------------------------------------------------------------
    template<class C, typename T>
    inline std::function<void(T)> bind (C* c, void(C::*method)(T)) {
      return [=](T t) {
        return (c->*method)(t);
      };
    }

    // --------------------------------------------------------------------------
    //
    // Wrapper for a named attribute of a persistent struct.
    //
    template<typename T>
    struct setter : public property {
      inline setter (std::function<void(T)> fn, const std::string& name)
        : property(name)
        , fn(fn)
      {}

      inline void call (T&& value) {
        fn(std::move(value));
      }

      std::function<void(T)> fn; /// The method to write the attribute to
    };

  } // namespace detail

  // --------------------------------------------------------------------------
  template<typename T>
  inline detail::attribute<T> attribute (T& value, const std::string& n) {
    return detail::attribute<T>(value, n);
  }

  template<typename T>
  inline detail::getter<T> getter (T&& value, const std::string& n) {
    return detail::getter<T>(value, n);
  }

  template<class C, typename T>
  inline detail::setter<T> setter (C& c, void(C::*method)(T), const std::string& n) {
    return detail::setter<T>(detail::bind(&c, method), n);
  }

  template<typename T>
  inline detail::setter<T> setter (std::function<void(T)> fn, const std::string& n) {
    return detail::setter<T>(fn, n);
  }

  // --------------------------------------------------------------------------
  template<typename T>
  inline const std::string& get_property_name (const detail::attribute<T>& a) {
    return a.name;
  }

  template<typename T>
  inline const std::string& get_property_name (const detail::getter<T>& g) {
    return g.name;
  }

  template<typename T>
  inline const std::string& get_property_name (const detail::setter<T>& s) {
    return s.name;
  }

  // --------------------------------------------------------------------------
  template<typename T>
  inline const T& get_property_value (const detail::attribute<T>& a) {
    return a.value;
  }

  template<typename T>
  inline const T get_property_value (const detail::getter<T>& g) {
    return g.value;
  }

  // --------------------------------------------------------------------------
  template<typename T>
  inline T& access_property_value (detail::attribute<T>& a) {
    return a.value;
  }

  template<typename T>
  inline void set_property_value (detail::setter<T>& s, std::remove_const_t<std::remove_reference_t<T>>&& value) {
    s.call(std::move(value));
  }

  // --------------------------------------------------------------------------
  template<typename T>
  struct convert {

    static inline std::string key_to_string (const T& k) {
      std::ostringstream os;
      os << k;
      return os.str();
    }

    static inline T string_to_key (const std::string& s) {
      T k = {};
      std::istringstream(s) >> k;
      return k;
    }
  };

  template<>
  struct convert<std::string> {

    static inline const std::string& key_to_string (const std::string& k) {
      return k;
    }

    static inline const std::string& string_to_key (const std::string& k) {
      return k;
    }
  };

  // --------------------------------------------------------------------------

} // namespace persistent

// --------------------------------------------------------------------------
