import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.body.VariableDeclarator;
import com.github.javaparser.ast.stmt.*;

import java.util.HashMap;
import java.util.Stack;

public class NodeVisitorWithScopeTracking extends NodeVisitor
{
    public HashMap<Integer, HashMap<String, VariableDeclarator>> blocksToLocalVariableNamesToInfo = new HashMap<>();;
    public Stack<Integer> currentBlocksStack = new Stack<>();
    private int stackCounter = 0;

    protected VariableDeclarator getVariableDeclarator(String name)
    {
        for (int i = currentBlocksStack.size() - 1; i >= 0; i--)
            if (blocksToLocalVariableNamesToInfo.get(currentBlocksStack.get(i)).containsKey(name))
                return blocksToLocalVariableNamesToInfo.get(currentBlocksStack.get(i)).get(name);
        return null;
    }

    protected String getVariableType(String name)
    {
        VariableDeclarator declarator = getVariableDeclarator(name);
        if (declarator != null)
            return declarator.getType().asString();
        return null;
    }

    private void enterBlock()
    {
        blocksToLocalVariableNamesToInfo.put(stackCounter, new HashMap<>());
        currentBlocksStack.push(stackCounter);
        stackCounter++;
    }

    private void exitBlock()
    {
        currentBlocksStack.pop();
    }

    @Override
    public void enter(Node n)
    {
        if (n.getClass() == BlockStmt.class
                || n.getClass() == IfStmt.class
                || n.getClass() == ForStmt.class
                || n.getClass() == ForEachStmt.class
                || n.getClass() == WhileStmt.class
                || n.getClass() == DoStmt.class
        )
            enterBlock();
        if (n.getClass() == VariableDeclarator.class)
        {
            VariableDeclarator declarator = (VariableDeclarator) n;
            blocksToLocalVariableNamesToInfo.get(currentBlocksStack.peek())
                    .put(declarator.getName().asString(), declarator);
        }
    }

    @Override
    public void exit(Node n)
    {
        if (n.getClass() == BlockStmt.class
                || n.getClass() == IfStmt.class
                || n.getClass() == ForStmt.class
                || n.getClass() == ForEachStmt.class
                || n.getClass() == WhileStmt.class
                || n.getClass() == DoStmt.class
        )
            exitBlock();
    }
}
