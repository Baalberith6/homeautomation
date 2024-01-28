import unittest

from estia_energy import calculate_cop


class TestEstiaEnergy(unittest.TestCase):

    def test(self):
        self.assertEqual(0, calculate_cop([0, 0, 0], [0,0,0]))
        self.assertEqual(2, calculate_cop([1287, 1, 0], [0, 0, 0])) # 18 * 143 = 2574, 2574 / 1287 = 2
        self.assertEqual(2.6153846153846154, calculate_cop([1287, 572, 1], [0, 2, 0]))  # 2574 + (16 * 143) / 1859 = 2.615
        self.assertEqual(3, calculate_cop([1287, 572, 143, 1], [0, 2, 10, 0]))  # 2574 + 2288 + (8 * 143) / 2002 = 3
        self.assertEqual(0.468, calculate_cop([1000, 10000, 1], [0, 0, 1]))
        self.assertEqual(2, calculate_cop([0, 1287, 100, 0], [18, 0, 0, 0])) # 18 * 143 = 2574, 2574 / 1287 = 2

if __name__ == '__main__':
    unittest.main()