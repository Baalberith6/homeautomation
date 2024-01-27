import unittest

from estia_energy import calculate_cop


class TestEstiaEnergy(unittest.TestCase):

    def test_new(self):
        self.assertEqual(2, calculate_cop(0, 1287, 0, 0)) # 18 * 143 = 2574, 2574 / 1287 = 2

    def test_continuous(self):
        self.assertEqual(2.6153846153846154, calculate_cop(1287, 572, 2, 2))  # 2574 + (16 * 143) / 1859 = 2.615
        self.assertEqual(3, calculate_cop(1859, 143, 2.6153846153846154, 10))  # 2574 + 2288 + (8 * 143) / 2002 = 3

if __name__ == '__main__':
    unittest.main()
