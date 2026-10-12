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

#include "persistent_xml.h"
#include <testing/testing.h>

#include "test_structs.h"

std::string build_xml (const std::string& t) {
  std::ostringstream os;
  os << io::xml::s_header;
  os << io::xml::s_body;
  os << t;
  os << io::xml::s_nbody;
  return os.str();
}

// --------------------------------------------------------------------------
void test_read_empty () {

  test_int64 t1;
  std::istringstream is(build_xml("<t></t>"));
  auto at = attribute(t1, "t");
  io::read_xml(is, at);

  EXPECT_EQUAL(t1.i, 0);
  EXPECT_EQUAL(t1.j, 0);
  EXPECT_TRUE(is.good());
  is >> std::ws;
  EXPECT_FALSE(is.good());
  EXPECT_TRUE(is.eof());
}

// --------------------------------------------------------------------------
template<typename T>
void test_read_prop_type () {
  const auto expected = get_test_data<T>();
  std::string test_value = expected.first;
  test_value.erase(remove(test_value.begin(), test_value.end(), '\"'), test_value.end());

  const std::string str = io::msg_fmt() << "<i>" << test_value << "</i>";

  T value = {};
  std::istringstream is(build_xml(str));
  auto at = attribute(value, "i");
  io::read_xml(is, at);

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
  std::istringstream is(build_xml("<a><ol><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li></ol></a>"));
  auto at = attribute(a, "a");
  io::read_xml(is, at);

  std::array<int64_t, 5> expected = {1, 2, 3, 4, 5};
  EXPECT_EQUAL(a, expected);
}
// --------------------------------------------------------------------------
void test_read_vector () {

  std::vector<int64_t> v;
  std::istringstream is(build_xml("<v><ol><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li></ol></v>"));
  auto at = attribute(v, "v");
  io::read_xml(is, at);

  std::vector<int64_t> expected = {1, 2, 3, 4, 5};
  EXPECT_EQUAL(v, expected);
}
// --------------------------------------------------------------------------
void test_read_pair () {
  test7 t;
  std::istringstream is(build_xml("<v><ol><li>Any Text</li><li>4711</li></ol></v>"));
  io::read_xml(is, t);
  EXPECT_EQUAL(t.p.first, "Any Text");
  EXPECT_EQUAL(t.p.second, 4711);
  is >> std::ws;
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}
// --------------------------------------------------------------------------
void test_read_map () {
  std::istringstream is(build_xml("<one>1</one><three>3</three><two>2</two>"));
  std::map<std::string, double> m;
  io::read_xml(is, m);
  std::map<std::string, double> expected { { "one", 1 }, { "two", 2 }, { "three", 3 } };
  EXPECT_EQUAL(m, expected);
}

