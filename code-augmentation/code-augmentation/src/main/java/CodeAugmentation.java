import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.NodeList;
import com.github.javaparser.ast.body.*;
import com.github.javaparser.ast.expr.*;
import com.github.javaparser.ast.stmt.*;
import com.github.javaparser.ast.type.ClassOrInterfaceType;
import com.github.javaparser.ast.type.ReferenceType;
import com.github.javaparser.ast.type.TypeParameter;

import java.util.*;

public class CodeAugmentation
{
    public static GenerateAugmentedCodeResult GenerateAugmentedCode(
            String method,
            int minimumChangesForOneRound,
            int maxExtraRounds,
            boolean enableSwapOperands,
            boolean enableRenameVariable,
            boolean enableSwapStatements
        )
    {
        GenerateAugmentedCodeResult result = new GenerateAugmentedCodeResult();
        MethodDeclaration methodDeclaration = StaticJavaParser.parseMethodDeclaration(method);

        // First attempt

        int swapOperandsChanges = 0, renameVariableChanges = 0, swapStatementsChanges = 0;
        if (enableSwapOperands)
            swapOperandsChanges = swapRandomOperandPairs(methodDeclaration, 0.75);
        if (enableRenameVariable)
            renameVariableChanges = renameRandomVariables(methodDeclaration, 0.75);
        if (enableSwapStatements)
            swapStatementsChanges = swapRandomStatementsInBlocks(methodDeclaration, 2);
        int changes = swapOperandsChanges + renameVariableChanges + swapStatementsChanges;

        if (changes >= minimumChangesForOneRound)
            result.generatedMethods.add(methodDeclaration.toString());

        result.firstAttemptSwapOperandsChanges = swapOperandsChanges;
        result.firstAttemptRenameVariableChanges = renameVariableChanges;
        result.firstAttemptSwapStatementsChanges = swapStatementsChanges;

        // More rounds based on the first attempt's results

        int moreRounds = Math.min(maxExtraRounds, changes / minimumChangesForOneRound - 1);
        Random random = new Random();
        for (int i = 0; i < moreRounds; i++)
        {
            methodDeclaration = StaticJavaParser.parseMethodDeclaration(method);
            if (enableSwapOperands)
                swapRandomOperandPairs(methodDeclaration, 0.5 + random.nextDouble() * 0.5);
            if (enableRenameVariable)
                renameRandomVariables(methodDeclaration, 0.5 + random.nextDouble() * 0.5);
            if (enableSwapStatements)
                swapRandomStatementsInBlocks(methodDeclaration, 1 + random.nextDouble() * 9);
            result.generatedMethods.add(methodDeclaration.toString());
        }
        return result;
    }

    /// @return The number of swaps
    public static int swapRandomOperandPairs(MethodDeclaration method, double swap_probability)
    {
        LinkedList<BinaryExpr> to_swap = new LinkedList<>();
        Random random = new Random();
        class Visitor extends NodeVisitorWithScopeTracking {
            private boolean isTypeSupported(String typename)
            {
                return typename.equals("boolean")
                        || typename.equals("char")
                        || typename.equals("int")
                        || typename.equals("long")
                        || typename.equals("float")
                        || typename.equals("double");
            }
            private int checkBinaryExpressionOneSide(Expression n)
            {
                if (n.isBinaryExpr())
                    return checkBinaryExpression(n.asBinaryExpr());
                if (n.isEnclosedExpr())
                    return checkBinaryExpressionOneSide(n.asEnclosedExpr().getInner());
                if (
                        n.isBooleanLiteralExpr()
                                || n.isCharLiteralExpr()
                                || n.isIntegerLiteralExpr()
                                || n.isLongLiteralExpr()
                                || n.isDoubleLiteralExpr()
                )
                    return 0;
                if (n.isNameExpr()) // A name without dots in an expression
                {
                    String var_type = getVariableType(n.asNameExpr().getName().asString());
                    if (var_type == null)
                        return 1;
                    if (isTypeSupported(var_type))
                        return 0;
                }
                if (n.isCastExpr())
                {
                    String cast_type = n.asCastExpr().getType().asString();
                    if (cast_type == null)
                        return 1;
                    if (isTypeSupported(cast_type))
                        return 0;
                }
                return 1;
            }
            private int checkBinaryExpression(BinaryExpr n)
            {
                int number_of_unsupported_operands = checkBinaryExpressionOneSide(n.getLeft());
                number_of_unsupported_operands += checkBinaryExpressionOneSide(n.getRight());
                return number_of_unsupported_operands;
            }
            private boolean isOperatorSupportedWithUnknownOperands(BinaryExpr.Operator operator)
            {
                String op = operator.asString();
                return op.equals("&&")
                        || op.equals("||")
                        || op.equals("==")
                        || op.equals("!=")
                        || op.equals("<")
                        || op.equals(">")
                        || op.equals("<=")
                        || op.equals(">=")
                        ;
            }
            private boolean isOperatorSupportedWithSupportedOperands(BinaryExpr.Operator operator)
            {
                String op = operator.asString();
                return op.equals("+")
                        || op.equals("*")
                        ;
            }
            public BinaryExpr.Operator mapOperator(BinaryExpr.Operator operator)
            {
                String op = operator.asString();
                if (op.equals("<"))
                    return BinaryExpr.Operator.GREATER;
                if (op.equals(">"))
                    return BinaryExpr.Operator.LESS;
                if (op.equals("<="))
                    return BinaryExpr.Operator.GREATER_EQUALS;
                if (op.equals(">="))
                    return BinaryExpr.Operator.LESS_EQUALS;
                return operator;
            }
            @Override
            public void enter(Node n)
            {
                super.enter(n);
                if (n.getClass() == BinaryExpr.class)
                {
                    BinaryExpr be = (BinaryExpr) n;
                    if (isOperatorSupportedWithUnknownOperands(be.getOperator()))
                    {
                        if (random.nextDouble() < swap_probability)
                            to_swap.add(be);
                    }
                    else if (isOperatorSupportedWithSupportedOperands(be.getOperator()) && checkBinaryExpression(be) == 0)
                    {
                        if (random.nextDouble() < swap_probability)
                            to_swap.add(be);
                    }
                }
            }
        }
        Visitor visitor = new Visitor();
        visitor.visit(method);
        for (BinaryExpr expr : to_swap)
        {
            Expression left = expr.getLeft();
            expr.setLeft(expr.getRight());
            expr.setRight(left);
            expr.setOperator(visitor.mapOperator(expr.getOperator()));
        }
        return to_swap.size();
    }
    public static void swapRandomOperandPairsTest(int repeats, double swap_probability)
    {
        String test_method = "void a()\n{\n\tint b; double a, c; char d, f; boolean e;\n"
                + "\tsomething = a.member + b; // no swap with unknown names\n"
                + "\tsomething = a + b.member; // no swap with unknown names\n"
                + "\tsomething = a.f() + b; // no swap with unknown names\n"
                + "\tsomething = a + b * c / d + 1.0f == 0.0 && e || (boolean)f;\n"
                + "\tsomething = a < b && c <= d || f > e && (f >= e || a != e);\n"
                + "\tfor (int i = 0; i < a; i++) { a = i + 1 + unknown; }\n"
                + "\tfor (unknown_i = 0; unknown_i < a; i++) { a = unknown_i + 1; a = unknown_obj == null; }\n"
                + "\tif (a < b == c < d && unknown_obj != null)\n"
                + "\t\tuntouched_unknowns = u1 + u2 * u3 + u4;\n}";
        System.out.println("Test method:");
        System.out.println(test_method);
        System.out.println(repeats + " results:");
        for (int i = 0; i < repeats; i++)
        {
            MethodDeclaration m = StaticJavaParser.parseMethodDeclaration(test_method);
            int count = CodeAugmentation.swapRandomOperandPairs(m, swap_probability);
            System.out.println(m.toString());
            System.out.println("Number of changes: " + count);
        }
    }

