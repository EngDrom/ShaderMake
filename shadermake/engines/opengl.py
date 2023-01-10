
from typing import List
from shadermake.engine import AbstractEngine

import dis

class ShaderOptions:
    def __init__(self):
        self.__inputs  = []
        self.__outputs = []
        self.__uniform = []

        self.__type = None
    
    def useVertex(self):
        self.__type = "vertex"
        return self
    def useFragment(self):
        self.__type = "fragment"
        return self
    def inputs (self): return self.__inputs
    def outputs(self): return self.__outputs
    def uniform(self): return self.__uniform
    def allVars(self):
        if self.__type == "vertex":
            return self.inputs() + self.outputs() + self.uniform() + [ (_t_vec4, "gl_Position"), (_t_float, "gl_PointSize") ]
        if self.__type == "fragment":
            return self.inputs() + self.outputs() + self.uniform()
        return self.inputs() + self.outputs() + self.uniform()

    def addInput (self, type, name, location=None):
        type = transform_native_type(type)
        self.__inputs.append((type, name, location))
        return self
    def addOutput(self, type, name, location=None):
        type = transform_native_type(type)
        self.__outputs.append((type, name, location))
        return self
    def addUniform(self, type, name):
        type = transform_native_type(type)
        self.__uniform.append((type, name))
        return self


class _GLSL_Type:
    def __init__(self, typename):
        self.__typename = typename
        self.__operands = {}
        self.__any_oper = {}
        self.__castable = set()
        self.__attributes = {}
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
    def link_attribute (self, name, type):
        self.__attributes[name] = type
        return self
    def link_attribute_array (self, names, type):
        for name in names:
            self.link_attribute(name, type)
        return self
    def get_attribute_type (self, name):
        return self.__attributes[name]
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
        return f"({', '.join(map(str, arr))})"

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
    def __init__(self, name, args, end_type, c_code, bound_shaders, python_function, shader_options: ShaderOptions):
        super().__init__(end_type, list(map(lambda T: T[0], args)))
        self.__args   = args
        self.__name   = name
        self.__c_code = c_code

        self.__bound_shaders = bound_shaders

        self.__python_function = python_function
        self.shader_options    = shader_options
    def find_variant (self, variables):
        if self.validate(variables):
            return self
        return None
        
    def c_code(self):
        try:
            return self.__r_c_code
        except Exception: pass

        self.__r_c_code = ""

        for (type, name, *args) in self.shader_options.inputs():
            if len(args) == 0 or args[0] is None:
                self.__r_c_code += f"in {type.typename()} {name};\n"
            else:
                location = args[0]
                self.__r_c_code += f"layout(location = {location}) in {type.typename()} {name};\n"
        for (type, name, *args) in self.shader_options.outputs():
            if len(args) == 0 or args[0] is None:
                self.__r_c_code += f"out {type.typename()} {name};\n"
            else:
                location = args[0]
                self.__r_c_code += f"layout(location = {location}) out {type.typename()} {name};\n"
        for (type, name) in self.shader_options.uniform():
            self.__r_c_code += f"uniform {type.typename()} {name};\n"

        self.__r_c_code += "\n".join([ shader.c_code() for shader in self.__bound_shaders ])
        self.__r_c_code += "\n"
        self.__r_c_code += self.__c_code
        
        return self.__r_c_code
    def name(self):
        return self.__name
    def args(self):
        return self.__args

