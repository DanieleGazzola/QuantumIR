import json
from dataclasses import dataclass
from typing import List, Optional, Union, Any, Dict, Type

@dataclass
class ASTNode:
    kind: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Assignment:
    kind: str
    type: str
    left: Union['NamedValue', 'ElementSelect']
    right: Union['NamedValue', 'EmptyArgument', 'BinaryOp']
    isNonBlocking: bool
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class BinaryOp:
    kind: str
    type: str
    op: str
    left: Union['NamedValue', 'EmptyArgument', 'BinaryOp']
    right: Union['NamedValue', 'EmptyArgument', 'BinaryOp']
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class CompilationUnit:
    kind: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Connection:
    kind: str
    port: str
    expr: 'ElementSelect'
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
    operand: 'IntegerLiteral'
    constant: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class ElementSelect:
    kind: str
    type: str
    value: 'NamedValue'
    selector: 'IntegerLiteral'
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class EmptyArgument:
    kind: str
    type: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class GenerateBlock:
    kind: str
    members: List[Union['Parameter', 'Instance']]
    constructIndex: int
    isUninstantiated: bool
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class GenerateBlockArray:
    kind: str
    members: List['GenerateBlock']
    constructIndex: int
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Genvar:
    kind: str
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class Instance:
    kind: str
    body: 'InstanceBody'
    connections: List['Connection']
    name: Optional[str] = None
    addr: Optional[int] = None

@dataclass
class InstanceBody:
    kind: str
    members: List[Union['Port', 'Net', 'PrimitiveInstance', 'Variable', 'ContinuousAssign', 'Parameter', 'Genvar', 'GenerateBlockArray']]
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
class Parameter:
    kind: str
    type: str
    value: int
    isLocal: bool
    isPort: bool
    isBody: bool
    initializer: Optional['Conversion'] = None
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

##################################################################################################################################################################

def from_dict(data: Dict[str, Any]) -> ASTNode:

    if isinstance(data, list):
        return [from_dict(item) for item in data]

    if isinstance(data, dict):
        kind = data.get('kind', 'Connection') # Default kind is Connection because is the only one without it
        common_fields = {
            'name': data.get('name'),
            'kind': kind,
            'addr': data.get('addr')
        }

        if kind == 'Assignment':
            return Assignment(type=data['type'], left=from_dict(data['left']), right=from_dict(data['right']), isNonBlocking=data['isNonBlocking'], **common_fields)
        elif kind == 'BinaryOp':
            return BinaryOp(type=data['type'], op=data['op'], left=from_dict(data['left']), right=from_dict(data['right']), **common_fields)
        elif kind == 'CompilationUnit':
            return CompilationUnit(**common_fields)
        elif kind == 'Connection':
            return Connection(port=data['port'], expr=from_dict(data['expr']), **common_fields)
        elif kind == 'ContinuousAssign':
            return ContinuousAssign(assignment=from_dict(data['assignment']), **common_fields)
        elif kind == 'Conversion':
            return Conversion(type=data['type'], operand=from_dict(data['operand']), constant=data['constant'], **common_fields)
        elif kind == 'ElementSelect':
            return ElementSelect(type=data['type'], value=from_dict(data['value']), selector=from_dict(data['selector']), **common_fields)
        elif kind == 'EmptyArgument':
            return EmptyArgument(type=data['type'], **common_fields)
        elif kind == 'GenerateBlock':
            return GenerateBlock(members=from_dict(data['members']), constructIndex=data['constructIndex'], isUninstantiated=data['isUninstantiated'], **common_fields)
        elif kind == 'GenerateBlockArray':
            return GenerateBlockArray(members=from_dict(data['members']), constructIndex=data['constructIndex'], **common_fields)
        elif kind == 'Genvar':
            return Genvar(**common_fields)
        elif kind == 'Instance':
            return Instance(body=from_dict(data['body']), connections=from_dict(data['connections']), **common_fields)
        elif kind == 'InstanceBody':
            return InstanceBody(members=from_dict(data['members']), definition=data['definition'], **common_fields)
        elif kind == 'IntegerLiteral':
            return IntegerLiteral(type=data['type'], value=data['value'], constant=data['constant'], **common_fields)
        elif kind == 'NamedValue':
            return NamedValue(type=data['type'], symbol=data['symbol'], constant=data.get('constant', None), **common_fields)
        elif kind == 'Net':
            return Net(type=data['type'], netType=from_dict(data['netType']), **common_fields)
        elif kind == 'NetType':
            return NetType(kind=data['kind'], name=data['name'], addr=data['addr'], type=data['type'])
        elif kind == 'Parameter':
            if 'initializer' in data:
                initializer = from_dict(data['initializer'])
            else:
                initializer = None
            return Parameter(type=data['type'], initializer=initializer, value=data['value'], isLocal=data['isLocal'], isPort=data['isPort'], isBody=data['isBody'], **common_fields)
        elif kind == 'Port':
            return Port(type=data['type'], direction=data['direction'], internalSymbol=data['internalSymbol'], **common_fields)
        elif kind == 'PrimitiveInstance':
            return PrimitiveInstance(primitiveType=data['primitiveType'], ports=from_dict(data['ports']), **common_fields)
        elif kind == 'Root':
            return Root(members=from_dict(data['members']), **common_fields)
        elif kind == 'Variable':
            return Variable(type=data['type'], lifetime=data['lifetime'], **common_fields)
        else:
            raise ValueError(f"Unknown kind: {kind}")
    return data

