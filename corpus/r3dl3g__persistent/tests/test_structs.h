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
* @brief     C++ struct persistence test
*
* @license   MIT license. See accompanying file LICENSE.
*/

#pragma once

#include <memory>
#include "persistent.h"

using namespace persistent;

// --------------------------------------------------------------------------
struct names {
  static constexpr char i[] = "i";
  static constexpr char j[] = "j";
  static constexpr char v[] = "v";

  static constexpr char i1[] = "i1";
  static constexpr char t1[] = "t1";
  static constexpr char i2[] = "i2";
};

// --------------------------------------------------------------------------
template<typename T>
constexpr std::pair<char const*, T> get_test_data ();

template<> constexpr std::pair<char const*, bool>         get_test_data<bool> ()         { return { "1", true }; }
template<> constexpr std::pair<char const*, char>         get_test_data<char> ()         { return { "\"A\"", 'A' }; }
template<> constexpr std::pair<char const*, int8_t>       get_test_data<int8_t> ()       { return { "-127", -127 }; }
template<> constexpr std::pair<char const*, uint8_t>      get_test_data<uint8_t> ()      { return { "255", 255 }; }
template<> constexpr std::pair<char const*, int16_t>      get_test_data<int16_t> ()      { return { "-32767", -32767 }; }
template<> constexpr std::pair<char const*, uint16_t>     get_test_data<uint16_t> ()     { return { "65535", 65535 }; }
template<> constexpr std::pair<char const*, int32_t>      get_test_data<int32_t> ()      { return { "-2147483647", -2147483647 }; }
template<> constexpr std::pair<char const*, uint32_t>     get_test_data<uint32_t> ()     { return { "4294967295", 4294967295 }; }
template<> constexpr std::pair<char const*, int64_t>      get_test_data<int64_t> ()      { return { "-549755813887", -549755813887 }; }
template<> constexpr std::pair<char const*, uint64_t>     get_test_data<uint64_t> ()     { return { "549755813887", 549755813887 }; }
template<> constexpr std::pair<char const*, long>         get_test_data<long> ()         { return { "-549755813887", -549755813887 }; }
template<> constexpr std::pair<char const*, unsigned long> get_test_data<unsigned long> () { return { "549755813887", 549755813887 }; }
template<> constexpr std::pair<char const*, float>        get_test_data<float> ()        { return { "12345.12345", 12345.12345 }; }
template<> constexpr std::pair<char const*, double>       get_test_data<double> ()       { return { "12345678.12345678", 12345678.12345678 }; }
template<> inline    std::pair<char const*, std::string>  get_test_data<std::string> ()  { return { "\"Some text\"", "Some text" }; }
template<> inline    std::pair<char const*, std::unique_ptr<int64_t>> get_test_data<std::unique_ptr<int64_t>> () { return { "-549755813887", std::make_unique<int64_t>(-549755813887) }; }
template<> inline    std::pair<char const*, std::shared_ptr<int64_t>> get_test_data<std::shared_ptr<int64_t>> () { return { "-549755813886", std::make_shared<int64_t>(-549755813886) }; }

// --------------------------------------------------------------------------
struct test_int64 : private persistent_struct {

  int64_t i = 0;
  int64_t j = 0;

  auto attributes () {
    return make_attributes(attribute(i, names::i), attribute(j, names::j));
  }

};

// ----------------------------------------------------------------------------------------------------------------------------------------------------
struct test2 : private persistent_struct {

  int64_t i1 = 0;
  test_int64 t1;
  std::unique_ptr<int64_t> i2;

  auto attributes () {
    return make_attributes(attribute(i1, names::i1), attribute(t1, names::t1), attribute(i2, names::i2));
  }

};

// --------------------------------------------------------------------------
struct test3 : private persistent_struct {
private:
  std::vector<test_int64> m_v;

public:
  auto attributes () {
    return std::make_tuple(attribute(m_v, names::v));
  }

  const auto attributes () const {
    return std::make_tuple(attribute(m_v, names::v));
  }

  const std::vector<test_int64>& v () const {
    return m_v;
  }

  std::vector<test_int64>& v () {
    return m_v;
  }
};

// --------------------------------------------------------------------------
struct test4 : private persistent_struct {
  test4 (int64_t i_ = {}, const std::vector<int>& l_ = {})
    : i(i_)
    , l(l_)
  {}

