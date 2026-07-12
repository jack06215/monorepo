import unittest
from typing import List


class Solution:
    def search(self, nums: List[int], target: int) -> int:
        left = 0
        right = len(nums)

        while left < right:
            mid = left + (right - left) // 2
            if nums[mid] == target:
                return mid
            elif nums[mid] > target:
                right = mid
            else:
                left = mid + 1
        return -1


class TestSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.solution = Solution()

    def test_example_1(self) -> None:
        self.assertEqual(self.solution.search([-1, 0, 3, 5, 9, 12], 9), 4)

    def test_example_2(self) -> None:
        self.assertEqual(self.solution.search([-1, 0, 3, 5, 9, 12], 2), -1)

    def test_empty_array(self) -> None:
        self.assertEqual(self.solution.search([], 5), -1)

    def test_single_element_found(self) -> None:
        self.assertEqual(self.solution.search([5], 5), 0)

    def test_single_element_not_found(self) -> None:
        self.assertEqual(self.solution.search([5], 1), -1)

    def test_target_at_first_index(self) -> None:
        self.assertEqual(self.solution.search([1, 3, 5, 7, 9], 1), 0)

    def test_target_at_last_index(self) -> None:
        self.assertEqual(self.solution.search([1, 3, 5, 7, 9], 9), 4)

    def test_target_smaller_than_all_elements(self) -> None:
        self.assertEqual(self.solution.search([1, 3, 5, 7, 9], 0), -1)

    def test_target_larger_than_all_elements(self) -> None:
        self.assertEqual(self.solution.search([1, 3, 5, 7, 9], 10), -1)


if __name__ == "__main__":
    unittest.main()