    private static boolean isUpperCaseLetter(char ch)
    {
        return 'A' <= ch && ch <= 'Z';
    }

    private static boolean isLowerCaseLetter(char ch)
    {
        return 'a' <= ch && ch <= 'z';
    }

    private static boolean isNumber(char ch)
    {
        return '0' <= ch && ch <= '9';
    }

    private static char toUpper(char ch)
    {
        if (isLowerCaseLetter(ch))
            return (char)('A' + (ch - 'a'));
        return ch;
    }

    private static char toLower(char ch)
    {
        if (isUpperCaseLetter(ch))
            return (char)('a' + (ch - 'A'));
        return ch;
    }

    private static LinkedList<String> parseWordsInName(String name)
    {
        LinkedList<String> words = new LinkedList<>();
        StringBuilder current_word = new StringBuilder();
        for (int i = 0; i < name.length(); i++)
        {
            char ch = name.charAt(i);
            if (ch == '_'
                    || (isUpperCaseLetter(ch) && (
                            i == 0 || !isUpperCaseLetter(name.charAt(i - 1))
                                    || ( i+1 < name.length() && !isUpperCaseLetter(name.charAt(i + 1)) )
                        ))
                    || (isNumber(ch) && (i == 0 || !isNumber(name.charAt(i - 1))))
                )
            {
                if (current_word.length() != 0)
                {
                    words.add(current_word.toString());
                    current_word.delete(0, current_word.length());
                }
            }
            if (isLowerCaseLetter(ch) || isUpperCaseLetter(ch) || isNumber(ch))
                current_word.append(ch);
        }
        if (current_word.length() != 0)
            words.add(current_word.toString());
        return words;
    }

    private static String toCamelCase(LinkedList<String> words, boolean join_one_letter_words, boolean pascal_case)
    {
        StringBuilder result = new StringBuilder();
        boolean separate = pascal_case;
        int c = 0;
        for (String word : words)
        {
            StringBuilder new_word = new StringBuilder(word.toLowerCase());
            if (separate || (c != 0 && word.length() > 1)) // Not that beautiful because Iterator is limited.
                new_word.setCharAt(0, toUpper(new_word.charAt(0)));
            result.append(new_word);
            separate = !join_one_letter_words || word.length() > 1; // Cannot check out next item because Iterator is limited.
            c++;
        }
        return result.toString();
    }

    private static String toSnakeCase(LinkedList<String> words, boolean join_one_letter_words, boolean screaming_snake_case)
    {
        StringBuilder result = new StringBuilder();
        boolean separate = false;
        int c = 0;
        for (String word : words)
        {
            if (separate || (c != 0 && word.length() > 1)) // Not that beautiful because Iterator is limited.
                result.append('_');
            result.append(screaming_snake_case ? word.toUpperCase() : word.toLowerCase());
            separate = !join_one_letter_words || word.length() > 1; // Cannot check out next item because Iterator is limited.
            c++;
        }
        return result.toString();
    }

    private static boolean isCountVariable(LinkedList<String> words)
    {
        String first = words.getFirst().toLowerCase();
        String last = words.getLast().toLowerCase();
        return last.equals("count")
                || last.equals("counter")
                || first.equals("number")
                || first.equals("num") ||
                first.equals("n");
    }

    private static void convertToAlternativeCountVariableName(LinkedList<String> words, Random random)
    {
        // Remove count word(s)
        if (words.size() == 0)
            return;
        int count_type;
        String first = words.getFirst().toLowerCase();
        String last = words.getLast().toLowerCase();
        if (last.equals("count"))
        {
            count_type = 0;
            words.removeLast();
        }
        else if (last.equals("counter"))
        {
            count_type = 1;
            words.removeLast();
        }
        else if (first.equals("number"))
        {
            count_type = 2;
            words.removeFirst();
            if (words.size() != 0 && words.getFirst().equalsIgnoreCase("of"))
            {
                count_type = 3;
                words.removeFirst();
            }
        }
        else if (first.equals("num"))
        {
            count_type = 4;
            words.removeFirst();
        }
        else if (first.equals("n"))
        {
            count_type = 5;
            words.removeFirst();
        }
        else return;
        // Add new count word(s)
        int selector = random.nextInt(6);
        if (selector >= count_type)
            selector++;
        switch (selector)
        {
            case 0:
                words.add("count");
                break;
            case 1:
                words.add("counter");
                break;
            case 2:
                words.addFirst("number");
                break;
            case 3:
                words.addFirst("of");
                words.addFirst("number");
                break;
            case 4:
                words.addFirst("num");
                break;
            case 5:
                words.addFirst("n");
                break;
            case 6:
                words.addLast("number");
                break;
        }
    }

