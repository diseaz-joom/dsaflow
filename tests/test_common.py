#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import logging
import unittest

from jf import common


_logger = logging.getLogger(__name__)


class TestStruct(unittest.TestCase):
    def test_kwargs(self):
        s = common.Struct(x=42)
        self.assertEqual({'x': 42}, s)
        self.assertEqual(42, s.x)

    def test_from_dict(self):
        s = common.Struct.from_dict({'x': 42})
        self.assertEqual({'x': 42}, s)
        self.assertEqual(42, s.x)

    def test_copy(self):
        s = common.Struct(x=42)
        t = s.copy()
        self.assertEqual(s, t)
        self.assertIsNot(s, t)
        self.assertEqual(42, t.x)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
