#include <functional>
#include <queue>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

struct TreeNode {
  int val;
  TreeNode* left;
  TreeNode* right;
  TreeNode() : val(0), left(nullptr), right(nullptr) {}
  TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
  TreeNode(int x, TreeNode* left, TreeNode* right)
      : val(x), left(left), right(right) {}
};

const string nilToken = "null";

template <typename T>
string vectorToString(vector<T> v) {
  auto i = v.begin();
  ostringstream ans;
  ans << "[";
  for (; i != v.end(); ++i) {
    ans << *i;
    if (i + 1 != v.end()) {
      ans << ",";
    }
  }
  ans << "]";
  return ans.str();
}

vector<string> stringToVector(string str) {
  str = str.substr(1, str.size() - 2);
  istringstream ss(str);
  string token;
  vector<string> ans;
  while (getline(ss, token, ',')) {
    ans.push_back(token);
  }
  return ans;
}

TreeNode* deserialize(string str) {
  auto v = stringToVector(str);
  if (v.empty()) {
    return nullptr;
  }
  queue<TreeNode*> q;
  auto root = new TreeNode(stoi(v[0]));
  q.push(root);
  for (int i = 1, N = v.size(); i < N;) {
    auto node = q.front();
    q.pop();
    if (v[i] != nilToken) {
      q.push(node->left = new TreeNode(stoi(v[i])));
    }
    ++i;
    if (i < N && v[i] != nilToken) {
      q.push(node->right = new TreeNode(stoi(v[i])));
    }
    ++i;
  }
  return root;
}

string serialize(TreeNode* root) {
  vector<string> v;
  if (!root) {
    return vectorToString(v);
  }
  queue<TreeNode*> q;
  q.push(root);
  while (q.size()) {
    root = q.front();
    q.pop();
    if (root) {
      v.push_back(to_string(root->val));
      q.push(root->left);
      q.push(root->right);
    } else
      v.push_back(nilToken);
  }
  while (v.back() == nilToken) {
    v.pop_back();
  }
  return vectorToString(v);
}

vector<vector<int>> print(TreeNode* node) {
  vector<vector<int>> ans;
  function<void(TreeNode*, int)> traverse;

  traverse = [&ans, &traverse](TreeNode* root, int depth) {
    if (root == nullptr) {
      return;
    }

    if (ans.size() == depth) {
      ans.resize(depth + 1);
    }

    ans[depth].push_back(root->val);
    traverse(root->left, depth + 1);
    traverse(root->right, depth + 1);
  };
  traverse(node, 0);
  return ans;
}
