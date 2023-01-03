
from typing import List, Tuple, Any

from shadermake.engine         import AbstractEngine
from shadermake.engines.opengl import OpenGLEngine

from shadermake.engines.opengl import vec2

def make_shader_function(engine):
    manager = engine()

    def wrapper(function):
        return function

    return wrapper
def make_shader(engine, argument_types=[], bound_shaders=[]):
    manager: AbstractEngine = engine()

    def wrapper(function):
        shader = manager.generate(function, argument_types, bound_shaders)

        return shader
    
    return wrapper

@make_shader(OpenGLEngine, argument_types=[ float ])
def custom_f(x):
    return x + 1

@make_shader(OpenGLEngine, bound_shaders=[custom_f])
def main_shader():
    x = 1.0
    y = 2
    z = x + y
    z = x - y
    w = custom_f(x * y)
    w = x / y

    V = vec2(x, y)
    W = vec2(z, w)

    U = V + W

    return 0
print(main_shader.c_code())