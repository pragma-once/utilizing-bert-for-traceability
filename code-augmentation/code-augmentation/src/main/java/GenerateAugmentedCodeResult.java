import java.util.ArrayList;

public class GenerateAugmentedCodeResult
{
    public ArrayList<String> generatedMethods = new ArrayList<>();
    public int firstAttemptSwapOperandsChanges = 0;
    public int firstAttemptRenameVariableChanges = 0;
    public int firstAttemptSwapStatementsChanges = 0;
    public boolean parseFailed = false;
}
