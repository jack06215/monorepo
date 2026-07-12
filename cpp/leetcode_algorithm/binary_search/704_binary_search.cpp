#include <vector>

#define CATCH_CONFIG_MAIN
#include "../catch.hpp"

class Solution {
 public:
  int search(std::vector<int>& nums, int target) {
    int left = 0;
    int right = nums.size();

    while (left < right) {
      int mid = left + (right - left) / 2;
      if (nums[mid] == target) {
        return mid;
      } else if (nums[mid] > target) {
        right = mid;
      } else {
        left = mid + 1;
      }
    }
    return -1;
  }
};

TEST_CASE("search handles the LeetCode examples", "[search]") {
  Solution solution;

  SECTION("example 1") {
    std::vector<int> nums = {-1, 0, 3, 5, 9, 12};
    REQUIRE(solution.search(nums, 9) == 4);
  }

  SECTION("example 2") {
    std::vector<int> nums = {-1, 0, 3, 5, 9, 12};
    REQUIRE(solution.search(nums, 2) == -1);
  }
}

TEST_CASE("search handles edge cases", "[search]") {
  Solution solution;

  SECTION("empty array") {
    std::vector<int> nums = {};
    REQUIRE(solution.search(nums, 5) == -1);
  }

  SECTION("single element found") {
    std::vector<int> nums = {5};
    REQUIRE(solution.search(nums, 5) == 0);
  }

  SECTION("single element not found") {
    std::vector<int> nums = {5};
    REQUIRE(solution.search(nums, 1) == -1);
  }

  SECTION("target at first index") {
    std::vector<int> nums = {1, 3, 5, 7, 9};
    REQUIRE(solution.search(nums, 1) == 0);
  }

  SECTION("target at last index") {
    std::vector<int> nums = {1, 3, 5, 7, 9};
    REQUIRE(solution.search(nums, 9) == 4);
  }

  SECTION("target smaller than all elements") {
    std::vector<int> nums = {1, 3, 5, 7, 9};
    REQUIRE(solution.search(nums, 0) == -1);
  }

  SECTION("target larger than all elements") {
    std::vector<int> nums = {1, 3, 5, 7, 9};
    REQUIRE(solution.search(nums, 10) == -1);
  }
}
