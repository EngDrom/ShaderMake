
from typing import List, Tuple, Any

from shadermake.engine         import AbstractEngine
from shadermake.engines.opengl import OpenGLEngine

from shadermake.engines.opengl import vec2

def make_shader_function(engine):
    manager = engine()

    def wrapper(function):
        return function

    return wrapper
def make_shader(engine, inputs: List[Tuple[str, Any]]=[]):
    manager: AbstractEngine = engine()

    def wrapper(function):
        shader = manager.generate(function)
        print(shader.c_code())
        return function
    
    return wrapper

@make_shader(OpenGLEngine)
def main_shader():
    x = 1.0
    y = 2
    z = x + y
    z = x - y
    w = x * y
    w = x / y

    V = vec2(x, y)
    W = vec2(z, w)

    U = V + W

    return 0