// --------------------------------------------------------------------------
void test_read_1 () {
  int64_t i= 0;
  std::istringstream is(build_xml("<i>4711</i>"));
  auto at = attribute(i, "i");
  io::read_xml(is, at);

  EXPECT_EQUAL(i, 4711);
  is >> std::ws;
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_2 () {

  test_int64 t1;
  std::istringstream is(build_xml("<t><i>4711</i><j>815</j></t>"));
  auto at = attribute(t1, "t");
  io::read_xml(is, at);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 815);
  is >> std::ws;
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_3 () {
  test_int64 t1;
  std::istringstream is(build_xml("<t><i>4711</i></t>"));
  auto at = attribute(t1, "t");
  io::read_xml(is, at);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 0);
  is >> std::ws;
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_4 () {
  test_int64 t1;
  std::istringstream is(build_xml(" \n \t <t> \n \t <i> \n \t \n \t 4711 \n \t </i> \n \t </t> \n \t "));
  auto at = attribute(t1, "t");
  io::read_xml(is, at);

  EXPECT_EQUAL(t1.i, 4711);
  EXPECT_EQUAL(t1.j, 0);
  is >> std::ws;
  EXPECT_TRUE(is.eof());
  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_5 () {
  test2 t2;
  std::istringstream is(build_xml("<t2><i1>815</i1><t1><i>911</i><j>203</j></t1><i2>4711</i2></t2>"));
  auto at = attribute(t2, "t2");
  io::read_xml(is, at);

  EXPECT_EQUAL(t2.i1, 815);
  EXPECT_EQUAL(t2.t1.i, 911);
  EXPECT_EQUAL(t2.t1.j, 203);
  EXPECT_EQUAL(*(t2.i2), 4711);
}

// --------------------------------------------------------------------------
void test_read_6 () {
  test_int64 t1;
  std::istringstream is(build_xml("<t1><i>4711</i><k>815</k></t1>"));
  try {
    auto at = attribute(t1, "t1");
    io::read_xml(is, at);
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
  std::istringstream is(build_xml("<t2><v><ol><li><i>1</i><j>2</j></li><li><i>3</i><j>4</j></li><li><i>5</i><j>6</j></li></ol></v></t2>"));
  auto at = attribute(t3, "t3");
  io::read_xml(is, at);

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
  std::istringstream is(build_xml("<i>Text 5</i><i><ol><li>List item 1</li><li>List item 2</li></ol></i>"));
  io::read_xml(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 5");
  EXPECT_EQUAL(t.l, expected);

//  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_9 () {
  test6 t;
  std::istringstream is(build_xml("<i>Text 6</i><i><ol><li>List item 1</li><li>List item 2</li></ol></i>"));
  io::read_xml(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 6");
  EXPECT_EQUAL(t.l, expected);

//  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_10 () {
  test5 t;
  std::istringstream is(build_xml("<i><ol><li>List item 1</li><li>List item 2</li></ol></i><i>Text 7</i>"));
  io::read_xml(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 7");
  EXPECT_EQUAL(t.l, expected);

//  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_read_11 () {
  test6 t;
  std::istringstream is(build_xml("<i><ol><li>List item 1</li><li>List item 2</li></ol></i><i>Text 8</i>"));
  io::read_xml(is, t);

  std::vector<std::string> expected({"List item 1", "List item 2"});

  EXPECT_EQUAL(t.i, "Text 8");
  EXPECT_EQUAL(t.l, expected);

//  EXPECT_FALSE(is.good());
}

// --------------------------------------------------------------------------
void test_write_1 () {
  int64_t i = 4711;
  std::ostringstream os;
  io::write_xml(os, attribute(i, "i"), false);

  auto expected = build_xml("<i>4711</i>");
  EXPECT_EQUAL(os.str(), expected);
}

// --------------------------------------------------------------------------
void test_write_2 () {
  test_int64 t1;
  std::ostringstream os;
  io::write_xml(os, t1, false);

  auto expected = build_xml("<i>0</i><j>0</j>");
  EXPECT_EQUAL(os.str(), expected);
}

// --------------------------------------------------------------------------
void test_write_3 () {
  test2 t2;
  std::ostringstream os;
  io::write_xml(os, t2, false);

  auto expected = build_xml("<i1>0</i1><t1><i>0</i><j>0</j></t1><i2></i2>");
  EXPECT_EQUAL(os.str(), expected);
}

// --------------------------------------------------------------------------
void test_write_4 () {
  test3 t3;
  t3.v().push_back(test_int64());
  std::ostringstream os;
  io::write_xml(os, t3, false);

  auto expected = build_xml("<v><ol><li><i>0</i><j>0</j></li></ol></v>");
  EXPECT_EQUAL(os.str(), expected);
}

// --------------------------------------------------------------------------
void test_write_5 () {
  test5 t("Text 5", {"List item 1", "List item 2"});
  std::ostringstream os;
  io::write_xml(os, t, false);

  auto expected = build_xml("<i>Text 5</i><i><ol><li>List item 1</li><li>List item 2</li></ol></i>");
  EXPECT_EQUAL(os.str(), expected);
}

// --------------------------------------------------------------------------
void test_write_6 () {
  test6 t("Text 6", {"List item 1", "List item 2"});
  std::ostringstream os;
  io::write_xml(os, t, false);

  auto expected = build_xml("<i><ol><li>List item 1</li><li>List item 2</li></ol></i><i>Text 6</i>");
  EXPECT_EQUAL(os.str(), expected);
}

// --------------------------------------------------------------------------
void test_write_array () {

  std::array<int64_t, 5> a({1, 2, 3, 4, 5});
  std::ostringstream os;
  io::write_xml(os, attribute(a, "a"), false);

  auto expected = build_xml("<a><ol><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li></ol></a>");
  EXPECT_EQUAL(os.str(), expected);
}
// --------------------------------------------------------------------------
void test_write_vector () {

  std::vector<int64_t> v({1, 2, 3, 4, 5});
  std::ostringstream os;
  io::write_xml(os, attribute(v, "v"), false);
  auto expected = build_xml("<v><ol><li>1</li><li>2</li><li>3</li><li>4</li><li>5</li></ol></v>");
  EXPECT_EQUAL(os.str(), expected);
}
// --------------------------------------------------------------------------
void test_write_pair () {
  test7 t("Any Text", 4711);
  std::ostringstream os;
  io::write_xml(os, t, false);
  auto expected = build_xml("<v><ol><li>Any Text</li><li>4711</li></ol></v>");
  EXPECT_EQUAL(os.str(), expected);
}
// --------------------------------------------------------------------------
void test_write_map () {
  std::map<std::string, double> m { { "one", 1 }, { "two", 2 }, { "three", 3 } };
  std::ostringstream os;
  io::write_xml(os, m, false);
  auto expected = build_xml("<one>1</one><three>3</three><two>2</two>");
  EXPECT_EQUAL(os.str(), expected);
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
  run_test(test_write_1);
  run_test(test_write_2);
  run_test(test_write_3);
  run_test(test_write_4);
  run_test(test_write_5);
  run_test(test_write_6);
}

// --------------------------------------------------------------------------