class OpenGLEngine(AbstractEngine):
    def generate (self, function, argument_types, bound_shaders, shader_options=ShaderOptions()):
        for shader in bound_shaders:
            assert isinstance(shader, _GLSL_Shader)
        for idx_arg_type in range(len(argument_types)):
            argument_types[idx_arg_type] = transform_native_type(argument_types[idx_arg_type])
        
        argument_array = function.__code__.co_varnames[:function.__code__.co_argcount]
        assert len(argument_array) == len(argument_types), "Missing argument types in shader declaration"
        
        argument_data = [(type, name) for (type, name) in zip(argument_types, argument_array)]

        code_data = dis.Bytecode(function)
        stack     = []

        indentation = 1
        glsl_shader = []
        type_array  = { name:type for (type, name) in zip(argument_types, argument_array)}

        for (type, name, *args) in shader_options.allVars():
            type_array[name] = type

        user_code   = list(code_data)
        glsl_shader = self.generate_c_code( 0, len( user_code ), stack, type_array, 1, bound_shaders, user_code )
        
        if '<return>' not in type_array:
            type_array['<return>'] = _t_void
        
        function_parameters  = ", ".join([ f"{self.get_typename(type)} {name}" for (type, name) in argument_data ])
        function_declaration = f"{self.get_typename(type_array['<return>'])} {function.__name__} ({function_parameters})" + " {\n"
        function_end         = "\n}"
        
        function_c_code = (function_declaration + "\n".join(glsl_shader) + function_end)

        return _GLSL_Shader(function.__name__, argument_data, type_array['<return>'], function_c_code, bound_shaders, function, shader_options)

    def generate_c_code (self, start, end, stack: List, type_array, indentation: int, bound_shaders, function_code):
        glsl_shader = []

        code_piece_id = start
        while code_piece_id < end:
            code_piece = function_code[code_piece_id]
            disassembler_name = f"compute__{code_piece.opname}"
            assert hasattr(self, disassembler_name), f"{code_piece.opname} is not implemented : {str(code_piece)}"
        
            disassembler                 = getattr(self, disassembler_name)
            c_code, n_indentation, delta = disassembler(stack, type_array, code_piece, indentation, bound_shaders, function_code)

            if hasattr(code_piece, "appended_blocks"):
                delta_indentation = 0
                for appended_block, end_indentation, local_indetation in code_piece.appended_blocks:
                    delta_indentation = end_indentation - indentation
                    
                    glsl_shader.append("\t" * local_indetation + appended_block)
                n_indentation += delta_indentation
                indentation += delta_indentation

            if c_code is not None:
                glsl_shader.append("\t" * indentation + c_code)

            code_piece_id += 1 + delta
            indentation    = n_indentation
        
        return glsl_shader

    def find_lca (self, user_code, a, b):
        while a != b:
            if a > b: a, b = b, a

            next_a = a + 1
            if user_code[a].opname == "JUMP_FORWARD":
                next_a = self.binary_search(user_code, user_code[a].argval)
            
            a = next_a
        
        return a
    def get_typename (self, value_type):
        type_name = None
        if isinstance(value_type, _GLSL_Type):
            type_name = value_type.typename()

        assert type_name is not None, f"{value_type} type is not implemented in type conversion"

        return type_name
    
    def binary_search(self, function_code, offset):
        a = 0
        b = len(function_code)

        while b - a > 1:
            c = (a + b) >> 1

            if function_code[c].offset <= offset: a = c
            else: b = c
        
        return a

    # Python no-op so nothing happens
    def compute__RESUME(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        return None, indentation, 0
    def compute__PRECALL(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        return None, indentation, 0
    def compute__COPY_FREE_VARS(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        return None, indentation, 0
    def compute__PUSH_NULL(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        return None, indentation, 0
    def compute__JUMP_FORWARD(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        return None, indentation, self.binary_search(function_code, operation.argval) - self.binary_search(function_code, operation.offset) - 1
    def compute__POP_JUMP_FORWARD_IF_FALSE(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        return self.compute__POP_JUMP_IF_FALSE(stack, type_array, operation, indentation, bound_shaders, function_code)
    def compute__POP_JUMP_IF_FALSE(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        main_branch = self.binary_search(function_code, operation.offset) + 1
        altr_branch = self.binary_search(function_code, operation.argval)

        condition_type, condition_expr = stack.pop()
        assert condition_type.castable(_t_bool), "Only a boolean can be used in an if statement"

        end_branch = self.find_lca(function_code, main_branch, altr_branch)

        if not hasattr ( function_code[end_branch], "appended_blocks" ):
            function_code[end_branch].appended_blocks = []

        function_code[end_branch].appended_blocks.insert( 0, ("}", indentation, indentation) )
        if end_branch != altr_branch:
            shader_inner_code = self.generate_c_code(altr_branch, end_branch, stack, { k:type_array[k] for k in type_array.keys() }, indentation + 1, bound_shaders, function_code)
            
            function_code[end_branch].appended_blocks.insert( 0, ("\n".join(shader_inner_code), indentation, 0) )
            function_code[end_branch].appended_blocks.insert( 0, ("} else {", indentation, indentation) )

            pass
        
        return "if (" + str(condition_expr) + ") {\n" \
            + "\n".join(self.generate_c_code(main_branch, end_branch, stack, { k:type_array[k] for k in type_array.keys() }, indentation + 1, bound_shaders, function_code)), \
            indentation, end_branch - self.binary_search(function_code, operation.offset) - 1

    def compute__LOAD_CONST (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        if isinstance(operation.argval, float): stack.append((_t_float, operation.argval))
        elif isinstance(operation.argval, int): stack.append((_t_int, operation.argval))
        elif operation.argval is None: stack.append((_t_NoneType, None))
        else: assert False, f"Only integers and floats are implemented in LOAD_CONST : {operation.argval}"

        return None, indentation, 0
    def compute__STORE_FAST (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        value_type, value = stack.pop()

        assert value_type != _t_NoneType, "Cannot store none type"

        if operation.argval in type_array:
            return f"{operation.argval} = {value};", indentation, 0

        type_name = self.get_typename(value_type)
        type_array[operation.argval] = value_type

        return f"{type_name} {operation.argval} = {value};", indentation, 0
    def compute__LOAD_FAST (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        assert operation.argval in type_array, f"Could not compute {operation.argval} type"
        stack.append((type_array[operation.argval], operation.argval))

        return None, indentation, 0
    def compute__LOAD_GLOBAL(self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        if operation.argval in type_array:
            stack.append((type_array[operation.argval], operation.argval))

            return None, indentation, 0
        for bound_shader in bound_shaders:
            if bound_shader.name() == operation.argval:
                stack.append(("function", bound_shader))
                return None, indentation, 0

        assert operation.argval in GLSL_Authorized_Functions, f"Could not find {operation.argval} in authorized GLSL functions"
        stack.append(("function", GLSL_Authorized_Functions[operation.argval]))

        return None, indentation, 0
    def compute__LOAD_DEREF(self, *args, **kwargs):
        return self.compute__LOAD_GLOBAL(*args, **kwargs)
    def compute__LOAD_ATTR (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        value_type, value = stack.pop()

        next_type = value_type.get_attribute_type(operation.argval)

        stack.append( (next_type, f"{str(value)}.{operation.argval}") )

        return None, indentation, 0

    def compute__BINARY_OPERAND (self, stack, operand):
        (type_b, b), (type_a, a) = stack.pop(), stack.pop()
        type_c = type_a.get_resulting_type(operand, type_b)
        
        assert type_c is not None, f"combination of types {type_a} and {type_b} did not work"
        
        stack.append((type_c, f"{a} {operand} {b}"))
    
    def compute__BINARY_OP (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        self.compute__BINARY_OPERAND(stack, operation.argrepr)

        return None, indentation, 0
    def compute__COMPARE_OP (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        self.compute__BINARY_OPERAND(stack, operation.argrepr)

        return None, indentation, 0
    def compute__BINARY_ADD (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        self.compute__BINARY_OPERAND(stack, "+")

        return None, indentation, 0
    def compute__BINARY_SUBTRACT (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        self.compute__BINARY_OPERAND(stack, "-")
        
        return None, indentation, 0
    def compute__BINARY_MULTIPLY (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        self.compute__BINARY_OPERAND(stack, "*")
        
        return None, indentation, 0
    def compute__BINARY_TRUE_DIVIDE (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        self.compute__BINARY_OPERAND(stack, "/")
        
        return None, indentation, 0

    def compute__RETURN_VALUE (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        type_name, value = _t_int, 0
        if len(stack) == 1: type_name, value = stack.pop()

        if type_name == _t_NoneType:
            type_name, value = _t_void, 0

        if '<return>' in type_array:
            assert type_name == type_array['<return>'], "Return type can only be unique"
        else: type_array['<return>'] = type_name
        
        if type_name == _t_void:
            return None, indentation, 0
        return f"return {value};", indentation, 0
    
    def make_call(self, args, func, stack: List, indentation: int):
        assert func[0] == 'function', "The function called should be a function"

        func: _GLSL_Pure_Function = func[1]
        variant: _GLSL_Variant    = func.find_variant(args)
        
        return_type = variant.end_type()
        parameters  = variant.make (args)
        func_call   = f"{func.name()}{parameters}"

        stack.append((return_type, func_call))

        return None, indentation, 0
    def compute__CALL_FUNCTION (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        args = stack[- operation.argval:]
        func = stack[- operation.argval - 1]
        for _ in range(operation.argval + 1): stack.pop()

        return self.make_call(args, func, stack, indentation)
    def compute__CALL (self, stack: List, type_array, operation: dis.Instruction, indentation: int, bound_shaders, function_code):
        args = stack[- operation.argval:]
        func = stack[- operation.argval - 1]
        for _ in range(operation.argval + 1): stack.pop()

        return self.make_call(args, func, stack, indentation)

COMPARABLE = ['>', '>=', '<', '<=', '==', '!=']

_t_NoneType = _GLSL_Type("0")

_t_vec2 = _GLSL_Type("vec2")
_t_vec3 = _GLSL_Type("vec3")
_t_vec4 = _GLSL_Type("vec4")

_t_mat4 = _GLSL_Type("mat4")

_t_int   = _GLSL_Type("int")
_t_float = _GLSL_Type("float")
_t_bool  = _GLSL_Type("bool")

_t_void = _GLSL_Type("void")

_t_int  .link_array( [ '+', '-', '*', '/' ], _t_int,   _t_int )
_t_int  .link_array( [ '+', '-', '*', '/' ], _t_float, _t_float )
_t_int  .link_array( COMPARABLE, _t_int,   _t_bool )
_t_int  .link_array( COMPARABLE, _t_float, _t_bool )
_t_float.link_array( [ '+', '-', '*', '/' ], _t_int,   _t_float )
_t_float.link_array( [ '+', '-', '*', '/' ], _t_float, _t_float )
_t_float.link_array( COMPARABLE, _t_int,   _t_bool )
_t_float.link_array( COMPARABLE, _t_float, _t_bool )

_t_int.link_castable(_t_float)
_t_float.link_castable(_t_int)

_t_vec2.link_array( [ '+', '-' ], _t_vec2, _t_vec2 )
_t_vec3.link_array( [ '+', '-' ], _t_vec3, _t_vec3 )
_t_vec4.link_array( [ '+', '-' ], _t_vec4, _t_vec4 )

_t_vec2.link_attribute_array( [ 'x', 'y' ], _t_float )
_t_vec3.link_attribute_array( [ 'x', 'y', 'z' ], _t_float )
_t_vec4.link_attribute_array( [ 'x', 'y', 'z', 'w' ], _t_float )

_t_mat4.link_array( [ '*' ], _t_vec4, _t_vec4 )
_t_mat4.link_array( [ '+', '-', '*' ], _t_mat4, _t_mat4 )

vec2 = _GLSL_Pure_Function( "vec2" ) \
    .link_variant( _GLSL_Variant( _t_vec2, [ _t_float, _t_float ] ) )
vec3 = _GLSL_Pure_Function( "vec3" ) \
    .link_variant( _GLSL_Variant( _t_vec3, [ _t_float, _t_float, _t_float ] ) )
vec4 = _GLSL_Pure_Function( "vec4" ) \
    .link_variant( _GLSL_Variant( _t_vec4, [ _t_float, _t_float, _t_float, _t_float ] ) )

mat4 = _t_mat4

def transform_native_type (type):
    if type == float:
        type = _t_float
    if type == int:
        type = _t_int
    if type == vec2: type = _t_vec2
    if type == vec3: type = _t_vec3
    if type == vec4: type = _t_vec4
    return type

GLSL_Authorized_Functions = {
    "vec2": vec2,
    "vec3": vec3,
    "vec4": vec4
}
