
from shadermake.decorator      import make_shader
from shadermake.engines.opengl import OpenGLEngine, ShaderOptions, vec2, vec3, vec4, mat4

def test_simple_function():
    @make_shader(OpenGLEngine)
    def main():
        pass
    
    assert main.c_code() == "\nvoid main () {\n\n}"

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
        "\nvoid main () {",
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
        "W = x / z;"
    ]) + "\n}"

def test_vector_arithmetic ():
    @make_shader(OpenGLEngine)
    def main():
        A = vec2(0, 1)
        B = vec2(1.0, 2.0)

        C = A + B
    
    assert main.c_code() == "\n\t".join([
        "\nvoid main () {",
        "vec2 A = vec2(0, 1);",
        "vec2 B = vec2(1.0, 2.0);",
        "vec2 C = A + B;"
    ]) + "\n}"

def test_input_arithmetic ():
    @make_shader(OpenGLEngine, argument_types=[ int, float, vec2 ])
    def main(x, y, A):
        z = x + y
        A = A + vec2(x, z)
    assert main.c_code() == "\n\t".join([
        "\nvoid main (int x, float y, vec2 A) {",
        "float z = x + y;",
        "A = A + vec2(x, z);"
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
        "\n\nvoid main () {",
        "C = A + B;",
        "D = C + E;"
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
        "void main () {",
        "int a = 0;",
        "int b = 1;",
        "float c = f(a + b);"
    ]) + "\n}"

def test_matrix_multiplication ():
    options = ShaderOptions() \
        .addInput( vec4, "position", 0 ) \
        .addUniform( mat4, "matProj" ) \
        .addUniform( mat4, "matModel" ) \
        .addUniform( mat4, "matView" )
    @make_shader(OpenGLEngine, shader_options=options)
    def main():
        L = matProj * position
        M = matProj * matModel * matView
        R = M * position
        U = matProj * matModel * matView * position

        gl_Position = U
    
    assert main.c_code() == "\n".join([
        "layout(location = 0) in vec4 position;",
        "uniform mat4 matProj;",
        "uniform mat4 matModel;",
        "uniform mat4 matView;",
        "",
        "void main () {",
        "\tvec4 L = matProj * position;",
        "\tmat4 M = matProj * matModel * matView;",
        "\tvec4 R = M * position;",
        "\tvec4 U = matProj * matModel * matView * position;",
        "\tvec4 gl_Position = U;",
        "}"
    ])

EXPECTED_IF_STATEMENT_RESULT = [ """
void main () {
\tint x = 0;
\tint y = 1;
\tint z = x + y;
\tif (z > 0.5) {
\t\ty = 2;
\t} else {
\t\tif (z >= 1) {
\t\t\ty = 4;
\t\t} else {
\t\t\ty = 3;
\t\t}
\t}
\tint u = 0;
\tif (u + z > 0.2) {
\t\tint a = u - z;
\t}
\tint a = u + y;
}""", """
void main () {
\tint x = 0;
\tint y = 1;
\tint z = x + y;
\tif (z > 0.5) {
\t\ty = 2;
\t} else {
\t\tif (z >= 1) {
\t\t\ty = 4;
\t\t} else {
\t\t\ty = 3;
\t\t}
\t}
\tint u = 0;
\tif (u + z > 0.2) {
\t\tint a = u - z;
\t} else {
\t\tint a = u + y;
\t}
}"""]
def test_if_statement ():
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
    
    print(main.c_code())
    assert main.c_code() in EXPECTED_IF_STATEMENT_RESULT
