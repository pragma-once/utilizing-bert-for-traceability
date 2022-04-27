import java.util.HashMap;

public class CountOfNumbers
{
    void increment(int number)
    {
        if (count.size() == 0)
        {
            minNumber = number;
            maxNumber = number;
        }

        if (number < minNumber)
            minNumber = number;
        if (number > maxNumber)
            maxNumber = number;

        if (!count.containsKey(number))
            count.put(number, 0);
        count.put(number, count.get(number) + 1);
    }

    public String toCSV()
    {
        StringBuilder result = new StringBuilder();
        result.append(minNumber);
        for (int i = minNumber + 1; i <= maxNumber; i++)
        {
            result.append(",").append(i);
        }
        result.append("\n");
        result.append(count.getOrDefault(minNumber, 0));
        for (int i = minNumber + 1; i <= maxNumber; i++)
        {
            result.append(",").append(count.getOrDefault(i, 0));
        }
        return result.toString();
    }

    @Override
    public String toString()
    {
        StringBuilder result = new StringBuilder();
        result.append(minNumber);
        result.append(": ");
        result.append(count.getOrDefault(minNumber, 0));
        int step = 1;
        if (maxNumber - minNumber > 50)
            step = (maxNumber - minNumber) / 50;
        for (int i = minNumber + 1; i <= maxNumber; i += step)
        {
            int sum = 0;
            for (int j = 0; j < step; j++)
                sum += count.getOrDefault(i + j, 0);
            result.append(", ").append(step == 1 ? i : (i + "-" + (i + step - 1)));
            result.append(": ");
            result.append(sum);
        }
        return result.toString();
    }

    private final HashMap<Integer, Integer> count = new HashMap<>();
    private int minNumber = 0;
    private int maxNumber = 0;
}
