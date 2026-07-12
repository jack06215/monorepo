#include <limits>
#include <vector>

#define CATCH_CONFIG_MAIN
#include "../catch.hpp"

using namespace std;

class Solution {
 public:
  int maxArea(vector<int>& height) {
    int left = 0;
    int right = height.size() - 1;
    int max_area = numeric_limits<int>::min();

    while (left < right) {
      int left_h = height[left];
      int right_h = height[right];

      max_area = max(max_area, (right - left) * min(right_h, left_h));

      if (left_h < right_h) {
        ++left;
      } else {
        --right;
      }
    }
    return max_area;
  }
};

TEST_CASE("maxArea handles the LeetCode examples", "[maxArea]") {
  Solution solution;

  SECTION("example 1") {
    vector<int> height = {1, 8, 6, 2, 5, 4, 8, 3, 7};
    REQUIRE(solution.maxArea(height) == 49);
  }

  SECTION("example 2") {
    vector<int> height = {1, 1};
    REQUIRE(solution.maxArea(height) == 1);
  }
}

TEST_CASE("maxArea handles edge cases", "[maxArea]") {
  Solution solution;

  SECTION("two elements") {
    vector<int> height = {4, 3};
    REQUIRE(solution.maxArea(height) == 3);
  }

  SECTION("strictly increasing heights") {
    vector<int> height = {1, 2, 3, 4, 5};
    REQUIRE(solution.maxArea(height) == 6);
  }

  SECTION("strictly decreasing heights") {
    vector<int> height = {5, 4, 3, 2, 1};
    REQUIRE(solution.maxArea(height) == 6);
  }

  SECTION("all equal heights") {
    vector<int> height = {3, 3, 3, 3, 3};
    REQUIRE(solution.maxArea(height) == 12);
  }

  SECTION("zero height at boundary") {
    vector<int> height = {0, 2};
    REQUIRE(solution.maxArea(height) == 0);
  }
}
