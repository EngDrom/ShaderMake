
# shader-make

Drom project to make shader translator. shader-make currently only works with GLSL. It uses a decorator to transform itself into a GPU based function, here for OpenGL. You cannot currently reuse a shader function as a default function but we prepared the setup to do that. We haven't implemented every python feature that we don't think are usefull for the purpose of what we will be using it for, such as while loops that could be interesting.

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

# Linking multiple functions

We will admit you have a cool python function called magic that you would like to use in multiple shader functions. You can do that using the parameter bound_shaders. For this example we will use the cool function f(x) = x + 1 and add it to our transform function :

```python
from shadermake.decorator import make_shader
from shadermake.engines.opengl import OpenGLEngine, vec3

@make_shader(OpenGLEngine, argument_types=[ float ])
def f(x):
    return x + 1

@make_shader(OpenGLEngine, argument_types=[ float, float ], bound_shaders=[ f ])
def transform(x, y):
    y = f(y)
    return vec3(x, y, x + y)
```

```c
float f (float x) {
        return x + 1;
}
vec3 transform (float x, float y) {
        y = f(y);
        return vec3(x, y, x + y);
}
```

# Inputs, outputs and uniforms

When you want to compile a shader, it can be needed to import existing inputs, setup outputs or use uniform variables shared between every vertex. For this you can use a ShaderOptions element and use addInput, addOutput and addUniform to append metadata. You can also generate the default vertex shader data or fragment shader data using the useVertex or useFragment functions. The following example generates a function with an uniform displacement :

```python
from shadermake.decorator import make_shader
from shadermake.engines.opengl import OpenGLEngine, ShaderOptions, vec2, vec3, vec4

options = ShaderOptions() \
    .useVertex() \
    .addInput( vec4, "pos", 0 ) \
    .addUniform( vec4, "delta" )
@make_shader(OpenGLEngine, shader_options=options)
def shader():
    gl_Position = pos + delta
```

```c
layout(location = 0) in vec4 pos;
uniform vec4 delta;

int shader () {
        gl_Position = pos + delta;
        return 0;
}
```

# If statements

The usage of if statement is implemented by default but the usage of elif strongly increments the C final code size. Here is the example of the shader used in the testing and one of the following results (the one on the github actions architecture) :

```python
@make_shader(OpenGLEngine)
def main():
    x = 0
    y = 1
    z = x + y
    if z > 0.5:
        y = 2
    elif z >= 1:
        y = 4
    else:
        y = 3
    u= 0
    if u + z > 0.2:
        a = u - z
    else: a = u + y
```

```c
int main () {
    int x = 0;
    int y = 1;
    int z = x + y;
    if (z > 0.5) {
        y = 2;
    } else {
        if (z >= 1) {
            y = 4;
        } else {
            y = 3;
        }
    }
    int u = 0;
    if (u + z > 0.2) {
        int a = u - z;
    } else {
        int a = u + y;
    }
    return 0;
}
```

As you can see here, the a variable is only created in the if scope. This isn't the default behavior of python so you might have to create your variable and initialize it before the if statement with a placeholder value like 0 to avoid your data being destroyed.
