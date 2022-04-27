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
    }

    @Override
    public String toString()
    {
        return "parse failed: " +
                parseFailsCount +
                "\ncode augmentation rounds:\n" +
                actualRoundsCounts +
                "\nfirst attempt swap operands changes:\n" +
                firstSwapOperandsChangesCounts +
                "\nfirst attempt rename variable changes:\n" +
                firstRenameVariableChangesCounts +
                "\nfirst attempt swap statements changes:\n" +
                firstSwapStatementsChangesCounts;
    }

    private int parseFailsCount = 0;
    // Non-failed cases:
    private final CountOfNumbers actualRoundsCounts = new CountOfNumbers();
    private final CountOfNumbers firstSwapOperandsChangesCounts = new CountOfNumbers();
    private final CountOfNumbers firstRenameVariableChangesCounts = new CountOfNumbers();
    private final CountOfNumbers firstSwapStatementsChangesCounts = new CountOfNumbers();
}
