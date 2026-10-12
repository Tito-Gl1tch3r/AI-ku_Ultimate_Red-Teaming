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

#include "persistent_ini.h"
#include <testing/testing.h>

#include "test_structs.h"

// --------------------------------------------------------------------------
void test_read_empty () {

  test_int64 t1;
  std::istringstream is("");
  io::read_ini(is, t1);

  EXPECT_EQUAL(t1.i, 0);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
template<typename T>
void test_read_prop_type () {
  const auto expected = get_test_data<T>();
  std::string test_value = expected.first;
  test_value.erase(remove(test_value.begin(), test_value.end(), '\"'), test_value.end());
  const std::string str = io::msg_fmt() << "i=" << test_value;

  T value = {};
  std::istringstream is(str);
  auto at = attribute(value, "i");
  io::read_ini(is, at);

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
  std::istringstream is("a.0=1\n"
                        "a.1=2\n"
                        "a.2=3\n"
                        "a.3=4\n"
                        "a.4=5\n");
  auto at = attribute(a, "a");
  io::read_ini(is, at);

  std::array<int64_t, 5> expected = {1, 2, 3, 4, 5};
  EXPECT_EQUAL(a, expected);
}
// --------------------------------------------------------------------------
void test_read_vector () {

  std::vector<int64_t> v;
  std::istringstream is("v.0=1\n"
                        "v.1=2\n"
                        "v.2=3\n"
                        "v.3=4\n"
                        "v.4=5\n");
  auto at = attribute(v, "v");
  io::read_ini(is, at);

  std::vector<int64_t> expected = {1, 2, 3, 4, 5};
  EXPECT_EQUAL(v, expected);
}
// --------------------------------------------------------------------------
void test_read_pair () {
  test7 t;
  std::istringstream is("v.0=Any Text\n"
                        "v.1=4711\n");
  io::read_ini(is, t);
  EXPECT_EQUAL(t.p.first, "Any Text");
  EXPECT_EQUAL(t.p.second, 4711);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}
// --------------------------------------------------------------------------
void test_read_map () {
  std::istringstream is("one=1\n"
                        "three=3\n"
                        "two=2\n");
  std::map<std::string, double> m;
  io::read_ini(is, m);
  std::map<std::string, double> expected { { "one", 1 }, { "two", 2 }, { "three", 3 } };
  EXPECT_EQUAL(m, expected);
}

// --------------------------------------------------------------------------
void test_read_1 () {

  int64_t i = 0;
  std::istringstream is("i=4711\n");
  auto at = attribute(i, "i");
  io::read_ini(is, at);

  EXPECT_EQUAL(i, 4711);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_2 () {

  test_int64 t1;
  std::istringstream is("i=4711\n"
                        "j=815\n");
  io::read_ini(is, t1);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 815);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_3 () {

  test_int64 t1;
  std::istringstream is("i=4711\n");
  io::read_ini(is, t1);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_4 () {

  test_int64 t1;
  std::istringstream is(" \n \t \n \t i \t = \t 4711 \n \t \n \t ");
  io::read_ini(is, t1);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_5 () {
  test2 t2;
  std::istringstream is("i1=815\n"
                        "t1.i=911\n"
                        "t1.j=203\n"
                        "i2=4711\n");
  io::read_ini(is, t2);

  EXPECT_EQUAL(t2.i1, 815);
  EXPECT_EQUAL(t2.t1.i, 911);
  EXPECT_EQUAL(t2.t1.j, 203);
  EXPECT_EQUAL(*(t2.i2), 4711);
}

// --------------------------------------------------------------------------
void test_read_6 () {

  test_int64 t1;
  std::istringstream is("i=4711\n"
                        "k=815\n");
  try {
    io::read_ini(is, t1);
    EXPECT_FALSE("Exception expected");
  } catch (std::exception& ex) {
    EXPECT_TRUE("Exception expected");
  }

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_7 () {

  test3 t3;
  std::istringstream is("v.0.i=1\n"
                        "v.0.j=2\n"
                        "v.1.i=3\n"
                        "v.1.j=4\n"
                        "v.2.i=5\n"
                        "v.2.j=6\n");
  io::read_ini(is, t3);

  EXPECT_EQUAL(t3.v().size(), 3);
  EXPECT_EQUAL(t3.v()[0].i, 1);
  EXPECT_EQUAL(t3.v()[0].j, 2);
  EXPECT_EQUAL(t3.v()[1].i, 3);
  EXPECT_EQUAL(t3.v()[1].j, 4);
  EXPECT_EQUAL(t3.v()[2].i, 5);
  EXPECT_EQUAL(t3.v()[2].j, 6);
}

// --------------------------------------------------------------------------
void test_read_8a () {

  test4 t4;
  std::istringstream is("i=4711\n"
                        "i.0=1\n"
                        "i.1=2\n"
                        "i.2=3\n");
  io::read_ini(is, t4);

  EXPECT_EQUAL(t4.i, 4711);
  EXPECT_EQUAL(t4.l[0], 1);
  EXPECT_EQUAL(t4.l[1], 2);
  EXPECT_EQUAL(t4.l[2], 3);
}

// --------------------------------------------------------------------------
void test_read_8 () {
  test5 t;
  std::istringstream is("i=Text 5\n"
                        "i.0=List item 1\n"
                        "i.1=List item 2\n");

  io::read_ini(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 5");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_9 () {
  test6 t;
  std::istringstream is("i=Text 6\n"
                        "i.0=List item 1\n"
                        "i.1=List item 2\n");

  io::read_ini(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 6");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_10 () {
  test5 t;
  std::istringstream is("i.0=List item 1\n"
                        "i.1=List item 2\n"
                        "i=Text 7\n");

  io::read_ini(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 7");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_11 () {
  test6 t;
  std::istringstream is("i.0=List item 1\n"
                        "i.1=List item 2\n"
                        "i=Text 8\n");

  io::read_ini(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 8");
  EXPECT_EQUAL(t.l, expected);

  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_write_1 () {
  int64_t i = 4711;
  std::ostringstream os;
  io::write_ini(os, attribute(i, "i"));

  EXPECT_EQUAL(os.str(), "i=4711\n");
}

// --------------------------------------------------------------------------
void test_write_2 () {
  test_int64 t1;
  std::ostringstream os;
  io::write_ini(os, t1);

  EXPECT_EQUAL(os.str(), "i=0\n"
                         "j=0\n");
}

// --------------------------------------------------------------------------
void test_write_3 () {
  test2 t2;
  std::ostringstream os;
  io::write_ini(os, t2);

  EXPECT_EQUAL(os.str(), "i1=0\n"
                         "t1.i=0\n"
                         "t1.j=0\n"
                         "i2=\n");
}

// --------------------------------------------------------------------------
void test_write_4 () {
  test3 t3;
  t3.v().push_back(test_int64());
  std::ostringstream os;
  io::write_ini(os, t3);

  EXPECT_EQUAL(os.str(), "v.0.i=0\n"
                         "v.0.j=0\n");
}

// --------------------------------------------------------------------------
void test_write_5 () {
  test4 t4(4711, {1, 2, 3});
  std::ostringstream os;
  io::write_ini(os, t4);

  EXPECT_EQUAL(os.str(), "i=4711\n"
                         "i.0=1\n"
                         "i.1=2\n"
                         "i.2=3\n"
               );
}

// --------------------------------------------------------------------------
void test_write_6 () {
  test5 t("Text 5", {"List item 1", "List item 2"});
  std::ostringstream os;
  io::write_ini(os, t);

  EXPECT_EQUAL(os.str(), "i=Text 5\n"
                         "i.0=List item 1\n"
                         "i.1=List item 2\n");
}

// --------------------------------------------------------------------------
void test_write_7 () {
  test6 t("Text 6", {"List item 1", "List item 2"});
  std::ostringstream os;
  io::write_ini(os, t);

  EXPECT_EQUAL(os.str(), "i.0=List item 1\n"
                         "i.1=List item 2\n"
                         "i=Text 6\n");
}

// --------------------------------------------------------------------------
void test_write_array () {

  std::array<int64_t, 5> a({1, 2, 3, 4, 5});
  std::ostringstream os;
  io::write_ini(os, attribute(a, "a"));
  EXPECT_EQUAL(os.str(), "a.0=1\n"
                         "a.1=2\n"
                         "a.2=3\n"
                         "a.3=4\n"
                         "a.4=5\n");
}
// --------------------------------------------------------------------------
void test_write_vector () {

  std::vector<int64_t> v({1, 2, 3, 4, 5});
  std::ostringstream os;
  io::write_ini(os, attribute(v, "v"));
  EXPECT_EQUAL(os.str(), "v.0=1\n"
                         "v.1=2\n"
                         "v.2=3\n"
                         "v.3=4\n"
                         "v.4=5\n");
}
// --------------------------------------------------------------------------
void test_write_pair () {
  test7 t("Any Text", 4711);
  std::ostringstream os;
  io::write_ini(os, t);

  EXPECT_EQUAL(os.str(), "v.0=Any Text\n"
                         "v.1=4711\n");
}
// --------------------------------------------------------------------------
void test_write_map () {
  std::map<std::string, double> m { { "one", 1 }, { "two", 2 }, { "three", 3 } };
  std::ostringstream os;
  io::write_ini(os, m);

  EXPECT_EQUAL(os.str(), "one=1\n"
                         "three=3\n"
                         "two=2\n");
}

// --------------------------------------------------------------------------
void test_main (const testing::start_params& params) {
  testing::log_info("Running " __FILE__);

  run_test(test_write_array);
  run_test(test_write_vector);
  run_test(test_write_pair);
  run_test(test_write_map);
  run_test(test_write_1);
  run_test(test_write_2);
  run_test(test_write_3);
  run_test(test_write_4);
  run_test(test_write_5);
  run_test(test_write_6);
  run_test(test_write_7);

  run_test(test_read_empty);
  run_test(test_read_all_basic_types);
  run_test(test_read_1);
  run_test(test_read_array);
  run_test(test_read_vector);
  run_test(test_read_pair);
  run_test(test_read_map);
  run_test(test_read_2);
  run_test(test_read_3);
  run_test(test_read_4);
  run_test(test_read_5);
  run_test(test_read_6);
  run_test(test_read_7);
  run_test(test_read_8a);
  run_test(test_read_8);
  run_test(test_read_9);
  run_test(test_read_10);
  run_test(test_read_11);

}

// --------------------------------------------------------------------------

