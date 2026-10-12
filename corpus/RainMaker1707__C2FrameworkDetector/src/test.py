from pipeline import *

import unittest


VERSION = 0.1
NAME = "test_pipeline"

class TestMethod(unittest.TestCase):
    def test_config_load(self):
        config_file = "configs.json"
        configs = load_config(config_file)
        self.assertEqual(configs.get("version"), VERSION)
        self.assertEqual(configs.get("name"), NAME)

    def test_splitter(self):
        pass
    
    def test_filler(self):
        pass



class TestScoring(unittest.TestCase):
    def test_scoring(self):
        pass

    def test_csv_to_tab(self):
        pass

    def test_precision(self):
        pass

    def test_recall(self):
        pass

    def test_f1(self):
        pass


class TestPipeline(unittest.TestCase):
    def test_pipeline(self):
        pass



if __name__ == "__main__":
    unittest.main()

