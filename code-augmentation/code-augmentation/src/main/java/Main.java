import com.github.javaparser.JavaToken;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.body.MethodDeclaration;
import org.json.JSONObject;

import java.io.*;
import java.nio.file.Paths;
import java.util.*;

public class Main
{
    public static void main(String[] args)
    {
        Scanner reader = new Scanner(System.in);
        System.out.println("ATTENTION: Keep a backup of the original files somewhere else just to make sure.");
        System.out.println("ATTENTION: Do the operation in a separate folder.");
        System.out.println("Enter the input directory that contains jsonl files:");
        String inputDirectory = reader.nextLine();
        {
            File file = new File(inputDirectory);
            if (!file.exists() || !file.isDirectory())
            {
                System.out.println("This directory doesn't exist.");
                return;
            }
        }
        System.out.println("Enter the output directory to create augmented jsonl files in:");
        String outputDirectory = reader.nextLine();
        String outputStatsDirectory = Paths.get(outputDirectory, "stats").toString();
        {
            File file = new File(outputDirectory);
            if (!file.exists())
            {
                System.out.println("This directory doesn't exist, making it...");
                if (!file.mkdirs())
                {
                    System.out.println("Couldn't make dir.");
                    return;
                }
            }
            else if (!file.isDirectory())
            {
                System.out.println("This is not a directory.");
                return;
            }
            file = new File(outputStatsDirectory);
            if (!file.exists())
            {
                System.out.println("Making stats directory inside the output directory...");
                if (!file.mkdirs())
                {
                    System.out.println("Couldn't make dir.");
                    return;
                }
            }
        }
        if (Paths.get(inputDirectory).equals(Paths.get(outputDirectory)))
        {
            System.out.println("[WARNING] The entered input and output directories are the same.");
        }

        ArrayList<String> inputFileNames = new ArrayList<>();
        for (String filename : new File(inputDirectory).list())
        {
            File file = new File(Paths.get(inputDirectory, filename).toString());
            if (file.exists() && file.isFile() && filename.endsWith(".jsonl"))
            {
                inputFileNames.add(filename);
            }
        }
        if (inputFileNames.size() == 0)
        {
            System.out.println(inputDirectory + " has no jsonl file.");
            return;
        }
        System.out.println("Discovered " + inputFileNames.size() + " file(s).");

        try
        {
            try (BufferedReader br = new BufferedReader(new FileReader(Paths.get(inputDirectory, inputFileNames.get(0)).toString())))
            {
                String line = br.readLine();
                if (line == null)
                {
                    System.out.println(inputFileNames.get(0) + " seems to be empty.");
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
            System.out.println("Couldn't read " + inputFileNames.get(0) + ".");
            return;
        }

        System.out.println("Enter the method code key:");
        String methodCodeKey = reader.nextLine();

        System.out.println("Enter the method code tokens key:");
        String methodCodeTokensKey = reader.nextLine();

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

        for (String inputFileName : inputFileNames)
        {
            String inputFilePath = Paths.get(inputDirectory, inputFileName).toString();
            String outputFilePath = Paths.get(outputDirectory, inputFileName).toString();

            System.out.println();
            System.out.println("Input: " + inputFilePath);
            System.out.println("Output: " + outputFilePath);
            System.out.println();
            try
            {
                try (BufferedReader fileReader = new BufferedReader(new FileReader(inputFilePath)))
                {
                    try
                    {
                        try (BufferedWriter fileWriter = new BufferedWriter(new FileWriter(outputFilePath, false)))
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
                                    if (!methodCodeTokensKey.isBlank())
                                    {
                                        MethodDeclaration methodDeclaration = StaticJavaParser.parseMethodDeclaration(code);
                                        ArrayList<String> codeTokens = new ArrayList<>();
                                        for (JavaToken javaToken : methodDeclaration.getTokenRange().get())
                                        {
                                            String text = javaToken.getText();
                                            if (!text.isBlank())
                                                codeTokens.add(text);
                                        }
                                        row.put(methodCodeTokensKey, codeTokens);
                                    }
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
                    catch (IOException e)
                    {
                        System.out.println("Couldn't open " + outputFilePath + ".");
                    }
                }
            }
            catch (IOException e)
            {
                System.out.println("Couldn't read " + inputFilePath + ".");
            }
        }

        String filePath = Paths.get(outputStatsDirectory, "stats-summary.txt").toString();
        try (BufferedWriter fileWriter = new BufferedWriter(new FileWriter(filePath, false)))
        {
            fileWriter.append("Config:");
            fileWriter.newLine();
            fileWriter.append("    Minimum changes for one augmentation round: ");
            fileWriter.append(Integer.toString(minimumChangesForOneRound));
            fileWriter.newLine();
            fileWriter.append("    Maximum extra augmentation rounds (other than first round): ");
            fileWriter.append(Integer.toString(maxExtraRounds));
            fileWriter.newLine();
            fileWriter.append("    Swap operands: ");
            fileWriter.append(enableSwapOperands ? "Enabled" : "Disabled");
            fileWriter.newLine();
            fileWriter.append("    Renamed variable: ");
            fileWriter.append(enableRenameVariable ? "Enabled" : "Disabled");
            fileWriter.newLine();
            fileWriter.append("    Swap statements: ");
            fileWriter.append(enableSwapStatements ? "Enabled" : "Disabled");
            fileWriter.newLine();
            fileWriter.newLine();
            fileWriter.append("Stats:");
            fileWriter.newLine();
            fileWriter.newLine();
            fileWriter.append(statistics.toString());
            fileWriter.newLine();
        }
        catch (IOException e)
        {
            System.out.println("Couldn't open " + filePath + ".");
        }

        filePath = Paths.get(outputStatsDirectory, "stats.csv").toString();
        try (BufferedWriter fileWriter = new BufferedWriter(new FileWriter(filePath, false)))
        {
            fileWriter.append(statistics.toCSV());
        }
        catch (IOException e)
        {
            System.out.println("Couldn't open " + filePath + ".");
        }
    }
}
