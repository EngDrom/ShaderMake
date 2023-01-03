
# shader-make

Drom licensed project to make universal shader translator. shader-make currently only works in Python. It uses a decorator to transform itself into a GPU based function.

# Compiling a simple function to shader code

First you will need to import the decorator and the shader engine you want to use. We currently only support OpenGL with GLSL support. shader-make will then do type analysis on the variables to generate C code that you can compile to GLSL (you have to specify the type of your input for it to work). Here is a simple GLSL function that takes two coordinates a and b and creates a vec3 with (x, y, x + y) :

```python
from shadermake.decorator import make_shader
from shadermake.engines.opengl import OpenGLEngine, vec3

@make_shader(OpenGLEngine, argument_types=[ float, float ])
def transform(x, y):
    return vec3(x, y, x + y)
```

And the resulting C code is the following when you do transform.c_code():

```c
vec3 transform (float x, float y) {
        return vec3(x, y, x + y);
}
```
