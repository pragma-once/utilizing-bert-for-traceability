import java.util.ArrayList;

public class CodeAugmentationStatistics
{
    public void record(GenerateAugmentedCodeResult data)
    {
        if (data.parseFailed)
        {
            parseFailsCount++;
            return;
        }
        actualRoundsCounts.increment(data.generatedMethods.size());
        firstSwapOperandsChangesCounts.increment(data.firstAttemptSwapOperandsChanges);
        firstRenameVariableChangesCounts.increment(data.firstAttemptRenameVariableChanges);
        firstSwapStatementsChangesCounts.increment(data.firstAttemptSwapStatementsChanges);
        allAugmentationResults.add(new GenerateAugmentedCodeStats(data));
    }

    @Override
    public String toString()
    {
        return "parse failed: " +
                parseFailsCount +
                "\ncode augmentation rounds (number of generated methods) (rounds: count):\n" +
                actualRoundsCounts +
                "\nfirst attempt swap operands changes (changes: count):\n" +
                firstSwapOperandsChangesCounts +
                "\nfirst attempt rename variable changes (changes: count):\n" +
                firstRenameVariableChangesCounts +
                "\nfirst attempt swap statements changes (changes: count):\n" +
                firstSwapStatementsChangesCounts;
    }

    public String toCSV()
    {
        StringBuilder result = new StringBuilder();
        result.append("parse_failed,");
        result.append("generated_methods_count,");
        result.append("first_attempt_swap_operands_changes,");
        result.append("first_attempt_rename_variable_changes,");
        result.append("first_attempt_swap_statements_changes");
        for (GenerateAugmentedCodeStats stats : allAugmentationResults)
        {
            result.append("\n");
            result.append(stats.parseFailed ? "1" : "0");
            result.append(",").append(stats.generatedMethodsCount);
            result.append(",").append(stats.firstAttemptSwapOperandsChanges);
            result.append(",").append(stats.firstAttemptRenameVariableChanges);
            result.append(",").append(stats.firstAttemptSwapStatementsChanges);
        }
        return result.toString();
    }

    int parseFailsCount = 0;
    // Non-failed cases:
    final CountOfNumbers actualRoundsCounts = new CountOfNumbers();
    final CountOfNumbers firstSwapOperandsChangesCounts = new CountOfNumbers();
    final CountOfNumbers firstRenameVariableChangesCounts = new CountOfNumbers();
    final CountOfNumbers firstSwapStatementsChangesCounts = new CountOfNumbers();
    final ArrayList<GenerateAugmentedCodeStats> allAugmentationResults = new ArrayList<>();
}
