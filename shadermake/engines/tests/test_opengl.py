
from shadermake.decorator      import make_shader
from shadermake.engines.opengl import OpenGLEngine, ShaderOptions, vec2, vec3, vec4

def test_simple_function():
    @make_shader(OpenGLEngine)
    def main():
        pass
    
    assert main.c_code() == "\nint main () {\n\treturn 0;\n}"

def test_simple_arithmetic():
    @make_shader(OpenGLEngine)
    def main():
        x = 0
        y = 1
        z = 2.0

        w = x + y
        w = x - y
        w = x * y
        w = x / y
        W = x + z
        W = x - z
        W = x * z
        W = x / z
    assert main.c_code() == "\n\t".join([
        "\nint main () {",
        "int x = 0;",
        "int y = 1;",
        "float z = 2.0;",
        "int w = x + y;",
        "w = x - y;",
        "w = x * y;",
        "w = x / y;",
        "float W = x + z;",
        "W = x - z;",
        "W = x * z;",
        "W = x / z;",
        "return 0;"
    ]) + "\n}"

def test_vector_arithmetic ():
    @make_shader(OpenGLEngine)
    def main():
        A = vec2(0, 1)
        B = vec2(1.0, 2.0)

        C = A + B
    
    assert main.c_code() == "\n\t".join([
        "\nint main () {",
        "vec2 A = vec2(0, 1);",
        "vec2 B = vec2(1.0, 2.0);",
        "vec2 C = A + B;",
        "return 0;"
    ]) + "\n}"

def test_input_arithmetic ():
    @make_shader(OpenGLEngine, argument_types=[ int, float, vec2 ])
    def main(x, y, A):
        z = x + y
        A = A + vec2(x, z)
    assert main.c_code() == "\n\t".join([
        "\nint main (int x, float y, vec2 A) {",
        "float z = x + y;",
        "A = A + vec2(x, z);",
        "return 0;"
    ]) + "\n}"

def test_options ():
    options = ShaderOptions() \
        .addInput( vec2, "A", 0 ) \
        .addInput( vec2, "B" ) \
        .addOutput( vec2, "C", 0 ) \
        .addOutput( vec2, "D" ) \
        .addUniform( vec2, "E" )
    @make_shader(OpenGLEngine, shader_options=options)
    def main():
        C = A + B
        D = C + E

    assert main.c_code() == "\n".join([
        "layout(location = 0) in vec2 A;",
        "in vec2 B;",
        "layout(location = 0) out vec2 C;",
        "out vec2 D;",
        "uniform vec2 E;"
    ])+ "\n\t".join([
        "\n\nint main () {",
        "C = A + B;",
        "D = C + E;",
        "return 0;"
    ]) + "\n}"

def test_simple_added_function ():
    @make_shader (OpenGLEngine, argument_types=[ float ])
    def f(x):
        return x + 1
    @make_shader (OpenGLEngine, bound_shaders=[ f ])
    def main():
        a = 0
        b = 1
        c = f(a + b)
    assert main.c_code() == "\n\t".join([
        "\nfloat f (float x) {",
        "return x + 1;"
    ]) + "\n}\n" + "\n\t".join([
        "int main () {",
        "int a = 0;",
        "int b = 1;",
        "float c = f(a + b);",
        "return 0;"
    ]) + "\n}"