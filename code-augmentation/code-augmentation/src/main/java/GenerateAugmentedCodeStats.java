public class GenerateAugmentedCodeStats
{
    public GenerateAugmentedCodeStats(GenerateAugmentedCodeResult r)
    {
        generatedMethodsCount = r.generatedMethods.size();
        firstAttemptSwapOperandsChanges = r.firstAttemptSwapOperandsChanges;
        firstAttemptRenameVariableChanges = r.firstAttemptRenameVariableChanges;
        firstAttemptSwapStatementsChanges = r.firstAttemptSwapStatementsChanges;
        parseFailed = r.parseFailed;
    }
    public int generatedMethodsCount = 0;
    public int firstAttemptSwapOperandsChanges = 0;
    public int firstAttemptRenameVariableChanges = 0;
    public int firstAttemptSwapStatementsChanges = 0;
    public boolean parseFailed = false;
}