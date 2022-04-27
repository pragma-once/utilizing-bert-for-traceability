import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.body.MethodDeclaration;
import org.json.JSONObject;

import java.io.*;
import java.util.*;

public class Main
{
    public static void main(String[] args)
    {
        Scanner reader = new Scanner(System.in);
        System.out.println("ATTENTION: Keep a backup of the original files somewhere else.");
        System.out.println("ATTENTION: Do the operation in a separate folder.");
        System.out.println("Enter the jsonl filename fraction before '<number>.jsonl':");
        String inputFilenameStart = reader.nextLine();

        int inputFilesCount = 0;
        for (; new File(inputFilenameStart + inputFilesCount + ".jsonl").exists(); inputFilesCount++);
        if (inputFilesCount == 0)
            System.out.println(inputFilenameStart + "0.jsonl not found.");
        System.out.println("Discovered " + inputFilesCount + " file(s).");

        try
        {
            try (BufferedReader br = new BufferedReader(new FileReader(inputFilenameStart + "0.jsonl")))
            {
                String line = br.readLine();
                if (line == null)
                {
                    System.out.println("The file seems to be empty.");
                    return;
                }
                JSONObject row = new JSONObject(line);
                System.out.println("Keys:");
                for (String key : row.keySet())
                {
                    System.out.println(key);
                }
            }
        }
        catch (IOException e)
        {
            System.out.println("Couldn't read " + inputFilenameStart + "0.jsonl.");
            return;
        }

        System.out.println("Enter the method code key:");
        String methodCodeKey = reader.nextLine();

        System.out.println("Enter minimum changes for one augmentation round:");
        int minimumChangesForOneRound = Integer.parseInt(reader.nextLine());

        System.out.println("Enter maximum extra augmentation rounds (other than the first round):");
        int maxExtraRounds = Integer.parseInt(reader.nextLine());

        System.out.println("Enable swap operands? (Y/n):");
        boolean enableSwapOperands = !reader.nextLine().equalsIgnoreCase("n");
        System.out.println(enableSwapOperands ? "Enabled" : "Disabled");

        System.out.println("Enable rename variable? (Y/n):");
        boolean enableRenameVariable = !reader.nextLine().equalsIgnoreCase("n");
        System.out.println(enableRenameVariable ? "Enabled" : "Disabled");

        System.out.println("Enable swap statements? (Y/n):");
        boolean enableSwapStatements = !reader.nextLine().equalsIgnoreCase("n");
        System.out.println(enableSwapStatements ? "Enabled" : "Disabled");

        CodeAugmentationStatistics statistics = new CodeAugmentationStatistics();

        for (int i = 0; i < inputFilesCount; i++)
        {
            String inputFilename = inputFilenameStart + i + ".jsonl";
            String outputFilename = inputFilenameStart + (inputFilesCount + i) + ".jsonl";

            System.out.println();
            System.out.println("Input: " + inputFilename);
            System.out.println("Output: " + outputFilename);
            System.out.println();
            try
            {
                try (BufferedReader fileReader = new BufferedReader(new FileReader(inputFilename)))
                {
                    try (BufferedWriter fileWriter = new BufferedWriter(new FileWriter(outputFilename, false)))
                    {
                        String line;
                        boolean first = true;
                        while ((line = fileReader.readLine()) != null)
                        {
                            JSONObject row = new JSONObject(line);
                            GenerateAugmentedCodeResult result = CodeAugmentation.generateAugmentedCode(
                                    row.getString(methodCodeKey),
                                    minimumChangesForOneRound,
                                    maxExtraRounds,
                                    enableSwapOperands,
                                    enableRenameVariable,
                                    enableSwapStatements
                            );
                            statistics.record(result);
                            for (String code : result.generatedMethods)
                            {
                                // A time-consuming test
                                /*try
                                {
                                    MethodDeclaration methodDeclaration = StaticJavaParser.parseMethodDeclaration(code);
                                }
                                catch (Exception e)
                                {
                                    System.out.println("[ALERT] Failed parsing the generated code.");
                                }*/
                                row.put(methodCodeKey, code);
                                if (first)
                                    first = false;
                                else
                                    fileWriter.newLine();
                                fileWriter.append(row.toString());
                            }
                        }
                        System.out.println(statistics);
                    }
                }
            }
            catch (IOException e)
            {
                System.out.println("Couldn't read " + inputFilename + ".");
            }
        }
    }
}
