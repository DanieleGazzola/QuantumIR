import json
from dataclasses import dataclass
from typing import List, Optional, Union, Any, Dict

#################################### DATACLASSES ############################################################################################################
# This file contains the dataclasses that represent the AST of the JSON file and the logic to convert it.
# Each dataclass corresponds to an AST element. 
# We then work on the dataclass tree to build the MLIR.

@dataclass
class ASTNode:
    kind: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Assignment:
    kind: str
    type: str
    left: 'NamedValue'
    right: Union['NamedValue', 'BinaryOp', 'Conversion']
    isNonBlocking: bool
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class BinaryOp:
    kind: str
    type: str
    op: str
    left: Union['NamedValue', 'BinaryOp']
    right: Union['NamedValue', 'BinaryOp']
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class UnaryOp:
    kind: str
    type: str
    op: str
    operand: Union['NamedValue', 'BinaryOp', 'Conversion']
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class CompilationUnit:
    kind: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class ContinuousAssign:
    kind: str
    assignment: 'Assignment'
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Conversion:
    kind: str
    type: str
    operand: Union['Conversion','NamedValue','IntegerLiteral']
    constant: Optional[str] = None
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Instance:
    kind: str
    body: 'InstanceBody'
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class InstanceBody:
    kind: str
    members: List[Union['Port', 'PrimitiveInstance', 'Variable', 'ContinuousAssign', 'ProceduralBlock', 'Net']]
    definition: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class IntegerLiteral:
    kind: str
    type: str
    value: str
    constant: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class NamedValue:
    kind: str
    type: str
    symbol: str
    constant: Optional[str] = None
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Net:
    kind: str
    type: str
    netType: 'NetType'
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class NetType:
    kind: str
    type: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Port:
    kind: str
    type: str
    direction: str
    internalSymbol: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class PrimitiveInstance:
    kind: str
    primitiveType: str
    ports: List[Union['Assignment', 'NamedValue']]
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Root:
    kind: str
    members: List[Union['CompilationUnit', 'Instance']]
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Variable:
    kind: str
    type: str
    lifetime: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class ProceduralBlock:
    kind: str
    body : 'Block'
    procedureKind : str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Block:
    kind: str
    blockKind : str
    body: List[Union['ExpressionStatement']]
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class ExpressionStatement:
    kind: str
    expr: List[Union['Assignment', 'BinaryOp', 'UnaryOp', 'NamedValue', 'Conversion']]
    name: Optional[str] = None
    addr: Optional[int] = None


##################################################################################################################################################################

def from_dict(data: Dict[str, Any]) -> ASTNode:

    if isinstance(data, list):
        return [from_dict(item) for item in data]

    if isinstance(data, dict):
        kind = data.get('kind', None)
        common_fields = {
            'name': data.get('name'),
            'kind': kind,
            'addr': data.get('addr')
        }

        if kind == 'Assignment':
            return Assignment(type=data['type'], left=from_dict(data['left']), right=from_dict(data['right']), isNonBlocking=data['isNonBlocking'], **common_fields)
        elif kind == 'BinaryOp':
            return BinaryOp(type=data['type'], op=data['op'], left=from_dict(data['left']), right=from_dict(data['right']), **common_fields)
        elif kind == 'UnaryOp':
            return UnaryOp(type=data['type'], op=data['op'], operand=from_dict(data['operand']), **common_fields)
        elif kind == 'CompilationUnit':
            return CompilationUnit(**common_fields)
        elif kind == 'ContinuousAssign':
            return ContinuousAssign(assignment=from_dict(data['assignment']), **common_fields)
        elif kind == 'Conversion':
            if 'constant' in data:
                return Conversion(type=data['type'], operand=from_dict(data['operand']), constant=data['constant'], **common_fields)
            else:
                return Conversion(type=data['type'], operand=from_dict(data['operand']), **common_fields)
        elif kind == 'Instance':
            return Instance(body=from_dict(data['body']), **common_fields)
        elif kind == 'InstanceBody':
            return InstanceBody(members=from_dict(data['members']), definition=data['definition'], **common_fields)
        elif kind == 'NamedValue':
            return NamedValue(type=data['type'], symbol=data['symbol'], constant=data.get('constant', None), **common_fields)
        elif kind == 'Net':
            return Net(type=data['type'], netType=from_dict(data['netType']), **common_fields)
        elif kind == 'NetType':
            return NetType(type=data['type'], **common_fields)
        elif kind == 'Port':
            return Port(type=data['type'], direction=data['direction'], internalSymbol=data['internalSymbol'], **common_fields)
        elif kind == 'PrimitiveInstance':
            return PrimitiveInstance(primitiveType=data['primitiveType'], ports=from_dict(data['ports']), **common_fields)
        elif kind == 'Root':
            return Root(members=from_dict(data['members']), **common_fields)
        elif kind == 'Variable':
            return Variable(type=data['type'], lifetime=data['lifetime'], **common_fields)
        elif kind == 'ProceduralBlock':
            return ProceduralBlock(body=from_dict(data['body']), procedureKind=data['procedureKind'], **common_fields)
        elif kind == 'Block':
            return Block(blockKind=data['blockKind'], body=from_dict(data['body']), **common_fields)
        elif kind == 'ExpressionStatement':
            return ExpressionStatement(expr=from_dict(data['expr']), **common_fields)
        elif kind == "List":
            return [from_dict(item) for item in data['list']]
        elif kind == "IntegerLiteral":
            return IntegerLiteral(type=data['type'], value=data['value'], constant=data['constant'], **common_fields)
        else:
            raise ValueError(f"Unknown kind: {kind}")
    return data