    public static String getAlternativeName(String name, Random random)
    {
        double selector = random.nextDouble();
        if (selector < 0.1)
        {
            if (random.nextDouble() < 0.8)
            {
                return "" + (char)('a' + random.nextInt('z' - 'a' + 1));
            }
            else
            {
                return "" + (char)('A' + random.nextInt('Z' - 'A' + 1));
            }
        }

        LinkedList<String> words = parseWordsInName(name);
        if (words.size() == 0)
            return name;

        if (selector < 0.3)
        {
            StringBuilder new_name = new StringBuilder();
            if (random.nextDouble() < 0.75)
            {
                for (String word : words)
                {
                    if (isNumber(word.charAt(0)))
                        new_name.append(word);
                    else
                        new_name.append(toLower(word.charAt(0)));
                }
            }
            else
            {
                for (String word : words)
                {
                    if (isNumber(word.charAt(0)))
                        new_name.append(word);
                    else
                        new_name.append(toUpper(word.charAt(0)));
                }
            }
            if (isNumber(new_name.charAt(0)))
                return "_" + new_name;
            return new_name.toString();
        }

        if (isCountVariable(words) && random.nextDouble() < 0.5)
        {
            convertToAlternativeCountVariableName(words, random);
        }

        if (words.size() > 1 && random.nextDouble() < 0.3)
        {
            while (random.nextDouble() < 0.75)
            {
                int i = random.nextInt(words.size());
                int j = random.nextInt(words.size() - 1);
                if (j >= i)
                    j++;
                String word_i = words.get(i);
                words.set(i, words.get(j));
                words.set(j, word_i);
            }
        }

        LinkedList<String> new_words;

        if (random.nextDouble() < 0.4)
        {
            new_words = new LinkedList<>();
            for (String word : words)
            {
                if (random.nextBoolean() && !isNumber(word.charAt(0)))
                {
                    new_words.add("" + word.charAt(0));
                }
                else
                {
                    new_words.add(word);
                }
            }
        }
        else
            new_words = words;

        boolean join_one_letter_words = random.nextDouble() < 0.75;

        double naming_convention_selector = random.nextDouble();
        String result;
        if (naming_convention_selector < 0.5)
            result = toCamelCase(new_words, join_one_letter_words, false);
        else if (naming_convention_selector < 0.75)
            result = toSnakeCase(new_words, join_one_letter_words, false);
        else if (naming_convention_selector < 0.9)
            result = toSnakeCase(new_words, join_one_letter_words, true);
        else
            result = toCamelCase(new_words, join_one_letter_words, true);

        if (isNumber(result.charAt(0)))
            return "_" + result;
        return result;
    }
    /// @return The number of renames
    public static int renameRandomVariables(MethodDeclaration method, double rename_probability)
    {
        HashMap<VariableDeclarator, LinkedList<NameExpr>> namesMap = new HashMap<>();
        HashMap<String, Boolean> usedNames = new HashMap<>();
        Random random = new Random();
        class Visitor extends NodeVisitorWithScopeTracking
        {
            @Override
            public void enter(Node n)
            {
                super.enter(n);
                if (n.getClass() == NameExpr.class) // A simple name or the first name in a name with dots in an expression
                {
                    usedNames.put(((NameExpr) n).getName().asString(), true);
                    VariableDeclarator declarator = getVariableDeclarator(((NameExpr) n).getName().asString());
                    if (declarator != null)
                    {
                        if (!namesMap.containsKey(declarator))
                            namesMap.put(declarator, new LinkedList<>());
                        namesMap.get(declarator).add((NameExpr) n);
                    }
                }
            }
        }
        Visitor visitor = new Visitor();
        visitor.visit(method);
        int change_counter = 0;
        for (Map.Entry<VariableDeclarator, LinkedList<NameExpr>> item : namesMap.entrySet())
        {
            if (random.nextDouble() >= rename_probability)
                continue;
            for (int i = 0; i < 10; i++)
            {
                String new_name = getAlternativeName(item.getKey().getName().asString(), random);
                if (usedNames.containsKey(new_name))
                    continue;
                usedNames.put(new_name, true);
                item.getKey().setName(new_name);
                for (NameExpr nameExpr : item.getValue())
                {
                    nameExpr.setName(new_name);
                }
                change_counter++;
                break;
            }
        }
        return change_counter;
    }
    public static void renameRandomVariablesTest(int repeats, double rename_probability)
    {
        String test_method = "void a()\n{\n\ttype1 beanCount, someLongNAMEHere; type2 ant_value, cat; type3 DUNE, f; type4 e;\n"
                + "\ttype5 some, other, more, names, method;\n"
                + "\tsomething.some.other.names = ant_value.some.more.names + beanCount.some.method() * cat / DUNE + 1.0f == 0.0 && e || (boolean)f; \n"
                + "\tthis.beanCount = this.ant_value;\n"
                + "\tbeanCount = ant_value;\n"
                + "\tbeanCount.member = ant_value.member;\n"
                + "\tant_value(); // Call on local variable in Java is not possible.\n"
                + "\tant_value.someMethod();\n"
                + "\tant_value.beanCount();\n"
                + "\tsomething = ant_value.beanCount();\n"
                + "\tsomeLongNAMEHere = ant_value < beanCount && cat <= DUNE || f > e && (f >= e || a != e);\n"
                + "\tfor (int i = 0; i < ant_value; i++) { ant_value = i + 1 + unknown; }\n"
                + "\tfor (unknown_i = 0; unknown_i < ant_value; i++) { ant_value = unknown_i + 1; }\n"
                + "\tif (ant_value < beanCount == cat < DUNE)\n"
                + "\t\tuntouched_unknowns = u1 + u2 * u3 + u4;\n}";
        System.out.println("Test method:");
        System.out.println(test_method);
        System.out.println(repeats + " results:");
        for (int i = 0; i < repeats; i++)
        {
            MethodDeclaration m = StaticJavaParser.parseMethodDeclaration(test_method);
            int count = CodeAugmentation.renameRandomVariables(m, rename_probability);
            System.out.println(m.toString());
            System.out.println("Number of changes: " + count);
        }
    }

