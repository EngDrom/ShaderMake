
from typing import List, Tuple, Any

from shadermake.engine         import AbstractEngine
from shadermake.engines.opengl import OpenGLEngine, ShaderOptions

from shadermake.engines.opengl import vec2, vec3, vec4

def make_shader(engine, argument_types=[], bound_shaders=[], *args, **kwargs):
    manager: AbstractEngine = engine()

    def wrapper(function):
        shader = manager.generate(function, argument_types, bound_shaders, *args, **kwargs)

        return shader
    
    return wrapper