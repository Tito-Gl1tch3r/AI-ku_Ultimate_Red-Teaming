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

// --------------------------------------------------------------------------
//
// Project includes
//
#include "persistent_ios.h"


namespace persistent {

  namespace io {

    // --------------------------------------------------------------------------
    //
    // specializations for xml ostream
    //
    struct xml_formatter_context : public ios_formatter_context {
      xml_formatter_context (std::ostream& os, bool beautify = true)
        : ios_formatter_context(os, beautify)
      {}

    };

    namespace xml {
      const std::string s_header = "<?xml version=\"1.0\" encoding=\"utf-8\"?>";
      const std::string s_body = "<body>";
      const std::string s_nbody = "</body>";
    }

    template<>
    struct formatter<xml_formatter_context> {

      static void write_list_start (xml_formatter_context& out) {
        out.endl().fill().os << "<ol>",
        out.endl().inc();
      }

      static void write_list_element_init (xml_formatter_context& out, int) {
        out.fill().inc().os << "<li>";
      }

      static void write_list_element_finish (xml_formatter_context& out) {
        out.dec().fill().os << "</li>";
        out.endl();
      }

      static void write_list_end (xml_formatter_context& out) {
        out.dec().fill().os << "</ol>";
        out.endl();
      }

      static void write_members_delemiter (xml_formatter_context&) {
      }

      static void write_property_init (xml_formatter_context& out, const std::string& name) {
        out.fill().inc().os << "<" << name << '>';
      }

      static void write_property_finish (xml_formatter_context& out, const std::string& name) {
        out.dec().fill().os << "</" << name << '>';
        out.endl();
      }

      static void write_struct_start (xml_formatter_context&) {
      }

      static void write_struct_end (xml_formatter_context&) {
      }

      static void write_empty_ptr (xml_formatter_context&) {
      }
    };

    template<typename T>
    struct write_value_t<xml_formatter_context, T> {
      static void to (xml_formatter_context& out, const T& t) {
        write_value(out.os, t);
      }
    };

    template<>
    struct write_value_t<xml_formatter_context, const std::string> {
      static void to (xml_formatter_context& out, const std::string& t) {
        out.os << t;
      }
    };

    template<typename T>
    void write_xml (std::ostream& os, const T& t, bool beautify = true) {
      xml_formatter_context out(os, beautify);
      out.os << xml::s_header;
      out.endl().os << xml::s_body;
      out.endl().inc();
      write(out, t);
      out.dec();
      os << xml::s_nbody;
      out.endl();
    }

    // --------------------------------------------------------------------------
    //
    // specializations for xml formatted istream
    //
    struct xml_parser_context {
      xml_parser_context (std::istream& is)
        : is(is)
      {}

      std::istream& is;

      const std::string& next_token () {
        if (token_empty()) {
          next();
        }
        return token;
      }

      const std::string& next () {
        is >> std::ws;
        token.clear();
        if (is.peek() == '<') {
          std::getline(is, token, '>');
          token += '>';
        }
        return token;
      }

      void check_token (const std::string& expected) {
        if (next_token() != expected) {
          throw std::runtime_error(msg_fmt() << "Expected '" << expected
                                             << "' but got '" << token 
                                             << "' at position " << is.tellg());
        }
        clear_token();
      }

      void clear_token () {
        token.clear();
      }

      bool token_empty () const {
        return token.empty();
      }

      auto tellg () const {
        return is.tellg();
      }

    private:
      std::string token;

    };

    template<>
    struct parser<xml_parser_context> {

      static bool read_list_start (xml_parser_context& in) {
        if (in.next_token() == "<ol>") {
          in.clear_token();
          return true;
        }
        return false;
      }

      static bool read_list_element_init (xml_parser_context& in, int) {
        if (in.next_token() == "<li>") {
          in.clear_token();
          return true;
        }
        return false;
      }

      static void read_list_element_finish (xml_parser_context& in) {
        in.check_token("</li>");
      }

      static void read_list_end (xml_parser_context& in) {
        in.check_token("</ol>");
      }

      static void read_property_init (xml_parser_context& in, std::string& key) {
        const std::string& token = in.next_token();
        if ((token.size() < 3) || (token.front() != '<') || (token.back() != '>')) {
          throw std::runtime_error(msg_fmt() << "Expected '<xyz>' but got '" << token
                                             << "' at position " << in.tellg());
        }
        key = token.substr(1, token.size() - 2);
        in.clear_token();
      }

      static void read_property_finish (xml_parser_context& in, const std::string& key) {
        in.check_token("</" + key + ">");
      }

      static bool read_next_struct_element (xml_parser_context& in, std::string& key) {
        const std::string& token = in.next_token();
        if (in.is.good() && (token.compare(0, 2, "</") != 0) &&
            (token.size() > 2) && (token.front() == '<') && (token.back() == '>')) {
          key = token.substr(1, token.size() - 2);
          in.clear_token();
          return true;
        }
        return false;
      }

      static void read_struct_element_finish (xml_parser_context& in, const std::string& key) {
        in.check_token("</" + key + ">");
      }

      static bool is_ptr_empty (xml_parser_context& in) {
        const std::string& token = in.next_token();
        return in.is.good() && (token.compare(0, 2, "</") == 0);
      }
    };

    template<typename T>
    struct read_value_t<xml_parser_context, T> {
      static bool from (xml_parser_context& in, T& t) {
        if (in.next_token().empty()) {
          return read_value(in.is, t);
        }
        return false;
      }
    };

    template<>
    struct read_value_t<xml_parser_context, std::string> {
      static bool from (xml_parser_context& in, std::string& t) {
        if (in.next_token().empty()) {
          std::getline(in.is, t, '<');
          if (in.is.good()) {
            in.is.putback('<');
          }
          return true;
        }
        return false;
      }
    };

    template<>
    struct read_value_t<xml_parser_context, char> {
      static bool from (xml_parser_context& in, char& t) {
        if (in.next_token().empty()) {
          t = in.is.get();
          return true;
        }
        return false;
      }
    };

    template<typename T>
    bool read_xml (std::istream& is, T& t) {
      xml_parser_context in(is);
      in.check_token(xml::s_header);
      in.check_token(xml::s_body);
      const bool found = read(in, t);
      in.check_token(xml::s_nbody);
      return found;
    }

  } // namespace io

} // namespace persistent

// --------------------------------------------------------------------------
