
from shadermake.engine         import AbstractEngine
from shadermake.engines.opengl import OpenGLEngine

def make_shader(engine):
    manager = engine()

    def wrapper(function):
        return function
    
    return wrapper
