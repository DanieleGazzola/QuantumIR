from xdsl.printer import Printer
from frontend.common_subexpr_elimination import CommonSubexpressionElimination
from frontend.remove_unused_op import RemoveUnusedOperations
from frontend.hermitian_gates_transformation import HermitianGatesElimination
from xdsl.pattern_rewriter import PatternRewriteWalker
from xdsl.dialects.builtin import ModuleOp, FunctionType
from xdsl.builder import Builder
from dialect import dialect as quantum
                        ####### TRANSFORMATIONS TEST PROGRAM ########
@ModuleOp
@Builder.implicit_region
def module():
    @Builder.implicit_region
    def main() -> None:
        a_0 = quantum.InitOp(quantum.IntegerType(1)).res
        a_1 = quantum.InitOp(quantum.IntegerType(1)).res
        a_2 = quantum.InitOp(quantum.IntegerType(1)).res
        a_3 = quantum.CCNotOp(a_0, a_1, a_2).res
        a_31 = quantum.NotOp(a_0).res
        a_4 = quantum.CCNotOp(a_0, a_1, a_3).res
        quantum.MeasureOp(a_4)
        quantum.MeasureOp(a_31)

    quantum.FuncOp("prova", main)

Printer().print_op(module)

while True:

    start_module = module.clone()
    PatternRewriteWalker(RemoveUnusedOperations()).rewrite_module(module)

    # check if any unused operations were removed
    if len(start_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
        print("\n\nRemoved unused operations")
        Printer().print_op(module)

    middle_module = module.clone()
    CommonSubexpressionElimination().apply(module)

    # check if any common subexpressions were eliminated
    if len(middle_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
        print("\n\nCommon subexpression elimination")
        Printer().print_op(module)

    end_module = module.clone()
    HermitianGatesElimination().apply(module)

    # check if any common subexpressions were eliminated
    if len(end_module.body.block._first_op.body.block.ops) != len(module.body.block._first_op.body.block.ops):
        print("\n\nHermitian elimination")
        Printer().print_op(module)

    # check if there were no changes in the last iteration
    if len(start_module.body.block._first_op.body.block.ops) == len(module.body.block._first_op.body.block.ops):
        print("\n\nNo more transformations possible\n")
        break

# Final IR
print("\nFinal IR:\n")
Printer().print_op(module)
