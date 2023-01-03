
from typing import List
from shadermake.engine import AbstractEngine

import dis

class _GLSL_Type:
    def __init__(self, typename):
        self.__typename = typename
        self.__operands = {}
        self.__any_oper = {}
        self.__castable = set()
    def typename(self):
        return self.__typename
    def castable (self, other_type):
        return other_type in self.__castable or other_type == self
    
    def link_operand (self, operand, type, end_type):
        if operand not in self.__operands: self.__operands[operand] = {}
        
        self.__operands[operand][type] = end_type
        return self
    def link_any (self, type, end_type):
        self.__any_oper[type] = end_type
        return self
    def link_array(self, operands, type, end_type):
        for operand in operands:
            self.link_operand(operand, type, end_type)
    def link_castable (self, type):
        self.__castable.add(type)
        return self
    def get_resulting_type (self, operand, type):
        if type in self.__any_oper:
            return self.__any_oper[type]
        assert operand in self.__operands, f"Operand {operand} cannot be used on type {self.typename()}"
        assert type in self.__operands[operand], f"Type {type.typename()} cannot be used with operand {operand} on type {self.typename()}"

        return self.__operands[operand][type]

class _GLSL_Variant:
    def __init__(self, end_type, input_types=[]):
        self.__end_type    = end_type
        self.__input_types = input_types
    def validate (self, variables):
        for (type, value), input_type in zip(variables, self.__input_types):
            if type.castable(input_type): continue
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

class _GLSL_Shader(_GLSL_Variant):
    def __init__(self, name, args, end_type, c_code, bound_shaders, python_function):
        super().__init__(end_type, list(map(lambda T: T[0], args)))
        self.__args   = args
        self.__name   = name
        self.__c_code = c_code

        self.__bound_shaders = bound_shaders

        self.__python_function = python_function
    def find_variant (self, variables):
        if self.validate(variables):
            return self
        return None
        
    def c_code(self):
        try:
            return self.__r_c_code
        except Exception: pass

        self.__r_c_code  = "\n".join([ shader.c_code() for shader in self.__bound_shaders ])
        self.__r_c_code += "\n"
        self.__r_c_code += self.__c_code
        
        return self.__r_c_code
    def name(self):
        return self.__name
    def args(self):
        return self.__args

