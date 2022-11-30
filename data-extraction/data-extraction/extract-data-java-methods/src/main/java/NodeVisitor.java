import com.github.javaparser.ast.Node;

public abstract class NodeVisitor
{
    public void visit(Node n)
    {
        enter(n);
        for (Node child : n.getChildNodes())
            visit(child);
        exit(n);
    }
    public abstract void enter(Node n);
    public abstract void exit(Node n);
}
