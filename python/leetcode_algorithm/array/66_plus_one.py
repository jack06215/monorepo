import unittest
from typing import List


class Solution:
    def plusOne(self, digits: List[int]) -> List[int]:
        n = len(digits)

        # Process each digit starting from the end
        for i in range(n - 1, -1, -1):
            if digits[i] < 9:
                # If the current digit is less than 9, just increment it and return
                digits[i] += 1
                return digits
            # If the digit is 9, set it to 0 (because 9 + 1 = 10)
            digits[i] = 0

        # If all digits are 9, the array will be all zeros and we need an
        # additional digit at the start
        return [1] + digits


class TestPlusOne(unittest.TestCase):
    def setUp(self) -> None:
        self.solution = Solution()

    def test_example_1(self) -> None:
        self.assertEqual(self.solution.plusOne([1, 2, 3]), [1, 2, 4])

    def test_example_2(self) -> None:
        self.assertEqual(self.solution.plusOne([4, 3, 2, 1]), [4, 3, 2, 2])

    def test_example_3(self) -> None:
        self.assertEqual(self.solution.plusOne([9]), [1, 0])

    def test_single_digit_no_carry(self) -> None:
        self.assertEqual(self.solution.plusOne([0]), [1])

    def test_all_nines_carries_into_new_leading_digit(self) -> None:
        self.assertEqual(self.solution.plusOne([9, 9, 9]), [1, 0, 0, 0])

    def test_trailing_nines_carry_partway(self) -> None:
        self.assertEqual(self.solution.plusOne([1, 9, 9]), [2, 0, 0])

    def test_no_carry_needed(self) -> None:
        self.assertEqual(self.solution.plusOne([1, 2, 3, 4]), [1, 2, 3, 5])


if __name__ == "__main__":
    unittest.main()