  auto attributes () {
    return make_attributes(attribute(i, names::i), attribute(l, names::i));
  }

  int64_t i;
  std::vector<int> l;
};

// --------------------------------------------------------------------------
struct test5 : private persistent_struct {
  test5 (const std::string& i_ = {}, const std::vector<std::string>& l_ = {})
    : i(i_)
    , l(l_)
  {}

  auto attributes () {
    return make_attributes(attribute(i, names::i), attribute(l, names::i));
  }

  std::string i;
  std::vector<std::string> l;
};

// --------------------------------------------------------------------------
struct test6 : private persistent_struct {
  test6 (const std::string& i_ = {}, const std::vector<std::string>& l_ = {})
    : i(i_)
    , l(l_)
  {}

  auto attributes () {
    return make_attributes(attribute(l, names::i), attribute(i, names::i));
  }

  std::vector<std::string> l;
  std::string i;
};

// --------------------------------------------------------------------------
struct test7 : private persistent_struct {
  test7 (const std::string& s_ = {}, int i_ = {})
    : p(std::make_pair(s_, i_))
  {}

  auto attributes () {
    return make_attributes(attribute(p, names::v));
  }

  std::pair<std::string, int> p;
};

// --------------------------------------------------------------------------
enum class key : char {
  first = 'F',
  second = 'S',
  third = 'T'
};

namespace persistent {

  template<>
  struct convert<key> {

    static inline std::string key_to_string (const key& k) {
      return std::string(1, static_cast<char>(k));
    }

    static inline key string_to_key (const std::string& k) {
      return static_cast<key>(k[0]);
    }

  };
}

// --------------------------------------------------------------------------
std::ostream& operator<< (std::ostream& os, key k) {
  return os << static_cast<char>(k);
}

std::istream& operator>> (std::istream& is, key& k) {
  return is >> reinterpret_cast<char&>(k);
}
// --------------------------------------------------------------------------

struct CpuLoad {
  std::string cpu;
  float usr;
  float nice;
  float sys;
  float iowait;
  float irq;
  float soft;
  float steal;
  float guest;
  float gnice;
  float idle;
};

struct Statistics {
  std::string timestamp;
  std::vector<CpuLoad> cpu_load;
};

struct Host {
  std::string nodename;
  std::string sysname;
  std::string release;
  std::string machine;
  int number_of_cpus;
  std::string date;
  std::vector<Statistics> statistics;
};

struct SysStat {
  std::vector<Host> hosts;
};

struct MpStat {
  SysStat sysstat;
};
// --------------------------------------------------------------------------
namespace persistent {

  template <>
  struct is_persistent<CpuLoad> : std::true_type {};

  template <>
  struct is_persistent<Statistics> : std::true_type {};

  template <>
  struct is_persistent<Host> : std::true_type {};

  template <>
  struct is_persistent<SysStat> : std::true_type {};

  template <>
  struct is_persistent<MpStat> : std::true_type {};

  template<>
  auto attributes<CpuLoad> (CpuLoad& t) {
    return make_attributes(
      attribute(t.cpu, "cpu"),
      attribute(t.usr, "usr"),
      attribute(t.nice, "nice"),
      attribute(t.sys, "sys"),
      attribute(t.iowait, "iowait"),
      attribute(t.irq, "irq"),
      attribute(t.soft, "soft"),
      attribute(t.steal, "steal"),
      attribute(t.guest, "guest"),
      attribute(t.gnice, "gnice"),
      attribute(t.idle, "idle")
    );
  }

  template<>
  auto attributes<Statistics> (Statistics& t) {
    return make_attributes(
      attribute(t.timestamp, "timestamp"),
      attribute(t.cpu_load, "cpu-load")
    );
  }

  template<>
  auto attributes<Host> (Host& t) {
    return make_attributes(
      attribute(t.nodename, "nodename"),
      attribute(t.sysname, "sysname"),
      attribute(t.release, "release"),
      attribute(t.machine, "machine"),
      attribute(t.number_of_cpus, "number-of-cpus"),
      attribute(t.date, "date"),
      attribute(t.statistics, "statistics")
    );
  }

  template<>
  auto attributes<SysStat> (SysStat& t) {
    return make_attributes(attribute(t.hosts, "hosts"));
  }

  template<>
  auto attributes<MpStat> (MpStat& t) {
    return make_attributes(attribute(t.sysstat, "sysstat"));
  }

}
