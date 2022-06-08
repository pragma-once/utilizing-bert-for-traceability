import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.Node;
import com.github.javaparser.ast.body.MethodDeclaration;

import java.util.ArrayList;

public class Utils
{
    public static ArrayList<MethodDeclaration> getMethodDeclarations(CompilationUnit compilationUnit)
    {
        ArrayList<MethodDeclaration> result = new ArrayList<>();
        class Visitor extends NodeVisitor
        {
            @Override
            public void enter(Node n)
            {
                if (n instanceof MethodDeclaration)
                    result.add((MethodDeclaration) n);
            }

            @Override
            public void exit(Node n)
            {
            }
        }
        Visitor visitor = new Visitor();
        visitor.visit(compilationUnit);
        return result;
    }
}