##################################################################################################################################################################

# function that takes as input a JSON string and returns a Root dataclass
def json_to_dataclass(json_data: str) -> Root:
    data = json.loads(json_data)
    return from_dict(data)

##################################################################################################################################################################

def read_json_file(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.read()

##################################################################################################################################################################
# This function takes a Root dataclass and returns a formatted string representation of the AST
def format_root(root: Root, indent: int = 0) -> str:
    return format_ast(root, indent)

# This recursive function takes an ASTNode and returns a formatted string representation of the AST
def format_ast(ast: ASTNode, indent: int = 0) -> str:
    lines = []
    indent_str = " " * indent

    def append_info(prefix: str, obj: Optional[ASTNode]):
        if obj:
            if hasattr(obj, 'name') and obj.name:
                lines.append(f"{indent_str}{prefix} Name: {obj.name}")
            if hasattr(obj, 'type'):
                lines.append(f"{indent_str}{prefix} Type: {obj.type}")
            if hasattr(obj, 'symbol'):
                lines.append(f"{indent_str}{prefix} Symbol: {obj.symbol}")
            if hasattr(obj, 'value'):
                if hasattr(obj, 'selector'):
                    lines.append(f"{indent_str}{prefix} Value: {obj.value.symbol}")
                    if isinstance(obj.selector, NamedValue):
                        lines.append(f"{indent_str}{prefix} Selector:")
                        lines.extend(format_ast(obj.selector, indent + 4))
                    elif isinstance(obj.selector, BinaryOp):
                        lines.append(f"{indent_str}{prefix} Selector:")
                        lines.extend(format_ast(obj.selector, indent + 4))
                    elif isinstance(obj.selector, UnaryOp):
                        lines.append(f"{indent_str}{prefix} Selector:")
                        lines.extend(format_ast(obj.selector, indent + 4))
                else:
                    lines.append(f"{indent_str}{prefix} Value: {obj.value}")
            elif hasattr(obj, 'constant') and obj.constant:
                lines.append(f"{indent_str}{prefix} Constant: {obj.constant}")

    if isinstance(ast, InstanceBody):
        lines.append(f"{indent_str}{ast.kind} Name: {ast.name if hasattr(ast, 'name') else 'Unknown'}")
    elif hasattr(ast, 'kind'):
        lines.append(f"{indent_str}{ast.kind}")
    if isinstance(ast, Root):
        for member in ast.members:
            lines.extend(format_ast(member, indent + 2))
    elif isinstance(ast, Instance):
        lines.extend(format_ast(ast.body, indent + 2))
    elif isinstance(ast, InstanceBody):
        for member in ast.members:
            lines.extend(format_ast(member, indent + 2))
    elif isinstance(ast, PrimitiveInstance):
        for port in ast.ports:
            lines.extend(format_ast(port, indent + 2))
    elif isinstance(ast, ContinuousAssign):
        lines.extend(format_ast(ast.assignment, indent + 2))
    elif isinstance(ast, Conversion):
        lines.append(indent_str + "  Type: " + ast.type)
        lines.extend(format_ast(ast.operand, indent + 2))
    elif isinstance(ast, Assignment):
        lines.extend(format_ast(ast.left, indent + 2))
        lines.extend(format_ast(ast.right, indent + 2))
    elif isinstance(ast, BinaryOp):
        lines.append(indent_str + "    Operator: " + ast.op)
        lines.append(indent_str + "    Left Operand:")
        lines.extend(format_ast(ast.left, indent + 4))
        lines.append(indent_str + "    Right Operand:")
        lines.extend(format_ast(ast.right, indent + 4))
    elif isinstance(ast, UnaryOp):
        lines.append(indent_str + "    Operator: " + ast.op)
        lines.append(indent_str + "    Operand:")
        lines.extend(format_ast(ast.operand, indent + 4))
    elif isinstance(ast, Port):
        direction = ast.direction if hasattr(ast, 'direction') else "Unknown"
        lines.append(indent_str + f"  Port: {ast.name} Direction: {direction}")
    elif isinstance(ast, ProceduralBlock):
        lines.append(indent_str + f"  ProcedureKind: {ast.procedureKind}")
        lines.extend(format_ast(ast.body, indent + 2))
    elif isinstance(ast, Block):
        lines.append(indent_str + f"  BlockKind: {ast.blockKind}")
        lines.extend(format_ast(ast.body, indent + 2))
    elif isinstance(ast, ExpressionStatement):
        lines.extend(format_ast(ast.expr, indent + 2))
    elif isinstance(ast, list):
        for item in ast:
            lines.extend(format_ast(item, indent))
    elif isinstance(ast, Net):
        lines.append(indent_str + f"  NetType: {ast.netType.type}" + f"  Name: {ast.name}")
    elif isinstance(ast, IntegerLiteral):
        lines.append(indent_str + f"  Value: {ast.value}")
    else:
        append_info(" ", ast)
    
    return lines

##################################################################################################################################################################

