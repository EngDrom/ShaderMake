
class AbstractEngine:
    def __init__(self):
        assert self.__class__ != AbstractEngine, "Cannot create AbstractEngine object"

    def generate (self, function):
        return None