    /// @return The number of swaps
    public static int swapRandomStatementsInBlocks(
            MethodDeclaration method,
            double swap_attempts_per_statement_count
    )
    {
        if (swap_attempts_per_statement_count < 0)
        {
            return 0;
        }

        class StmtInfo
        {
            public StmtInfo(BlockStmt block, int blockFraction, int indexInBlock)
            {
                this.block = block;
                this.blockFraction = blockFraction;
                this.indexInBlock = indexInBlock;
            }
            public BlockStmt block;
            public int blockFraction;
            public int indexInBlock;
            // SHOULD NOT store the VariableDeclarator
            // Names are names, an example of how storing VariableDeclarator could go wrong:
            //   a = 0;
            //   int a = 1;
            //   b = a;
            // b is dependent on 'int a = 1', so with that logic 'a = 0' and int 'a = 1' could be swapped:
            //   int a = 1;
            //   a = 0;
            //   b = a;
            // which changes the meaning of 'a = 0' while the name is the same.
            // Swapping changes name meanings, so it's best to know them by the names.
            public HashMap<String, Boolean> namesSetMap = new HashMap<>();
            public HashMap<String, Boolean> namesGetMap = new HashMap<>();
            public ArrayList<String> namesSet = new ArrayList<>();
            public ArrayList<String> namesGet = new ArrayList<>();

            public boolean garbage = false;

            public void addNameSet(String name)
            {
                if (!namesSetMap.containsKey(name))
                {
                    namesSetMap.put(name, true);
                    namesSet.add(name);
                }
            }
            public void addNameGet(String name)
            {
                if (!namesGetMap.containsKey(name))
                {
                    namesGetMap.put(name, true);
                    namesGet.add(name);
                }
            }
        }
        class BlockFractionInfo
        {
            public BlockFractionInfo(BlockStmt block, int blockFraction)
            {
                this.block = block;
                this.blockFraction = blockFraction;
            }
            public BlockStmt block;
            public int blockFraction;
            public ArrayList<StmtInfo> statements = new ArrayList<>();
            public HashMap<String, ArrayList<StmtInfo>> nameSetToStatementsMap = new HashMap<>();
            public HashMap<String, ArrayList<StmtInfo>> nameGetToStatementsMap = new HashMap<>();

            /// Takes care of the hash maps too
            public void addStatement(StmtInfo stmtInfo)
            {
                statements.add(stmtInfo);
                for (String name : stmtInfo.namesSet)
                {
                    if (!nameSetToStatementsMap.containsKey(name))
                        nameSetToStatementsMap.put(name, new ArrayList<>());
                    nameSetToStatementsMap.get(name).add(stmtInfo);
                }
                for (String name : stmtInfo.namesGet)
                {
                    if (!nameGetToStatementsMap.containsKey(name))
                        nameGetToStatementsMap.put(name, new ArrayList<>());
                    nameGetToStatementsMap.get(name).add(stmtInfo);
                }
            }

            public ArrayList<StmtInfo> getStatementsFromNameSet(String name)
            {
                if (nameSetToStatementsMap.containsKey(name))
                {
                    return nameSetToStatementsMap.get(name);
                }
                return null;
            }
            public ArrayList<StmtInfo> getStatementsFromNameGet(String name)
            {
                if (nameGetToStatementsMap.containsKey(name))
                {
                    return nameGetToStatementsMap.get(name);
                }
                return null;
            }
        }
        class Visitor extends NodeVisitor {

            public HashMap<BlockStmt, HashMap<Integer, BlockFractionInfo>> blockFractionMap = new HashMap<>();
            public HashMap<BlockStmt, Integer> blockCurrentFractionMap = new HashMap<>();
            public HashMap<BlockStmt, Integer> blockCurrentIndexMap = new HashMap<>();
            public Stack<StmtInfo> currentStatements = new Stack<>();

            private void addName(String name, boolean isGet, boolean isSet)
            {
                for (StmtInfo stmtInfo : currentStatements)
                {
                    if (isGet)
                        stmtInfo.addNameGet(name);
                    if (isSet)
                        stmtInfo.addNameSet(name);
                }
            }
            private void addNames(Node n, boolean isGet, boolean isSet)
            {
                if (n instanceof NameExpr)
                {
                    String name = ((NameExpr) n).getName().asString();
                    addName(name, isGet, isSet);
                }
                else if (n instanceof SimpleName)
                {
                    String name = ((SimpleName) n).asString();
                    addName(name, isGet, isSet);
                }
                else if (n instanceof Name)
                {
                    String names = ((Name) n).asString();
                    for (String name : names.split("\\."))
                        addName(name, isGet, isSet);
                }
                for (Node ch : n.getChildNodes())
                    addNames(ch, isGet, isSet);
            }
            private void addNamesFromExpression(Expression expr)
            {
                // isGet for assignments and variable declarations is always true to preserve order.
                // Essential for when there's control dependency. Example:
                //   a = 0;
                //   if (something)
                //     a = 1;
                // Here 'a = 0' and 'a = 1' should not be swapped.
                // There are many more examples, but a useless
                //   a = 0;
                //   a = 1;
                //   a = 2;
                // where the first 2 can be swapped is too rare (or even non-existent) to consider.
                //
                // Also, every name is added to the set/get sets, without considering the dots as a lot of names are unknown.
                // Therefore, swapping setters with shared names even in the same block may change the code behavior,
                // as the getter of the last setter of a name may actually depend on an earlier setter in the block,
                // so the order of setters matters, with or without inner blocks and control dependencies.
                if (expr.isVariableDeclarationExpr())
                {
                    for (VariableDeclarator declarator : expr.asVariableDeclarationExpr().getVariables())
                    {
                        // isGet always true
                        addNames(declarator.getName(), true, true);
                        if (declarator.getInitializer().isPresent())
                            addNamesFromExpression(declarator.getInitializer().get());
                    }
                }
                else if (expr.isAssignExpr())
                {
                    // isGet always true
                    addNames(expr.asAssignExpr().getTarget(), true, true);
                    addNamesFromExpression(expr.asAssignExpr().getValue());
                }
                else if (expr.isMethodCallExpr())
                {
                    MethodCallExpr call = expr.asMethodCallExpr();
                    for (Expression arg : call.getArguments())
                    {
                        addNamesFromExpression(arg);
                    }
                    if (call.getScope().isPresent())
                        addNames(call.getScope().get(), true, true);
                    addNames(call.getName(), true, true);
                    // Method behavior is unknown, splitBlock is done.
                    splitBlock();
                }
                else if (
                        expr.isUnaryExpr()
                                && (
                                        expr.asUnaryExpr().getOperator().equals(UnaryExpr.Operator.POSTFIX_INCREMENT)
                                                || expr.asUnaryExpr().getOperator().equals(UnaryExpr.Operator.POSTFIX_DECREMENT)
                                                || expr.asUnaryExpr().getOperator().equals(UnaryExpr.Operator.PREFIX_INCREMENT)
                                                || expr.asUnaryExpr().getOperator().equals(UnaryExpr.Operator.PREFIX_DECREMENT)
                        )
                    )
                {
                    addNames(expr, true, true);
                }
                else
                {
                    for (Node child : expr.getChildNodes())
                    {
                        if (child instanceof Expression)
                            addNamesFromExpression((Expression) child);
                        else
                            addNames(expr, true, false);
                    }
                }
                if (expr.isObjectCreationExpr())
                    // Like method, behavior is unknown, splitBlock is done.
                    splitBlock();
            }
            private void splitBlock()
            {
                // Divide the blocks to 2, before and after the current statements.
                for (StmtInfo stmtInfo : currentStatements)
                {
                    if (stmtInfo.garbage)
                        continue; // Already done
                    int fraction = blockCurrentFractionMap.get(stmtInfo.block);
                    fraction++;
                    blockCurrentFractionMap.put(stmtInfo.block, fraction);
                    blockFractionMap.get(stmtInfo.block).put(fraction, new BlockFractionInfo(stmtInfo.block, fraction));
                    stmtInfo.garbage = true;
                }
            }
            private boolean stop = false;
            public boolean skip = false;
            @Override
            public void enter(Node n)
            {
                //super.enter(n);
                if (n instanceof LabeledStmt)
                {
                    stop = true;
                    skip = true;
                }
                if (stop)
                    return;
                if (n.getClass() == BlockStmt.class)
                {
                    BlockStmt block = (BlockStmt) n;
                    blockFractionMap.put(block, new HashMap<>());
                    blockFractionMap.get(block).put(0, new BlockFractionInfo(block, 0));
                    blockCurrentFractionMap.put(block, 0);
                    blockCurrentIndexMap.put(block, 0);
                }
                if (n.getParentNode().isPresent() && n.getParentNode().get().getClass() == BlockStmt.class)
                {
                    BlockStmt block = (BlockStmt) n.getParentNode().get();

                    NodeList<Statement> statements = block.getStatements();
                    int i;
                    for (i = blockCurrentIndexMap.get(block); i < statements.size() && statements.get(i) != n; i++);
                    if (i >= statements.size())
                    {
                        // That's unexpected.
                        System.out.println(
                                "[ALERT] The block somehow doesn't have this statement next."
                                        + " This could be a bug."
                                        + " Stopping and skipping."
                        );
                        stop = true;
                        skip = true;
                        return;
                    }
                    blockCurrentIndexMap.put(block, i);
                    currentStatements.push(new StmtInfo(block, blockCurrentFractionMap.get(block), i));
                }
            }
            @Override
            public void exit(Node n)
            {
                if (stop)
                {
                    //super.exit(n);
                    return;
                }

                // Process statement

                if (n instanceof ExpressionStmt)
                {
                    addNamesFromExpression(((ExpressionStmt) n).getExpression());
                }
                else if (n instanceof IfStmt)
                {
                    addNamesFromExpression(((IfStmt) n).getCondition());
                }
                else if (n instanceof ForStmt)
                {
                    ForStmt stmt = (ForStmt) n;
                    for (Expression expr : stmt.getInitialization())
                        addNamesFromExpression(expr);
                    if (stmt.getCompare().isPresent())
                        addNamesFromExpression(stmt.getCompare().get());
                    for (Expression expr: stmt.getUpdate())
                        addNamesFromExpression(expr);
                }
                else if (n instanceof ForEachStmt)
                {
                    ForEachStmt stmt = (ForEachStmt) n;
                    addNamesFromExpression(stmt.getIterable());
                    addNamesFromExpression(stmt.getVariable());
                }
                else if (n instanceof WhileStmt)
                {
                    WhileStmt stmt = (WhileStmt) n;
                    addNamesFromExpression(stmt.getCondition());
                }
                else if (n instanceof DoStmt)
                {
                    DoStmt stmt = (DoStmt) n;
                    addNamesFromExpression(stmt.getCondition());
                }
                else if (n instanceof AssertStmt)
                {
                    AssertStmt stmt = (AssertStmt) n;
                    addNamesFromExpression(stmt.getCheck());
                }
                else if (n instanceof SwitchStmt)
                {
                    SwitchStmt stmt = (SwitchStmt) n;
                    addNamesFromExpression(stmt.getSelector());
                }
                else if (n instanceof SynchronizedStmt)
                {
                    SynchronizedStmt stmt = (SynchronizedStmt) n;
                    addNamesFromExpression(stmt.getExpression());
                }
                else if (n instanceof YieldStmt)
                {
                    YieldStmt stmt = (YieldStmt) n;
                    addNamesFromExpression(stmt.getExpression());
                }
                else if (
                        n instanceof ReturnStmt
                                || n instanceof BreakStmt
                                || n instanceof ContinueStmt
                                || n instanceof ThrowStmt
                                || n instanceof UnparsableStmt
                )
                {
                    // This will affect whether some statements are run, splitBlock is done.
                    splitBlock();
                }
                // No need to splitBlock in ClassOrInterfaceDeclaration, LocalClassDeclarationStmt, LocalRecordDeclarationStmt, ...
                else if (n instanceof ClassOrInterfaceDeclaration)
                {
                    ClassOrInterfaceDeclaration type_declaration = (ClassOrInterfaceDeclaration)n;
                    addNames(type_declaration.getName(), true, true);
                    for (Node node : type_declaration.getAnnotations())
                        addNames(node, true, false);
                    for (Node node : type_declaration.getExtendedTypes())
                        addNames(node, true, false);
                    for (Node node : type_declaration.getImplementedTypes())
                        addNames(node, true, false);
                    for (TypeParameter param : type_declaration.getTypeParameters())
                        addNames(param, true, false);
                }
                else if (n instanceof RecordDeclaration)
                {
                    RecordDeclaration type_declaration = (RecordDeclaration)n;
                    addNames(type_declaration.getName(), true, true);
                    for (AnnotationExpr node : type_declaration.getAnnotations())
                        addNames(node, true, false);
                    for (ClassOrInterfaceType node : type_declaration.getImplementedTypes())
                        addNames(node, true, false);
                    for (TypeParameter param : type_declaration.getTypeParameters())
                        addNames(param, true, false);
                }
                else if (n instanceof EnumDeclaration)
                {
                    EnumDeclaration type_declaration = (EnumDeclaration)n;
                    addNames(type_declaration.getName(), true, true);
                    for (Node node : type_declaration.getAnnotations())
                        addNames(node, true, false);
                    for (Node node : type_declaration.getImplementedTypes())
                        addNames(node, true, false);
                }
                else if (n instanceof AnnotationDeclaration)
                {
                    AnnotationDeclaration type_declaration = (AnnotationDeclaration)n;
                    addNames(type_declaration.getName(), true, true);
                    for (Node node : type_declaration.getAnnotations())
                        addNames(node, true, false);
                }
                else if (n instanceof TypeDeclaration<?>)
                {
                    TypeDeclaration<?> type_declaration = (TypeDeclaration<?>)n;
                    addNames(type_declaration.getName(), true, true);
                    for (Node node : type_declaration.getAnnotations())
                        addNames(node, true, false);
                }
                else if (n instanceof CallableDeclaration<?>)
                {
                    CallableDeclaration<?> declaration = (CallableDeclaration<?>)n;
                    addNames(declaration.getName(), true, true);
                    for (Node node : declaration.getAnnotations())
                        addNames(node, true, false);
                    for (Parameter param : declaration.getParameters())
                        for (String name : param.getType().asString().split("\\."))
                            addName(name, true, false);
                    for (ReferenceType referenceType : declaration.getThrownExceptions())
                        for (String name : referenceType.asString().split("\\."))
                            addName(name, true, false);
                    for (TypeParameter param : declaration.getTypeParameters())
                        addNames(param, true, false);
                }
                // BlockStmt is already considered elsewhere
                // ExplicitConstructorInvocationStmt doesn't exist in a method
                // TryStmt's catch parameters don't matter as the statements in those blocks won't be moved out.

                if (n.getParentNode().isPresent() && n.getParentNode().get().getClass() == BlockStmt.class)
                {
                    BlockStmt block = (BlockStmt) n.getParentNode().get();

                    StmtInfo stmtInfo = currentStatements.pop();
                    if (stmtInfo.block != block)
                    {
                        System.out.println(
                                "[ALERT] The block and the popped StmtInfo's block don't match."
                                        + " This should be a bug."
                                        + " Stopping and skipping."
                        );
                        stop = true;
                        skip = true;
                        return;
                    }
                    if (!stmtInfo.garbage)
                        blockFractionMap.get(stmtInfo.block).get(stmtInfo.blockFraction).addStatement(stmtInfo);
                }
                if (n.getClass() == BlockStmt.class)
                {
                    // Nothing
                }
                //super.exit(n);
            }
        }
        Visitor visitor = new Visitor();
        visitor.visit(method);
        // Print info:
        /*for (HashMap<Integer, BlockFractionInfo> map : visitor.blockFractionMap.values())
        {
            for (BlockFractionInfo blockFractionInfo : map.values())
            {
                System.out.println("[BLOCK]:");
                System.out.println(blockFractionInfo.block);
                System.out.println("[BLOCK FRACTION]:");
                System.out.println(blockFractionInfo.blockFraction);
                for (StmtInfo stmtInfo : blockFractionInfo.statements)
                {
                    System.out.println("[STMT]:");
                    System.out.println(stmtInfo.indexInBlock);
                    System.out.println(stmtInfo.block.getStatements().get(stmtInfo.indexInBlock));
                    System.out.println("[SET]:");
                    for (String name : stmtInfo.namesSet)
                    {
                        System.out.println(name);
                        System.out.println();
                    }
                    System.out.println("[GET]:");
                    for (String name : stmtInfo.namesGet)
                    {
                        System.out.println(name);
                        System.out.println();
                    }
                }
            }
        }*/
        if (visitor.skip)
            return 0;
        int change_counter = 0;
        Random random = new Random();
        class BlockFractionDependencyGraphNode
        {
            public BlockFractionDependencyGraphNode(StmtInfo stmtInfo)
            {
                this.stmtInfo = stmtInfo;
            }
            public StmtInfo stmtInfo;
            public HashMap<String, BlockFractionDependencyGraphNode> setters = new HashMap<>();
            public HashMap<String, ArrayList<BlockFractionDependencyGraphNode>> incompatibleSetters = new HashMap<>();
            public HashMap<String, ArrayList<BlockFractionDependencyGraphNode>> incompatibleGetters = new HashMap<>();
            public HashMap<String, ArrayList<BlockFractionDependencyGraphNode>> getters = new HashMap<>();
            public void addSetter(String name, BlockFractionDependencyGraphNode setterNode)
            {
                if (setters.containsKey(name))
                    System.out.println(
                            "[ALERT] The setter somehow already existed."
                                    + " This should be a bug."
                                    + " Not stopping."
                    );
                setters.put(name, setterNode);

                //setterNode.getters.add(this);
                if (!setterNode.getters.containsKey(name))
                    setterNode.getters.put(name, new ArrayList<>());
                setterNode.getters.get(name).add(this);
            }
            public void addIncompatibleSetter(String name, BlockFractionDependencyGraphNode setterNode)
            {
                if (!incompatibleSetters.containsKey(name))
                    incompatibleSetters.put(name, new ArrayList<>());
                incompatibleSetters.get(name).add(setterNode);

                if (!setterNode.incompatibleGetters.containsKey(name))
                    setterNode.incompatibleGetters.put(name, new ArrayList<>());
                setterNode.incompatibleGetters.get(name).add(this);
            }
            public boolean swapWith(
                    BlockFractionDependencyGraphNode other
                )
            {
                if (stmtInfo.indexInBlock == other.stmtInfo.indexInBlock)
                    return false;

                BlockFractionDependencyGraphNode a, b;
                if (stmtInfo.indexInBlock < other.stmtInfo.indexInBlock)
                {
                    a = this;
                    b = other;
                }
                else
                {
                    a = other;
                    b = this;
                }
                int a_i = a.stmtInfo.indexInBlock;
                int b_i = b.stmtInfo.indexInBlock;

                // from (current state)
                // ... a; ... b; ...
                // to
                // ... b; ... a; ...

                // what to look for:
                // (NOT b.incompatibleSetters, there are none because already checked b.setters in the middle)
                // b; // formerly a;
                // [a.getters (including b) and b.setters (including a)]
                // [a.incompatibleSetters (including b, with a's setters before the zone (no check for zone required))]
                // [b.incompatibleGetters (including a, with the setters before the zone)]
                //                        (duplicate action of including a, but better duplicate than sorry)
                // [incompatibleSetters (including a) of b.getters after the zone]
                // a; // formerly b;
                // [a.incompatibleGetters (with the setters in the middle including b)]

                // a.getters
                for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : a.getters.entrySet())
                {
                    for (BlockFractionDependencyGraphNode getter : entry.getValue())
                    {
                        if (getter.stmtInfo != null && getter.stmtInfo.indexInBlock <= b_i)
                            return false;
                    }
                }
                // b.setters
                for (Map.Entry<String, BlockFractionDependencyGraphNode> entry : b.setters.entrySet())
                {
                    BlockFractionDependencyGraphNode setter = entry.getValue();
                    if (setter.stmtInfo != null && setter.stmtInfo.indexInBlock >= a_i)
                        return false;
                }

                // a.incompatibleGetters
                for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : a.incompatibleGetters.entrySet())
                {
                    for (BlockFractionDependencyGraphNode incompatibleGetter : entry.getValue())
                    {
                        // incompatibleGetter.stmtInfo == null
                        // => rootGetter (end of the block fraction)
                        if (incompatibleGetter.stmtInfo == null || incompatibleGetter.stmtInfo.indexInBlock > b_i)
                        {
                            if (!incompatibleGetter.setters.containsKey(entry.getKey()))
                            {
                                System.out.println(
                                        "[ALERT] Incompatible getter doesn't have the matching setter (#1)."
                                                + " This should be a bug."
                                                + " Ignoring this and continuing."
                                );
                                continue;
                            }
                            BlockFractionDependencyGraphNode setter = incompatibleGetter.setters.get(entry.getKey());
                            if (setter.stmtInfo != null)
                            {
                                int i = setter.stmtInfo.indexInBlock;
                                if (a_i < i && i <= b_i)
                                {
                                    return false;
                                }
                            }
                        }
                    }
                }
                // a.incompatibleSetters
                for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : a.incompatibleSetters.entrySet())
                {
                    for (BlockFractionDependencyGraphNode incompatibleSetter : entry.getValue())
                    {
                        if (incompatibleSetter.stmtInfo != null)
                        {
                            int i = incompatibleSetter.stmtInfo.indexInBlock;
                            if (a_i < i && i <= b_i)
                            {
                                // The setter is definitely before the zone
                                // No need to check
                                return false;
                            }
                        }
                    }
                }
                // b.incompatibleGetters
                for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : b.incompatibleGetters.entrySet())
                {
                    for (BlockFractionDependencyGraphNode incompatibleGetter : entry.getValue())
                    {
                        if (incompatibleGetter.stmtInfo != null)
                        {
                            int i = incompatibleGetter.stmtInfo.indexInBlock;
                            if (a_i <= i && i < b_i)
                            {
                                if (!incompatibleGetter.setters.containsKey(entry.getKey()))
                                {
                                    System.out.println(
                                            "[ALERT] Incompatible getter doesn't have the matching setter (#2)."
                                                    + " This should be a bug."
                                                    + " Ignoring this and continuing."
                                    );
                                    continue;
                                }
                                BlockFractionDependencyGraphNode setter = incompatibleGetter.setters.get(entry.getKey());
                                // setter.stmtInfo == null
                                // => rootSetter (start of the block fraction)
                                if (setter.stmtInfo == null || setter.stmtInfo.indexInBlock < a_i)
                                {
                                    return false;
                                }
                            }
                        }
                    }
                }

                // incompatibleSetters of b.getters after the zone
                for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : b.getters.entrySet())
                {
                    for (BlockFractionDependencyGraphNode getter : entry.getValue())
                    {
                        // getter.stmtInfo == null
                        // => rootGetter (end of the block fraction)
                        if (getter.stmtInfo == null || getter.stmtInfo.indexInBlock > b_i)
                        {
                            if (!getter.incompatibleSetters.containsKey(entry.getKey()))
                                continue;
                            for (BlockFractionDependencyGraphNode incompatibleSetter : getter.incompatibleSetters.get(entry.getKey()))
                            {
                                if (incompatibleSetter.stmtInfo != null)
                                {
                                    int i = incompatibleSetter.stmtInfo.indexInBlock;
                                    if (a_i <= i && i < b_i)
                                    {
                                        return false;
                                    }
                                }
                            }
                        }
                    }
                }

                // Prepare to swap
                BlockStmt block = a.stmtInfo.block;
                if (block != b.stmtInfo.block)
                {
                    System.out.println(
                            "[ALERT] The block of the 2 statements to swap don't match."
                                    + " This should be a bug."
                                    + " Skipping."
                    );
                    return false;
                }
                // Swap
                Statement a_stmt = block.getStatement(a_i);
                Statement b_stmt = block.getStatement(b_i);
                block.setStatement(a_i, b_stmt);
                block.setStatement(b_i, a_stmt);
                a.stmtInfo.indexInBlock = b_i;
                b.stmtInfo.indexInBlock = a_i;
                return true;
            }
        }
        for (HashMap<Integer, BlockFractionInfo> blockFractionInfoMap : visitor.blockFractionMap.values())
        {
            for (BlockFractionInfo blockFractionInfo : blockFractionInfoMap.values()) // Process each block fraction separately
            {
                if (blockFractionInfo.statements.size() < 2)
                    continue;
                // Construct the graph
                BlockFractionDependencyGraphNode rootSetter = new BlockFractionDependencyGraphNode(null); // block start
                BlockFractionDependencyGraphNode rootGetter = new BlockFractionDependencyGraphNode(null); // end of block
                HashMap<String, BlockFractionDependencyGraphNode> lastSetters = new HashMap<>();
                HashMap<Integer, BlockFractionDependencyGraphNode> allNodes = new HashMap<>();
                allNodes.put(-1, rootSetter);
                allNodes.put(-2, rootGetter);
                for (StmtInfo stmtInfo : blockFractionInfo.statements)
                {
                    BlockFractionDependencyGraphNode stmtNode = new BlockFractionDependencyGraphNode(stmtInfo);
                    allNodes.put(stmtInfo.indexInBlock, stmtNode);
                }
                for (StmtInfo stmtInfo : blockFractionInfo.statements)
                {
                    BlockFractionDependencyGraphNode stmtNode = allNodes.get(stmtInfo.indexInBlock);
                    // Find the setters
                    for (String name : stmtInfo.namesGet)
                    {
                        BlockFractionDependencyGraphNode setterNode;

                        setterNode = lastSetters.getOrDefault(name, rootSetter);

                        stmtNode.addSetter(
                                name,
                                setterNode
                        );

                        ArrayList<StmtInfo> potentialIncompatibles = blockFractionInfo.getStatementsFromNameSet(name);
                        if (potentialIncompatibles != null)
                        {
                            for (StmtInfo potentialIncompatible : potentialIncompatibles)
                            {
                                if (potentialIncompatible != setterNode.stmtInfo && potentialIncompatible != stmtInfo)
                                {
                                    stmtNode.addIncompatibleSetter(
                                            name,
                                            allNodes.get(potentialIncompatible.indexInBlock)
                                    );
                                }
                            }
                        }
                    }
                    // Update last setters
                    for (String name : stmtInfo.namesSet)
                    {
                        lastSetters.put(name, stmtNode);
                    }
                }
                // Finally, construct rootGetter
                for (Map.Entry<String, BlockFractionDependencyGraphNode> entry : lastSetters.entrySet())
                {
                    BlockFractionDependencyGraphNode setterNode = entry.getValue();
                    String name = entry.getKey();
                    rootGetter.addSetter(name, setterNode);
                    ArrayList<StmtInfo> potentialIncompatibles = blockFractionInfo.getStatementsFromNameSet(name);
                    if (potentialIncompatibles != null)
                    {
                        for (StmtInfo potentialIncompatible : potentialIncompatibles)
                        {
                            if (potentialIncompatible != setterNode.stmtInfo)
                            {
                                rootGetter.addIncompatibleSetter(
                                        name,
                                        allNodes.get(potentialIncompatible.indexInBlock)
                                );
                            }
                        }
                    }
                }
                // Print info:
                /*for (StmtInfo stmtInfo : blockFractionInfo.statements)
                {
                    System.out.println("\n[STMT]:");
                    System.out.println(stmtInfo.block.getStatement(stmtInfo.indexInBlock));
                    System.out.println();
                    BlockFractionDependencyGraphNode stmtNode = allNodes.get(stmtInfo.indexInBlock);
                    // Print setters
                    System.out.println("[SETTERS]:");
                    for (Map.Entry<String, BlockFractionDependencyGraphNode> entry : stmtNode.setters.entrySet())
                    {
                        StmtInfo setterInfo = entry.getValue().stmtInfo;
                        System.out.println("NAME: '" + entry.getKey() + "', SETTER: "
                                + (setterInfo == null ? "rootSetter" :setterInfo.block.getStatement(setterInfo.indexInBlock)));
                    }
                    // Print getters
                    for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : stmtNode.getters.entrySet())
                    {
                        System.out.println("[GETTERS] for name '" + entry.getKey() + "':");
                        for (BlockFractionDependencyGraphNode node : entry.getValue())
                        {
                            StmtInfo info = node.stmtInfo;
                            System.out.println("GETTER: "
                                    + (info == null ?
                                    "rootGetter"
                                    : info.block.getStatement(info.indexInBlock)));
                        }
                    }
                    // Print incompatibleSetters
                    for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : stmtNode.incompatibleSetters.entrySet())
                    {
                        System.out.println("[INCOMPATIBLE-SETTERS] for name '" + entry.getKey() + "':");
                        for (BlockFractionDependencyGraphNode node : entry.getValue())
                        {
                            StmtInfo info = node.stmtInfo;
                            System.out.println("INCOMPATIBLE SETTER: "
                                    + (info == null ?
                                        "rootSetter"
                                        : info.block.getStatement(info.indexInBlock)));
                        }
                    }
                    // Print incompatibleGetters
                    for (Map.Entry<String, ArrayList<BlockFractionDependencyGraphNode>> entry : stmtNode.incompatibleSetters.entrySet())
                    {
                        System.out.println("[INCOMPATIBLE-GETTERS] for name '" + entry.getKey() + "':");
                        for (BlockFractionDependencyGraphNode node : entry.getValue())
                        {
                            StmtInfo info = node.stmtInfo;
                            System.out.println("INCOMPATIBLE GETTER: "
                                    + (info == null ?
                                    "rootGetter"
                                    : info.block.getStatement(info.indexInBlock)));
                        }
                    }
                }*/
                // Swap stmt operation section
                int nodes_count = blockFractionInfo.statements.size();
                int nodes_index_offset = blockFractionInfo.statements.get(0).indexInBlock; // size < 2 already rejected
                int try_count = (int)(swap_attempts_per_statement_count * nodes_count);
                if (nodes_count == 2)
                    // swap_attempt_per_statement_count is >= 0
                    try_count = random.nextDouble() < 1.0 - 1.0 / (1.0 + swap_attempts_per_statement_count) ? 1 : 0;
                for (int k = 0; k < try_count; k++)
                {
                    double distance_d = random.nextDouble();
                    distance_d *= distance_d;
                    int distance = 1 + (int)(distance_d * (nodes_count - 1));
                    if (distance >= nodes_count)
                        distance = nodes_count - 1;
                    int i = random.nextInt(nodes_count - distance);
                    int j = i + distance;
                    // Check and swap
                    if (allNodes.get(nodes_index_offset + i).swapWith(allNodes.get(nodes_index_offset + j)))
                    {
                        change_counter++;
                    }
                }
            }
        }
        return change_counter;
    }
    public static void swapRandomStatementsInBlocksTest(int repeats, double swap_attempts_per_statement_count)
    {
        String basic_block_fragment_test_method = "void a()\n{\n\tsome_type beanCount, someLongNAMEHere; some_type ant_value = 1, cat; some_type DUNE, f; some_type e;\n"
                + "\tsome_type some, other, more, names, method;\n"
                + "\tbreak;\n"
                + "\tthis.ant_value.b.c.d();\n"
                + "\t// Comment #1\n"
                + "\tthis.something.some.other.names = ant_value.some.more.names + beanCount.some.method() * cat / DUNE + 1.0f == 0.0 && e || (boolean)f; \n"
                + "\tsomeLongNAMEHere = ant_value < beanCount && cat <= DUNE || f > e && (f >= e || a != e);\n"
                + "\tcontinue;\n"
                + "\tfor (int i = 0; i < ant_value; i++) { ant_value = i + 1 + unknown; }\n"
                + "\tfor (unknown_i = 0; unknown_i < ant_value; i++) { ant_value = unknown_i + 1; }\n"
                + "\tif (ant_value < beanCount == cat < DUNE)\n"
                + "\t\tuntouched_unknowns = u1 + u2 * u3 + u4;\n"
                + "\telse if (someLongNAMEHere) { inBlockVar1 = ibu1; inBlockVar2 = ibu2; }\n"
                + "\telse other_untouched_unknowns = u5 + u6 * u7 + u8;\n"
                + "\tswitch (a) { case 0: a = b; c = d; case 1: b = a; }\n"
                + "}";
        String sort_test_method = "int find(T[] arr, T item)\n" +
                "{\n" +
                "    int start = 0;\n" +
                "    int stop = arr.length;\n" +
                "    int middle = (start + stop) / 2;\n" +
                "    while (start < stop)\n" +
                "    {\n" +
                "        if (item == arr[middle])\n" +
                "            return middle;\n" +
                "        if (item < arr[middle])\n" +
                "            stop = middle - 1;\n" +
                "        else\n" +
                "            start = middle + 1;\n" +
                "    }\n" +
                "    if (item == arr[start])\n" +
                "        return start;\n" +
                "    return -1;\n" +
                "}";
        String test_method = "boolean m()\n" +
                "{\n" +
                "    some_type a = 0;\n" +
                //"    func_call().something;\n" +
                //"    something.func_call().something;\n" +
                "    some_type b = 4;\n" +
                "    some_type c = a + 2;\n" +
                "    a++;\n" +
                "    some_type d = a * 2;\n" +
                "    e.ee = b.bb + d;\n" +
                "    f = c + b;\n" +
                "    g = 1;\n" +
                "    a = 1;\n" +
                "    h = a + d + 1;\n" +
                "    some_type a = 2;\n" +
                "    h = a + d + 2;\n" +
                //"    class A { void m() { mem = a + b + 2; } }\n" +
                //"    obj = new A() { void m() { a = 0; } };\n" +
                //"    obj = new A();\n" +
                "    a = 3;\n" +
                "    h = a + d + 3;\n" +
                "    while (e)\n" +
                "    {\n" +
                "        if (d)\n" +
                "            b = 0;\n" +
                "        if (d - 1)\n" +
                "            b = 1;\n" +
                "        if (d - 2)\n" +
                "            b = 2;\n" +
                "        if (d - 3)\n" +
                "            b = 3;\n" +
                "    }\n" +
                "    while (e)\n" +
                "    {\n" +
                "        if (d)\n" +
                "            b = 0;\n" +
                "    }\n" +
                "    while (e)\n" +
                "    {\n" +
                "        if (d)\n" +
                "            c = 0;\n" +
                "    }\n" +
                "    if (e)\n" +
                "    {\n" +
                "       c = 0;\n" +
                "       u1 = c;\n" +
                "       u2 = e;\n" +
                "       u3 = c;\n" +
                "       u4 = c;\n" +
                "    }\n" +
                "    if (a)\n" +
                "        return true;\n" +
                "    return false;\n" +
                "}";
        System.out.println("Test method:");
        System.out.println(test_method);
        System.out.println(repeats + " Results:");
        for (int i = 0; i < repeats; i++)
        {
            MethodDeclaration m = StaticJavaParser.parseMethodDeclaration(test_method);
            int count = CodeAugmentation.swapRandomStatementsInBlocks(
                    m,
                    swap_attempts_per_statement_count
            );
            System.out.println(m.toString());
            System.out.println("Number of changes: " + count);
        }
    }
}