##################################################################################################################################################################

def json_to_ast(json_data: str) -> ASTNode:
    data = json.loads(json_data)
    return from_dict(data)

##################################################################################################################################################################

def read_json_file(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.read()

##################################################################################################################################################################

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
            if hasattr(obj, 'constant'):
                lines.append(f"{indent_str}{prefix} Constant: {obj.constant}")
            if hasattr(obj, 'value'):
                if hasattr(obj, 'selector'):
                    lines.append(f"{indent_str}{prefix} Value: {obj.value.symbol}")
                    if isinstance(obj.selector, NamedValue):
                        lines.append(f"{indent_str}{prefix} Selector:")
                        lines.extend(format_ast(obj.selector, indent + 4))
                    elif isinstance(obj.selector, BinaryOp):
                        lines.append(f"{indent_str}{prefix} Selector:")
                        lines.extend(format_ast(obj.selector, indent + 4))
                    elif isinstance(obj.selector, IntegerLiteral):
                        lines.append(f"{indent_str}{prefix} Selector:")
                        lines.extend(format_ast(obj.selector, indent + 4))
                else:
                    lines.append(f"{indent_str}{prefix} Value: {obj.value}")

    if isinstance(ast, InstanceBody):
        lines.append(f"{indent_str}{ast.kind} Name: {ast.name if hasattr(ast, 'name') else 'Unknown'}")
    elif isinstance(ast, Parameter):
        lines.append(f"{indent_str}{ast.kind} Name: {ast.name if hasattr(ast, 'name') else 'Unknown'}")
    elif hasattr(ast, 'kind'):
        lines.append(f"{indent_str}{ast.kind}")

    if isinstance(ast, Root):
        for member in ast.members:
            lines.extend(format_ast(member, indent + 2))
    elif isinstance(ast, Instance):
        lines.extend(format_ast(ast.body, indent + 2))
        lines.append(indent_str + "Connections:")
        for connection in ast.connections:
            lines.extend(format_ast(connection, indent + 2))
    elif isinstance(ast, InstanceBody):
        for member in ast.members:
            lines.extend(format_ast(member, indent + 2))
    elif isinstance(ast, PrimitiveInstance):
        for port in ast.ports:
            lines.extend(format_ast(port, indent + 2))
    elif isinstance(ast, ContinuousAssign):
        lines.extend(format_ast(ast.assignment, indent + 2))
    elif isinstance(ast, Parameter):
        lines.extend(format_ast(ast.initializer, indent + 2))
    elif isinstance(ast, Conversion):
        lines.extend(format_ast(ast.operand, indent + 2))
    elif isinstance(ast, Assignment):
        lines.extend(format_ast(ast.left, indent + 2))
        lines.extend(format_ast(ast.right, indent + 2))
    elif isinstance(ast, BinaryOp):
        lines.append(indent_str + "  Binary Operation:")
        lines.append(indent_str + "    Operator: " + ast.op)
        lines.append(indent_str + "    Left Operand:")
        lines.extend(format_ast(ast.left, indent + 4))
        lines.append(indent_str + "    Right Operand:")
        lines.extend(format_ast(ast.right, indent + 4))
    elif isinstance(ast, EmptyArgument):
        lines.append(indent_str + "  Empty Argument")
    elif isinstance(ast, Port):
        direction = ast.direction if hasattr(ast, 'direction') else "Unknown"
        lines.append(indent_str + f"  Port: {ast.name} Direction: {direction}")
    elif isinstance(ast, GenerateBlockArray):
        for member in ast.members:
            lines.extend(format_ast(member, indent + 2))
    elif isinstance(ast, GenerateBlock):
        for member in ast.members:
            lines.extend(format_ast(member, indent + 2))
    elif isinstance(ast, Connection):
        lines.append(indent_str + f"  Port: {ast.port}")
        lines.extend(format_ast(ast.expr, indent + 2))
    else:
        append_info(" ", ast)
    
    return lines

##################################################################################################################################################################
