
from typing import List, Tuple, Any

from shadermake.engine         import AbstractEngine
from shadermake.engines.opengl import OpenGLEngine, ShaderOptions

from shadermake.engines.opengl import vec2, vec3, vec4

def make_shader_function(engine):
    manager = engine()

    def wrapper(function):
        return function

    return wrapper
def make_shader(engine, argument_types=[], bound_shaders=[], *args, **kwargs):
    manager: AbstractEngine = engine()

    def wrapper(function):
        shader = manager.generate(function, argument_types, bound_shaders, *args, **kwargs)

        return shader
    
    return wrapper

@make_shader(OpenGLEngine, argument_types=[ float ])
def custom_f(x):
    return x + 1

main_shader_options = ShaderOptions() \
    .addInput( vec3, "inPos", 0 ) \
    .addUniform( vec3, "deltaPos" ) \
    .useVertex()
@make_shader(OpenGLEngine, bound_shaders=[custom_f], shader_options=main_shader_options)
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

    gl_Position = vec4(x, y, z, w)

    return 0
print(main_shader.c_code())