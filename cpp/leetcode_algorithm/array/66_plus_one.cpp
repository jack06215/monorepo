#include <vector>

#define CATCH_CONFIG_MAIN
#include "../catch.hpp"

class Solution {
 public:
  std::vector<int> plusOne(std::vector<int>& digits) {
    int n = digits.size();

    // Process each digit starting from the end
    for (int i = n - 1; i >= 0; --i) {
      if (digits[i] < 9) {
        // If the current digit is less than 9, just increment it and return
        digits[i]++;
        return digits;
      }
      // If the digit is 9, set it to 0 (because 9 + 1 = 10)
      digits[i] = 0;
    }

    // If all digits are 9, the array will be all zeros and we need an
    // additional digit at the start
    std::vector<int> newDigits(n + 1);
    newDigits[0] =
        1;  // The only non-zero digit, which is the new leading digit
    return newDigits;
  }
};

TEST_CASE("plusOne handles the LeetCode examples", "[plusOne]") {
  Solution solution;

  SECTION("example 1") {
    std::vector<int> digits = {1, 2, 3};
    std::vector<int> expected = {1, 2, 4};
    REQUIRE(solution.plusOne(digits) == expected);
  }

  SECTION("example 2") {
    std::vector<int> digits = {4, 3, 2, 1};
    std::vector<int> expected = {4, 3, 2, 2};
    REQUIRE(solution.plusOne(digits) == expected);
  }

  SECTION("example 3") {
    std::vector<int> digits = {9};
    std::vector<int> expected = {1, 0};
    REQUIRE(solution.plusOne(digits) == expected);
  }
}

TEST_CASE("plusOne handles edge cases", "[plusOne]") {
  Solution solution;

  SECTION("single digit no carry") {
    std::vector<int> digits = {0};
    std::vector<int> expected = {1};
    REQUIRE(solution.plusOne(digits) == expected);
  }

  SECTION("all nines carries into a new leading digit") {
    std::vector<int> digits = {9, 9, 9};
    std::vector<int> expected = {1, 0, 0, 0};
    REQUIRE(solution.plusOne(digits) == expected);
  }

  SECTION("trailing nines carry partway") {
    std::vector<int> digits = {1, 9, 9};
    std::vector<int> expected = {2, 0, 0};
    REQUIRE(solution.plusOne(digits) == expected);
  }

  SECTION("no carry needed") {
    std::vector<int> digits = {1, 2, 3, 4};
    std::vector<int> expected = {1, 2, 3, 5};
    REQUIRE(solution.plusOne(digits) == expected);
  }
}
