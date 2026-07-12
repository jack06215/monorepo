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


def main() -> None:
    solution = Solution()
    digits = [4, 3, 2, 1]  # Example input
    result = solution.plusOne(digits)

    # Print the result
    print("".join(str(digit) for digit in result))


if __name__ == "__main__":
    main()
