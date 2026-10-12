import unittest

from opulence.python_template.feature import add, multiply


class TestFeature(unittest.TestCase):
    def setUp(self):
        # Allow to declare variables/objects/whatever used
        # in several tests.
        self.a = 1
        self.b = 2
        self.a_plus_b = 3
        self.a_times_b = 2

    def test_add(self):
        self.assertEqual(add(self.a, self.b), self.a_plus_b)

    def test_multiply(self):
        self.assertEqual(multiply(self.a, self.b), self.a_times_b)

    def tearDown(self):
        # Nothing here.
        # In general, clean all variables/objects/whatever
        # created for the tests.
        return
