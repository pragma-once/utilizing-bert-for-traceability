import com.github.javaparser.JavaToken;
import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.body.MethodDeclaration;
import org.json.JSONObject;

import java.io.*;
import java.util.ArrayList;

public class Main
{
    public static void main(String[] args)
    {
        System.out.println("ATTENTION: Keep a backup of the original files somewhere else.");
        if (args.length < 2 || args.length > 4)
        {
            System.out.println("Params: input-directory output-directory");
            System.out.println("The input-directory is the directory containing .jsonl files with 'code' fields of java code.");
            System.out.println("Will write code tokens to 'code_tokens' field.");
            return;
        }
        String inputDir = args[0];
        String outputDir = args[1];
        addCodeTokens(inputDir, outputDir);
    }

    private static void addCodeTokens(String inputDir, String outputDir)
    {
        System.out.println("Input directory: " + inputDir);
        System.out.println("Output directory: " + outputDir);
        File[] inputFiles = new File(inputDir).listFiles();
        if (inputFiles == null)
        {
            System.out.println("Cannot list files in input-directory: " + inputDir);
            return;
        }
        for (File inputFile : inputFiles)
        {
            String inputPath = inputFile.getPath();
            if (!inputFile.isFile() || !inputPath.endsWith(".jsonl"))
                continue;
            String outputPath = new File(outputDir, inputFile.getName()).getPath();
            try
            {
                try (BufferedReader fileReader = new BufferedReader(new FileReader(inputPath)))
                {
                    try (BufferedWriter fileWriter = new BufferedWriter(new FileWriter(outputPath, false)))
                    {
                        System.out.println("Processing " + inputFile.getName() + "...");
                        String line;
                        boolean first = true;
                        while ((line = fileReader.readLine()) != null)
                        {
                            JSONObject row = new JSONObject(line);
                            String code = row.getString("code");
                            MethodDeclaration methodDeclaration = StaticJavaParser.parseMethodDeclaration(code);
                            ArrayList<String> codeTokens = new ArrayList<>();
                            for (JavaToken javaToken : methodDeclaration.getTokenRange().get())
                            {
                                String text = javaToken.getText();
                                if (!text.isBlank())
                                    codeTokens.add(text);
                            }
                            row.put("code_tokens", codeTokens);
                            if (first)
                                first = false;
                            else
                                fileWriter.newLine();
                            fileWriter.append(row.toString());
                        }
                    }
                }
            }
            catch (IOException e)
            {
                System.out.println("Couldn't read " + inputPath + " or write to " + outputPath + ".");
            }
        }
    }
}
