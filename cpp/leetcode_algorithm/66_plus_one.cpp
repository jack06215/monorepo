#include <iostream>
#include <vector>
#include "prettyprint.h"

using namespace std;

class Solution {
public:
    vector<int> plusOne(vector<int>& digits) {
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

        // If all digits are 9, the array will be all zeros and we need an additional digit at the start
        vector<int> newDigits(n + 1);
        newDigits[0] = 1; // The only non-zero digit, which is the new leading digit
        return newDigits;
    }
};

int main() {
    Solution solution;
    vector<int> digits = { 4, 3, 2, 1 }; // Example input
    vector<int> result = solution.plusOne(digits);

    // Print the result
    for (int digit : result) {
        cout << digit;
    }
    cout << endl;

    return 0;
}
