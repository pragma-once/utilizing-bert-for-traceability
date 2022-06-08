import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.MethodDeclaration;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.*;
import java.util.ArrayList;
import java.util.HashMap;

public class Main
{
    public static void main(String[] args)
    {
        System.out.println("ATTENTION: Keep a backup of the original files somewhere else.");
        if (args.length < 2 || args.length > 4)
        {
            System.out.println("Params: input-directory output-directory [minimum-method-commit-lines [minimum-method-commit-lines-percentage]]");
            System.out.println("The input-directory is the directory containing .jsonl files created by extract-data.py with CODE_CONTENT=METHODS_AS_CODE");
            return;
        }
        String inputDir = args[0];
        String outputDir = args[1];
        int minMethodCommitLines = 1;
        double minMethodCommitLinesFraction = 0;
        if (args.length >= 3)
        {
            try
            {
                minMethodCommitLines = Integer.parseInt(args[2]);
            }
            catch (NumberFormatException e)
            {
                System.out.println(args[2] + " isn't a integer.");
                return;
            }
        }
        if (args.length >= 4)
        {
            try
            {
                minMethodCommitLinesFraction = Double.parseDouble(args[3]) / 100;
            }
            catch (NumberFormatException e)
            {
                System.out.println(args[3] + " isn't a number.");
                return;
            }
        }
        if (minMethodCommitLinesFraction > 1)
            minMethodCommitLinesFraction = 1;
        extractData(inputDir, outputDir, minMethodCommitLines, minMethodCommitLinesFraction);
    }

    private static void putInRow(
            JSONObject row,
            String code,
            int method_non_empty_lines_count,
            int method_removed_non_empty_lines_in_commit_count,
            int method_added_non_empty_lines_in_commit_count
        )
    {
        row.put("code", code);
        row.put("method_nonempty_lines", method_non_empty_lines_count);
        row.put("removed_nonempty_lines", method_removed_non_empty_lines_in_commit_count);
        row.put("added_nonempty_lines", method_added_non_empty_lines_in_commit_count);
    }

    private static String[] splitLines(String text)
    {
        //return text.split("\\r?\\n|\\r");
        return text.split("\\R"); // Since Java 8
    }

    private static int countNonEmptyLines(String[] lines, int inclusiveZeroBasedStart, int exclusiveZeroBasedStop)
    {
        int result = 0;
        for (int i = inclusiveZeroBasedStart; i < exclusiveZeroBasedStop; i++)
        {
            if (!lines[i].isBlank())
            {
                result++;
            }
        }
        return result;
    }

    private static void transformLinesToNewFile(
            JSONArray removed_lines,
            JSONArray added_lines,
            ArrayList<Float> allLinesInNewFile,
            HashMap<Float, Integer> allLinesToRemovedNonEmptyLinesCount,
            HashMap<Float, Integer> allLinesToAddedNonEmptyLinesCount
    )
    {
        int line_i = 0;
        float last_line = -1;
        int removed_lines_offset = 0;
        for (int j = 0; j < removed_lines.length(); j++)
        {
            int removed_line_index = removed_lines.getJSONObject(j).getInt("index");
            int removed_line_nonempty = removed_lines.getJSONObject(j).getString("text").isBlank() ? 0 : 1;
            while (line_i < added_lines.length())
            {
                int added_line_index = added_lines.getJSONObject(line_i).getInt("index");
                int added_line_nonempty = added_lines.getJSONObject(line_i).getString("text").isBlank() ? 0 : 1;
                if (added_line_index >= removed_line_index + removed_lines_offset)
                    break;

                allLinesInNewFile.add((float)added_line_index);
                allLinesToAddedNonEmptyLinesCount.put((float)added_line_index, added_line_nonempty);

                removed_lines_offset++;
                line_i++;
            }
            float new_removed_line_index = (float)(removed_line_index + removed_lines_offset) - 0.5f;
            if (new_removed_line_index != last_line)
            {
                allLinesInNewFile.add(new_removed_line_index);
                allLinesToRemovedNonEmptyLinesCount.put(new_removed_line_index, removed_line_nonempty);
                last_line = new_removed_line_index;
            }
            else if (removed_line_nonempty == 1)
            {
                allLinesToRemovedNonEmptyLinesCount.put(
                        new_removed_line_index,
                        allLinesToRemovedNonEmptyLinesCount.get(new_removed_line_index) + 1
                );
            }
            removed_lines_offset--;
        }
        while (line_i < added_lines.length())
        {
            int added_line_index = added_lines.getJSONObject(line_i).getInt("index");
            int added_line_nonempty = added_lines.getJSONObject(line_i).getString("text").isBlank() ? 0 : 1;

            allLinesInNewFile.add((float)added_line_index);
            allLinesToAddedNonEmptyLinesCount.put((float)added_line_index, added_line_nonempty);

            removed_lines_offset++;
            line_i++;
        }
    }

