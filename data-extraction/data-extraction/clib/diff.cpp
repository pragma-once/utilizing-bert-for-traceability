// clang++ -c -Wall -Werror -fpic diff.cpp -O2 -std=c++20 && clang++ -shared -o diff.so diff.o

#include <cstdint>
#include <map>
#include <vector>

struct sha256
{
public:
    std::int64_t data0;
    std::int64_t data1;
    std::int64_t data2;
    std::int64_t data3;
    auto operator<=>(const sha256&) const = default;
};

struct history_item
{
public:
    int x, y, change;
    history_item(int x, int y, int change) : x(x), y(y), change(change) {}
};

struct Frontier
{
public:
    int x;
    std::vector<history_item> history;
    Frontier() : x(0) {}
    Frontier(int x, std::vector<history_item> history) : x(x), history(history) {}
};

/// The algorithm Myers presents is 1-indexed; since C++ isn't, we
/// need a conversion.
inline int one(int idx)
{
    return idx - 1;
}

extern "C"
{
    void diff(
        sha256 * old_items_hash,
        sha256 * new_items_hash,
        std::int64_t old_items_size,
        std::int64_t new_items_size,
        std::int64_t * removed_items_output,
        std::int64_t * added_items_output
    )
    {
        // Based on:
        // https://gist.github.com/adamnew123456/37923cf53f51d6b9af32a539cdfa7cc4

        std::map<int, Frontier> frontier;
        frontier[1] = Frontier(0, std::vector<history_item>());

        int a_max = (int)old_items_size;
        int b_max = (int)new_items_size;

        int d_len = a_max + b_max + 1;
        for (int d = 0; d < d_len; d++)
        {
            for (int k = -d; k <= d; k += 2)
            {
                bool go_down = (k == -d or (k != d and frontier[k - 1].x < frontier[k + 1].x));

                int old_x;
                int x;
                std::vector<history_item> history;
                if (go_down)
                {
                    old_x = frontier[k + 1].x;
                    history = frontier[k + 1].history;
                    x = old_x;
                }
                else
                {
                    old_x = frontier[k - 1].x;
                    history = frontier[k - 1].history;
                    x = old_x + 1;
                }

                int y = x - k;

                if (1 <= y and y <= b_max and go_down)
                    history.push_back(history_item(one(x), one(y), 2)); // insert
                else if (1 <= x and x <= a_max)
                    history.push_back(history_item(one(x), one(y), 1)); // remove

                while (x < a_max and y < b_max and old_items_hash[one(x + 1)] == new_items_hash[one(y + 1)])
                {
                    x += 1;
                    y += 1;
                    history.push_back(history_item(one(x), one(y), 0)); // keep
                }

                if (x >= a_max and y >= b_max)
                {
                    // done
                    int rindex = 0;
                    int aindex = 0;
                    for (auto item : history)
                    {
                        if (item.change == 1)
                        {
                            int removed_index = item.x;
                            removed_items_output[rindex++] = removed_index;
                        }
                        if (item.change == 2)
                        {
                            int added_index = item.y;
                            added_items_output[aindex++] = added_index;
                        }
                    }
                    while (rindex < old_items_size)
                        removed_items_output[rindex++] = -1;
                    while (aindex < new_items_size)
                        added_items_output[aindex++] = -1;
                    return;
                }
                else
                {
                    frontier[k] = Frontier(x, history);
                }
            }
        }
        for (int i = 0; i < old_items_size; i++)
            removed_items_output[i] = -1;
        for (int i = 0; i < new_items_size; i++)
            added_items_output[i] = -1;
    }
}
