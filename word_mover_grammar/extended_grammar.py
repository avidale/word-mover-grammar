import random


from typing import List, Tuple


class Token:
    def __init__(self, text: str, idx: int, annotations=None):
        self.text: str = text
        self.idx = idx
        self.annotations: dict = annotations or {}

    def __repr__(self):
        return '[{}]'.format(self.text)


class Symbol:
    """ The base class for Terminals and NonTerminals"""
    def sample(self) -> List:
        raise NotImplementedError()

    def deep_sample(self) -> List:
        raise NotImplementedError()


class NonTerminal(Symbol):
    def __init__(self, name: str):
        self.name: str = name
        self.productions: List[Production] = []

    def sample(self) -> List[Symbol]:
        # todo: use weights
        return random.choice(self.productions).rhs

    def deep_sample(self):
        # todo: restrict recursion somehow
        return [item for symbol in self.sample() for item in symbol.deep_sample()]


class Terminal(Symbol):
    def __init__(self, name: str, data):
        self.name: str = name
        self.data = data

    def matches(self, token: Token) -> bool:
        return token == self.data

    def sample(self):
        return [self]

    def deep_sample(self):
        return [self.data]


class Production:
    def __init__(self, lhs: NonTerminal, rhs: Tuple[Symbol], weight: float = 1):
        self.lhs: Symbol = lhs
        self.rhs: Tuple[Symbol] = rhs
        self.weight: float = weight
