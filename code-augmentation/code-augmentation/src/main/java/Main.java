public class Main
{
    public static void main(String[] args)
    {
        System.out.println("\nSWAP OPERANDS TEST\n");
        CodeAugmentation.swapRandomOperandPairsTest(10, 0.75);
        System.out.println("\nRENAME VARIABLE TEST\n");
        CodeAugmentation.renameRandomVariablesTest(10, 0.75);
        System.out.println("\nSWAP STATEMENTS TEST\n");
        CodeAugmentation.swapRandomStatementsInBlocksTest(10, 2);
    }
}