class OpenGLEngine(AbstractEngine):
    def generate (self, function, argument_types, bound_shaders):
        for shader in bound_shaders:
            assert isinstance(shader, _GLSL_Shader)
        for idx_arg_type in range(len(argument_types)):
            if argument_types[idx_arg_type] == float:
                argument_types[idx_arg_type] = _t_float
            if argument_types[idx_arg_type] == int:
                argument_types[idx_arg_type] = _t_int
        
        argument_array = function.__code__.co_varnames[:function.__code__.co_argcount]
        assert len(argument_array) == len(argument_types), "Missing argument types in shader declaration"
        
        argument_data = [(type, name) for (type, name) in zip(argument_types, argument_array)]

        code_data = dis.Bytecode(function)
        stack     = []

        indentation = 1
        glsl_shader = []
        type_array  = { name:type for (type, name) in zip(argument_types, argument_array)}

        for code_piece in code_data:
            disassembler_name = f"compute__{code_piece.opname}"
            assert hasattr(self, disassembler_name), f"{code_piece.opname} is not implemented : {str(code_piece)}"
        
            disassembler        = getattr(self, disassembler_name)
            c_code, indentation = disassembler(stack, type_array, code_piece, indentation, bound_shaders)

            if c_code is not None:
                glsl_shader.append("\t" * indentation + c_code)
        
        if '<return>' not in type_array:
            type_array['<return>'] = int
            glsl_shader.append("\treturn 0;")
        
        function_parameters  = ", ".join([ f"{self.get_typename(type)} {name}" for (type, name) in argument_data ])
        function_declaration = f"{self.get_typename(type_array['<return>'])} {function.__name__} ({function_parameters})" + " {\n"
        function_end         = "\n}"
        
        function_c_code = (function_declaration + "\n".join(glsl_shader) + function_end)

        return _GLSL_Shader(function.__name__, argument_data, type_array['<return>'], function_c_code, bound_shaders, function)

    def get_typename (self, value_type):
        type_name = None
        if isinstance(value_type, _GLSL_Type):
            type_name = value_type.typename()

        assert type_name is not None, f"{value_type} type is not implemented in type conversion"

        return type_name

    def compute__LOAD_CONST (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        if isinstance(operation.argval, float): stack.append((_t_float, operation.argval))
        elif isinstance(operation.argval, int): stack.append((_t_int, operation.argval))
        else: assert False, "Only integers and floats are implemented in LOAD_CONST"

        return None, indentation
    def compute__STORE_FAST (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        value_type, value = stack.pop()

        if operation.argval in type_array:
            return f"{operation.argval} = {value};", indentation

        type_name = self.get_typename(value_type)
        type_array[operation.argval] = value_type

        return f"{type_name} {operation.argval} = {value};", indentation
    def compute__LOAD_FAST (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        assert operation.argval in type_array, f"Could not compute {operation.argval} type"
        stack.append((type_array[operation.argval], operation.argval))

        return None, indentation
    def compute__LOAD_GLOBAL(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        for bound_shader in bound_shaders:
            if bound_shader.name() == operation.argval:
                stack.append(("function", bound_shader))
                return None, indentation

        assert operation.argval in GLSL_Authorized_Functions, f"Could not find {operation.argval} in authorized GLSL functions"
        stack.append(("function", GLSL_Authorized_Functions[operation.argval]))

        return None, indentation
    
    def compute__BINARY_OPERAND (self, stack, operand):
        (type_b, b), (type_a, a) = stack.pop(), stack.pop()
        type_c = type_a.get_resulting_type(operand, type_b)
        
        assert type_c is not None, f"combination of types {type_a} and {type_b} did not work"
        
        stack.append((type_c, f"{a} {operand} {b}"))

    def compute__BINARY_ADD (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        self.compute__BINARY_OPERAND(stack, "+")

        return None, indentation
    def compute__BINARY_SUBTRACT (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        self.compute__BINARY_OPERAND(stack, "-")
        
        return None, indentation
    def compute__BINARY_MULTIPLY (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        self.compute__BINARY_OPERAND(stack, "*")
        
        return None, indentation
    def compute__BINARY_TRUE_DIVIDE (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        self.compute__BINARY_OPERAND(stack, "/")
        
        return None, indentation

    def compute__RETURN_VALUE (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
        type_name, value = int, 0
        if len(stack) == 1: type_name, value = stack.pop()

        if '<return>' in type_array:
            assert type_name == type_array['<return>'], "Return type can only be unique"
        else: type_array['<return>'] = type_name
        
        return f"return {value};", indentation
    def compute__CALL_FUNCTION (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders):
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

_t_int   = _GLSL_Type("int")
_t_float = _GLSL_Type("float")

_t_int  .link_array( [ '+', '-', '*', '/' ], _t_int,   _t_int )
_t_int  .link_array( [ '+', '-', '*', '/' ], _t_float, _t_float )
_t_float.link_array( [ '+', '-', '*', '/' ], _t_int,   _t_float )
_t_float.link_array( [ '+', '-', '*', '/' ], _t_float, _t_float )

_t_int.link_castable(_t_float)
_t_float.link_castable(_t_int)

_t_vec2.link_array( [ '+', '-' ], _t_vec2, _t_vec2 )
_t_vec3.link_array( [ '+', '-' ], _t_vec3, _t_vec3 )
_t_vec4.link_array( [ '+', '-' ], _t_vec4, _t_vec4 )

vec2 = _GLSL_Pure_Function( "vec2" ) \
    .link_variant( _GLSL_Variant( _t_vec2, [ _t_float, _t_float ] ) )
vec3 = _GLSL_Pure_Function( "vec3" ) \
    .link_variant( _GLSL_Variant( _t_vec3, [ _t_float, _t_float, _t_float ] ) )
vec4 = _GLSL_Pure_Function( "vec4" ) \
    .link_variant( _GLSL_Variant( _t_vec4, [ _t_float, _t_float, _t_float, _t_float ] ) )

GLSL_Authorized_Functions = {
    "vec2": vec2,
    "vec3": vec3,
    "vec4": vec4
}
