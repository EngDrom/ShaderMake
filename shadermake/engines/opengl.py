
from typing import List
from shadermake.engine import AbstractEngine

import dis

class _GLSL_Type:
    def __init__(self, typename):
        self.__typename = typename
    def typename(self):
        return self.__typename

class _GLSL_Variant:
    def __init__(self, end_type, input_types=[]):
        self.__end_type    = end_type
        self.__input_types = input_types
    def validate (self, variables):
        for (type, value), input_type in zip(variables, self.__input_types):
            if type == input_type: continue
            if type == int and input_type == float: continue

            return False
        
        return True
    def end_type(self): return self.__end_type
    def make (self, args):
        arr = []
        for typename, arg in args:
            arr.append(arg)
        return f"({', '.join(arr)})"

class _GLSL_Pure_Function:
    def __init__(self, name):
        self.__name     = name
        self.__variants = []
    def name (self):
        return self.__name
    def find_variant(self, variables):
        for variant in self.__variants:
            if variant.validate(variables):
                return variant
        
        return None
    def link_variant (self, variant):
        self.__variants.append(variant)
        return self

class _GLSL_Shader:
    def __init__(self, c_code):
        self.__c_code = c_code
    def c_code(self):
        return self.__c_code

class OpenGLEngine(AbstractEngine):
    def generate (self, function):
        code_data = dis.Bytecode(function)
        stack     = []

        indentation = 1
        glsl_shader = []
        type_array  = {}

        for code_piece in code_data:
            disassembler_name = f"compute__{code_piece.opname}"
            assert hasattr(self, disassembler_name), f"{code_piece.opname} is not implemented : {str(code_piece)}"
        
            disassembler        = getattr(self, disassembler_name)
            c_code, indentation = disassembler(stack, type_array, code_piece, indentation)

            if c_code is not None:
                glsl_shader.append("\t" * indentation + c_code)
        
        if '<return>' not in type_array:
            type_array['<return>'] = int
            glsl_shader.append("\treturn 0;")
        
        function_declaration = f"{self.get_typename(type_array['<return>'])} {function.__name__} ()" + " {\n"
        function_end         = "\n}"
        
        function_c_code = (function_declaration + "\n".join(glsl_shader) + function_end)
        
        return _GLSL_Shader(function_c_code)

    def get_typename (self, value_type):
        type_name = None
        if value_type == int:   type_name = "int"
        if value_type == float: type_name = "float"
        if isinstance(value_type, _GLSL_Type):
            type_name = value_type.typename()

        assert type_name is not None, f"{value_type} type is not implemented in type conversion"

        return type_name

    def compute__LOAD_CONST (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        if isinstance(operation.argval, float): stack.append((float, operation.argval))
        elif isinstance(operation.argval, int): stack.append((int, operation.argval))
        else: assert False, "Only integers and floats are implemented in LOAD_CONST"

        return None, indentation
    def compute__STORE_FAST (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        value_type, value = stack.pop()

        if operation.argval in type_array:
            return f"{operation.argval} = {value};", indentation

        type_name = self.get_typename(value_type)
        type_array[operation.argval] = value_type

        return f"{type_name} {operation.argval} = {value};", indentation
    def compute__LOAD_FAST (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        assert operation.argval in type_array, f"Could not compute {operation.argval} type"
        stack.append((type_array[operation.argval], operation.argval))

        return None, indentation
    def compute__LOAD_GLOBAL(self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        assert operation.argval in GLSL_Authorized_Functions, f"Could not find {operation.argval} in authorized GLSL functions"
        stack.append(("function", GLSL_Authorized_Functions[operation.argval]))

        return None, indentation
    
    def compute__BINARY_OPERAND (self, stack, operand):
        (type_a, a), (type_b, b) = stack.pop(), stack.pop()
        
        type_c = None
        if   type_a == type_b: type_c = type_a
        elif type_a == int and type_b == float: type_c = float
        elif type_b == int and type_a == float: type_c = float
        
        assert type_c is not None, f"combination of types {type_a} and {type_b} did not work"
        
        stack.append((type_c, f"{a} {operand} {b}"))

    def compute__BINARY_ADD (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        self.compute__BINARY_OPERAND(stack, "+")

        return None, indentation
    def compute__BINARY_SUBTRACT (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        self.compute__BINARY_OPERAND(stack, "-")
        
        return None, indentation
    def compute__BINARY_MULTIPLY (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        self.compute__BINARY_OPERAND(stack, "*")
        
        return None, indentation
    def compute__BINARY_TRUE_DIVIDE (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        self.compute__BINARY_OPERAND(stack, "/")
        
        return None, indentation

    def compute__RETURN_VALUE (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        type_name, value = int, 0
        if len(stack) == 1: type_name, value = stack.pop()

        if '<return>' in type_array:
            assert type_name == type_array['<return>'], "Return type can only be unique"
        else: type_array['<return>'] = type_name
        
        return f"return {value};", indentation
    def compute__CALL_FUNCTION (self, stack: List, type_array, operation: dis.Instruction, indentation: int):
        args = stack[- operation.argval:]
        func = stack[- operation.argval - 1]
        for _ in range(operation.argval + 1): stack.pop()

        assert func[0] == 'function', "The function called should be a function"

        func: _GLSL_Pure_Function = func[1]
        variant: _GLSL_Variant    = func.find_variant(args)
        
        return_type = variant.end_type()
        parameters  = variant.make (args)
        func_call   = f"{func.name()}{parameters}"

        stack.append((return_type, func_call))

        return None, indentation

_t_vec2 = _GLSL_Type("vec2")
_t_vec3 = _GLSL_Type("vec3")
_t_vec4 = _GLSL_Type("vec4")

vec2 = _GLSL_Pure_Function( "vec2" ) \
    .link_variant( _GLSL_Variant( _t_vec2, [ float, float ] ) )
vec3 = _GLSL_Pure_Function( "vec3" ) \
    .link_variant( _GLSL_Variant( _t_vec3, [ float, float, float ] ) )
vec4 = _GLSL_Pure_Function( "vec4" ) \
    .link_variant( _GLSL_Variant( _t_vec4, [ float, float, float, float ] ) )

GLSL_Authorized_Functions = {
    "vec2": vec2,
    "vec3": vec3,
    "vec4": vec4
}
