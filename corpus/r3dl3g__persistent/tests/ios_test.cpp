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

#include "persistent_ios.h"
#include <testing/testing.h>

#include "test_structs.h"

// --------------------------------------------------------------------------
void test_read_empty () {

  test_int64 t1;
  std::istringstream is("{}");
  io::read_stream(is, t1);

  EXPECT_EQUAL(t1.i, 0);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_TRUE(is.good());
  is.get();
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}
// --------------------------------------------------------------------------
template<typename T>
constexpr std::pair<char const*, T> get_ios_test_data () {
  return get_test_data<T>();
}

template<> inline std::pair<char const*, std::string>  get_ios_test_data<std::string> ()  {
  return { "\"Some text\"", "Some text" };
}

// --------------------------------------------------------------------------
template<typename T>
void test_read_prop_type () {
  const auto expected = get_ios_test_data<T>();
  const std::string str = io::msg_fmt() << "i:" << expected.first;

  T value = {};
  std::istringstream is(str);
  auto at = attribute(value, "i");
  io::read_stream(is, at);

  EXPECT_EQUAL(value, expected.second, " for type ", typeid(T).name(), " with source ", str);
}
// --------------------------------------------------------------------------
template<typename T, typename... Types>
struct Test {
  static void test () {
    test_read_prop_type<T>();
    Test<Types...>::test();
  }
};

template<typename T>
struct Test<T> {
  static void test () {
    test_read_prop_type<T>();
  }
};
// --------------------------------------------------------------------------
void test_read_all_basic_types () {
  Test<bool, int8_t, int16_t, int32_t, int64_t, uint8_t, uint16_t, uint32_t, uint64_t, float, double,
       std::string, char, short, int, long, unsigned char, unsigned short, unsigned int, unsigned long>::test();
}

// --------------------------------------------------------------------------
void test_read_array () {

  std::array<int64_t, 5> a;
  std::istringstream is("a:[1,2,3,4,5]");
  auto at = attribute(a, "a");
  io::read_stream(is, at);

  std::array<int64_t, 5> expected = {1, 2, 3, 4, 5};
  EXPECT_EQUAL(a, expected);
}
// --------------------------------------------------------------------------
void test_read_vector () {

  std::vector<int64_t> v;
  std::istringstream is("v:[1,2,3,4,5]");
  auto at = attribute(v, "v");
  io::read_stream(is, at);

  std::vector<int64_t> expected = {1, 2, 3, 4, 5};
  EXPECT_EQUAL(v, expected);
}
// --------------------------------------------------------------------------
void test_read_pair () {
  test7 t;
  std::istringstream is("{v:[\"Any Text\",4711]}");
  io::read_stream(is, t);
  std::pair<std::string, int> expected = {"Any Text", 4711};
  EXPECT_EQUAL(t.p, expected);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}
// --------------------------------------------------------------------------
void test_read_map () {
  std::istringstream is("{one:1,three:3,two:2}");
  std::map<std::string, double> m;
  io::read_stream(is, m);
  std::map<std::string, double> expected { { "one", 1 }, { "two", 2 }, { "three", 3 } };
  EXPECT_EQUAL(m, expected);
}
// --------------------------------------------------------------------------
void test_read_map_2 () {
  std::istringstream is("{1:1.1,2:2.2,3:3.3}");
  std::map<int, double> m;
  io::read_stream(is, m);
  std::map<int, double> expected { { 1, 1.1 }, { 2, 2.2 }, { 3, 3.3 } };
  EXPECT_EQUAL(m, expected);
}
// --------------------------------------------------------------------------
void test_read_map_3 () {
  std::istringstream is("{F:1.1,S:2.2,T:3.3}");
  std::map<key, double> m;
  io::read_stream(is, m);
  std::map<key, double> expected { { key::first, 1.1 }, { key::second, 2.2 }, { key::third, 3.3 } };
  EXPECT_EQUAL(m, expected);
}