    private static void extractData(String inputDir, String outputDir, int minMethodCommitLines, double minMethodCommitLinesFraction)
    {
        System.out.println("Input directory: " + inputDir);
        System.out.println("Output directory: " + outputDir);
        System.out.println("Minimum method commit lines: " + minMethodCommitLines);
        System.out.println("Minimum method commit lines percentage: " + (minMethodCommitLinesFraction * 100) + "%");
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
                            JSONObject code = row.getJSONObject("code");
                            JSONArray added_files = code.getJSONArray("added_files");
                            JSONArray modified_files = code.getJSONArray("modified_files");
                            // Added files
                            for (int i = 0; i < added_files.length(); i++)
                            {
                                JSONObject added_file = added_files.getJSONObject(i);
                                String newFileText = added_file.getString("text");

                                CompilationUnit compilationUnit;
                                try
                                {
                                    compilationUnit = StaticJavaParser.parse(newFileText);
                                }
                                catch (Exception e)
                                {
                                    System.out.println("[INFO] A compilation failed, skipping this one.");
                                    continue;
                                }

                                String[] newFileTextLines = splitLines(newFileText);

                                for (MethodDeclaration methodDeclaration : Utils.getMethodDeclarations(compilationUnit))
                                {
                                    int methodNonEmptyLines = countNonEmptyLines(
                                            newFileTextLines,
                                            methodDeclaration.getBegin().get().line - 1,
                                            methodDeclaration.getEnd().get().line
                                    );
                                    if (methodNonEmptyLines < minMethodCommitLines)
                                        continue;
                                    // Add the method
                                    putInRow(
                                            row,
                                            methodDeclaration.toString(),
                                            methodNonEmptyLines,
                                            0,
                                            methodNonEmptyLines
                                    );
                                    if (first)
                                        first = false;
                                    else
                                        fileWriter.newLine();
                                    fileWriter.append(row.toString());
                                }
                            }
                            // Modified files
                            for (int i = 0; i < modified_files.length(); i++)
                            {
                                JSONObject modified_file = modified_files.getJSONObject(i);
                                String newFileText = modified_file.getString("new_text");

                                CompilationUnit newFileCompilationUnit;
                                try
                                {
                                    newFileCompilationUnit = StaticJavaParser.parse(newFileText);
                                }
                                catch (Exception e)
                                {
                                    System.out.println("[INFO] A compilation failed, skipping this one.");
                                    continue;
                                }

                                JSONArray removed_lines = modified_file.getJSONArray("removed_lines");
                                JSONArray added_lines = modified_file.getJSONArray("added_lines");

                                String[] newFileTextLines = splitLines(newFileText);

                                // Translate all lines to the new file
                                //
                                // Removed line positions will be subtracted by 0.5.
                                // They're between the lines, so this way a removed method won't result in
                                // another method being linked to the issue, and helps overall.
                                ArrayList<Float> allLinesInNewFile = new ArrayList<>();
                                HashMap<Float, Integer> allLinesToRemovedNonEmptyLinesCount = new HashMap<>();
                                HashMap<Float, Integer> allLinesToAddedNonEmptyLinesCount = new HashMap<>();
                                transformLinesToNewFile(
                                        removed_lines,
                                        added_lines,
                                        allLinesInNewFile,
                                        allLinesToRemovedNonEmptyLinesCount,
                                        allLinesToAddedNonEmptyLinesCount
                                );

                                // TEST
                                /*System.out.print("[TEST] allLinesInNewFile: ");
                                for (float item : allLinesInNewFile)
                                {
                                    System.out.print(item);
                                }
                                System.out.println();*/

                                // Add methods that are modified
                                int line_i = 0;
                                for (MethodDeclaration methodDeclaration : Utils.getMethodDeclarations(newFileCompilationUnit))
                                {
                                    int methodBegin = methodDeclaration.getBegin().get().line;
                                    int methodEnd = methodDeclaration.getEnd().get().line;
                                    for (; line_i < allLinesInNewFile.size(); line_i++)
                                    {
                                        float line_number = allLinesInNewFile.get(line_i) + 1;
                                        if (line_number > (float) methodEnd)
                                        {
                                            break;
                                        }
                                        else if ((float) methodBegin <= line_number) // && line_number <= oldCompilationUnit.getEnd().get().line
                                        {
                                            int methodNonEmptyLines = countNonEmptyLines(
                                                    newFileTextLines,
                                                    methodBegin - 1,
                                                    methodEnd
                                            );
                                            int removedNonEmptyLinesInCommit = 0;
                                            int addedNonemptyLinesInCommit = 0;
                                            for (
                                                    int line_j = line_i;
                                                    line_j < allLinesInNewFile.size() && (allLinesInNewFile.get(line_j) + 1) <= (float) methodEnd;
                                                    line_j++
                                            )
                                            {
                                                float line_index = allLinesInNewFile.get(line_j);
                                                if (line_index == (float)(int)line_index)
                                                    addedNonemptyLinesInCommit += allLinesToAddedNonEmptyLinesCount.get(line_index);
                                                else
                                                    removedNonEmptyLinesInCommit += allLinesToRemovedNonEmptyLinesCount.get(line_index);
                                            }
                                            int allNonEmptyLineChangesInCommit = removedNonEmptyLinesInCommit + addedNonemptyLinesInCommit;
                                            if (allNonEmptyLineChangesInCommit < minMethodCommitLines)
                                                continue;
                                            if (((double)allNonEmptyLineChangesInCommit / (double)methodNonEmptyLines) < minMethodCommitLinesFraction)
                                                continue;
                                            // Add the method
                                            putInRow(
                                                    row,
                                                    methodDeclaration.toString(),
                                                    methodNonEmptyLines,
                                                    removedNonEmptyLinesInCommit,
                                                    addedNonemptyLinesInCommit
                                            );
                                            if (first)
                                                first = false;
                                            else
                                                fileWriter.newLine();
                                            fileWriter.append(row.toString());
                                            // Not twice
                                            break;
                                        }
                                        // else (line_number < begin) continue...
                                    }
                                }
                            }
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

    private static void testMethodBeginEnd()
    {
        String test_source = "class A\n" +
                "{\n" +
                "    void a()\n" +
                "    {\n" +
                "        hello();\n" +
                "    }\n" +
                "    \n" +
                "    void b()\n" +
                "    {\n\n" +
                "        // some code\n" +
                "        // some more code\n\n" +
                "    }\n" +
                "}";
        System.out.println("Source:");
        String[] test_source_lines = splitLines(test_source);
        for (int i = 0; i < test_source_lines.length; i++)
        {
            System.out.print(i + 1);
            System.out.print(": ");
            System.out.println(test_source_lines[i]);
        }
        System.out.println(test_source);
        CompilationUnit compilationUnit = StaticJavaParser.parse(test_source);
        ArrayList<MethodDeclaration> methods = Utils.getMethodDeclarations(compilationUnit);
        for (MethodDeclaration method : methods)
        {
            System.out.println();
            System.out.println("Method:");
            System.out.println(method);
            System.out.print("Begin: ");
            System.out.println(method.getBegin().get().line);
            System.out.print("End: ");
            System.out.println(method.getEnd().get().line);
        }
    }

    private static void testLinesAlgorithm()
    {
        int[] removed_lines_array = { 1, 2, 3, 4, 7, 8};
        int[] added_lines_array = { 2, 3, 5, 10, 11};
        String[] removed_lines_text_array = { "-1", "-2", " ", "-4", "-7", "-8"};
        String[] added_lines_text_array = { "+2", "+3", "", "+10", "  "};

        // 0 1 2 3 4 5 6 7 8 9 ... => remove =>
        // 0 5 6 9 ... => add =>
        // 0 5 a a 6 9 ... =>
        // translated removed lines: 0.5, 4.5
        // => 0.5, 2, 3, 4.5, 5, 10, 11

        // Data conversion to prepare for testing
        JSONObject[] removed_lines_objects = new JSONObject[removed_lines_array.length];
        for (int i = 0; i < removed_lines_array.length; i++)
        {
            removed_lines_objects[i] = new JSONObject();
            removed_lines_objects[i].put("index", removed_lines_array[i]);
            removed_lines_objects[i].put("text", removed_lines_text_array[i]);
        }
        JSONObject[] added_lines_objects = new JSONObject[added_lines_array.length];
        for (int i = 0; i < added_lines_array.length; i++)
        {
            added_lines_objects[i] = new JSONObject();
            added_lines_objects[i].put("index", added_lines_array[i]);
            added_lines_objects[i].put("text", added_lines_text_array[i]);
        }
        JSONArray removed_lines = new JSONArray(removed_lines_objects);
        JSONArray added_lines = new JSONArray(added_lines_objects);

        ArrayList<Float> allLinesInNewFile = new ArrayList<>();
        HashMap<Float, Integer> allLinesToRemovedNonEmptyLinesCount = new HashMap<>();
        HashMap<Float, Integer> allLinesToAddedNonEmptyLinesCount = new HashMap<>();
        transformLinesToNewFile(
                removed_lines,
                added_lines,
                allLinesInNewFile,
                allLinesToRemovedNonEmptyLinesCount,
                allLinesToAddedNonEmptyLinesCount
        );

        // Print the result
        System.out.println("Removed lines:");
        for (int i = 0; i < removed_lines_array.length; i++)
        {
            System.out.print(removed_lines_array[i]);
            System.out.print(": ");
            System.out.println(removed_lines_text_array[i]);
        }
        System.out.println("Added lines:");
        for (int i = 0; i < added_lines_array.length; i++)
        {
            System.out.print(added_lines_array[i]);
            System.out.print(": ");
            System.out.println(added_lines_text_array[i]);
        }
        System.out.println("Result:");
        for (float line : allLinesInNewFile)
        {
            System.out.print(line);
            System.out.print(": ");
            if (line == (float)(int)line)
                System.out.print(allLinesToAddedNonEmptyLinesCount.get(line));
            else
                System.out.print(allLinesToRemovedNonEmptyLinesCount.get(line));
            System.out.println(" lines of non-empty change");
        }
    }
}
