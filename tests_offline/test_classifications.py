import unittest

from mgci.infrastructure.classifications import parse_classification


class ClassificationTests(unittest.TestCase):
    def test_custom_codes_and_labels_are_canonical(self):
        self.assertEqual(parse_classification(b'lc_class,desc,color\n7,Trees,#008800\n2,Land,#123456\n'),
                         ((2, 'Land', '#123456'), (7, 'Trees', '#008800')))

    def test_duplicate_fractional_and_out_of_range_codes_are_rejected(self):
        for rows in ('1,A,#123456\n1.0,B,#123456', '2.1,A,#123456', '100,A,#123456', '1,A,red'):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                parse_classification(('lc_class,desc,color\n' + rows).encode())