// --------------------------------------------------------------------------
void test_read_1 () {

  test_int64 t1;
  std::istringstream is("{i:4711}");
  io::read_stream(is, t1);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_2 () {

  test_int64 t1;
  std::istringstream is("{i:4711,j:815}");
  io::read_stream(is, t1);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 815);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_3 () {

  int64_t i = 0;
  std::istringstream is("i:4711");
  auto at = attribute(i, "i");
  io::read_stream(is, at);

  EXPECT_EQUAL(i, 4711);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_4 () {

  test_int64 t1;
  std::istringstream is(" \n \t { \n \t i \n \t : \n \t 4711 \n \t } \n \t ");
  io::read_stream(is, t1);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_5 () {
  test2 t2;
  std::istringstream is("{i1:815, t1:{i:911, j:203}, i2: 4711}");
  io::read_stream(is, t2);

  EXPECT_EQUAL(t2.i1, 815);
  EXPECT_EQUAL(t2.t1.i, 911);
  EXPECT_EQUAL(t2.t1.j, 203);
  EXPECT_EQUAL(*(t2.i2), 4711);
}

// --------------------------------------------------------------------------
void test_read_6 () {

  test_int64 t1;
  std::istringstream is("{i:4711,k:815}");
  try {
    io::read_stream(is, t1);
    EXPECT_FALSE("Exception expected");
  } catch (std::exception& ex) {
    EXPECT_TRUE("Exception expected");
  }

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_TRUE(is.good());
}

// --------------------------------------------------------------------------
void test_read_7 () {

  test3 t3;
  std::istringstream is("{v:[{i:1,j:2},{i:3,j:4},{i:5,j:6}]}");
  io::read_stream(is, t3);

  EXPECT_EQUAL(t3.v().size(), 3);
  EXPECT_EQUAL(t3.v()[0].i, 1);
  EXPECT_EQUAL(t3.v()[0].j, 2);
  EXPECT_EQUAL(t3.v()[1].i, 3);
  EXPECT_EQUAL(t3.v()[1].j, 4);
  EXPECT_EQUAL(t3.v()[2].i, 5);
  EXPECT_EQUAL(t3.v()[2].j, 6);
}

// --------------------------------------------------------------------------
void test_read_8 () {
  test5 t;
  std::istringstream is("{i:\"Text 5\",i:[\"List item 1\",\"List item 2\"]}");

  io::read_stream(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 5");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_9 () {
  test6 t;
  std::istringstream is("{i:\"Text 6\",i:[\"List item 1\",\"List item 2\"]}");

  io::read_stream(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 6");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_10 () {
  test5 t;
  std::istringstream is("{i:[\"List item 1\",\"List item 2\"],i:\"Text 7\"}");

  io::read_stream(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 7");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_11 () {
  test6 t;
  std::istringstream is("{i:[\"List item 1\",\"List item 2\"],i:\"Text 8\"}");

  io::read_stream(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 8");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_write_1 () {
  int64_t i = 4711;
  std::ostringstream os;
  io::write_stream(os, attribute(i, "i"));

  EXPECT_EQUAL(os.str(), "i:4711");
}

// --------------------------------------------------------------------------
void test_write_2 () {
  test_int64 t1;
  std::ostringstream os;
  io::write_stream(os, t1);

  EXPECT_EQUAL(os.str(), "{i:0,j:0}");
}

// --------------------------------------------------------------------------
void test_write_3 () {
  test2 t2;
  std::ostringstream os;
  io::write_stream(os, t2);

  EXPECT_EQUAL(os.str(), "{i1:0,t1:{i:0,j:0},i2:}");
}

// --------------------------------------------------------------------------
void test_write_4 () {
  test3 t3;
  t3.v().push_back(test_int64());
  std::ostringstream os;
  io::write_stream(os, t3);

  EXPECT_EQUAL(os.str(), "{v:[{i:0,j:0}]}");
}

// --------------------------------------------------------------------------
void test_write_5 () {
  test5 t("Text 5", {"List item 1", "List item 2"});
  std::ostringstream os;
  io::write_stream(os, t);

  EXPECT_EQUAL(os.str(),"{i:\"Text 5\",i:[\"List item 1\",\"List item 2\"]}");
}

// --------------------------------------------------------------------------
void test_write_6 () {
  test6 t("Text 6", {"List item 1", "List item 2"});
  std::ostringstream os;
  io::write_stream(os, t);

  EXPECT_EQUAL(os.str(),"{i:[\"List item 1\",\"List item 2\"],i:\"Text 6\"}");
}

// --------------------------------------------------------------------------
void test_write_array () {

  std::array<int64_t, 5> a({1, 2, 3, 4, 5});
  std::ostringstream os;
  auto at = attribute(a, "a");
  io::write_stream(os, at);
  EXPECT_EQUAL(os.str(), "a:[1,2,3,4,5]");
}
// --------------------------------------------------------------------------
void test_write_vector () {

  std::vector<int64_t> v({1, 2, 3, 4, 5});
  std::ostringstream os;
  auto at = attribute(v, "v");
  io::write_stream(os, at);
  EXPECT_EQUAL(os.str(), "v:[1,2,3,4,5]");
}
// --------------------------------------------------------------------------
void test_write_pair () {
  test7 t("Any Text", 4711);
  std::ostringstream os;
  io::write_stream(os, t);

  EXPECT_EQUAL(os.str(), "{v:[\"Any Text\",4711]}");
}
// --------------------------------------------------------------------------
void test_write_map () {
  std::map<std::string, double> m { { "one", 1 }, { "two", 2 }, { "three", 3 } };
  std::ostringstream os;
  io::write_stream(os, m);

  EXPECT_EQUAL(os.str(), "{one:1,three:3,two:2}");
}
// --------------------------------------------------------------------------
void test_write_map_2 () {
  std::map<int, double> m { { 1, 1.1 }, { 2, 2.2 }, { 3, 3.3 } };
  std::ostringstream os;
  io::write_stream(os, m);

  EXPECT_EQUAL(os.str(), "{1:1.1,2:2.2,3:3.3}");
}
// --------------------------------------------------------------------------
void test_write_map_3 () {
  std::map<key, double> m { { key::first, 1.1 }, { key::second, 2.2 }, { key::third, 3.3 } };
  std::ostringstream os;
  io::write_stream(os, m);

  EXPECT_EQUAL(os.str(), "{F:1.1,S:2.2,T:3.3}");
}
// --------------------------------------------------------------------------
void test_main (const testing::start_params& params) {
  testing::log_info("Running " __FILE__);
  run_test(test_read_empty);
  run_test(test_read_all_basic_types);
  run_test(test_read_array);
  run_test(test_read_vector);
  run_test(test_read_pair);
  run_test(test_read_map);
  run_test(test_read_map_2);
  run_test(test_read_map_3);
  run_test(test_read_1);
  run_test(test_read_2);
  run_test(test_read_3);
  run_test(test_read_4);
  run_test(test_read_5);
  run_test(test_read_6);
  run_test(test_read_7);
  run_test(test_read_8);
  run_test(test_read_9);
  run_test(test_read_10);
  run_test(test_read_11);

  run_test(test_write_array);
  run_test(test_write_vector);
  run_test(test_write_pair);
  run_test(test_write_map);
  run_test(test_write_map_2);
  run_test(test_write_map_3);
  run_test(test_write_1);
  run_test(test_write_2);
  run_test(test_write_3);
  run_test(test_write_4);
  run_test(test_write_5);
  run_test(test_write_6);
}

// --------------------------------------------------------------------------

