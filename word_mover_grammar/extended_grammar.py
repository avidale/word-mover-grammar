import random


from typing import Dict, List, Tuple


class Token:
    def __init__(self, text: str, idx: int, annotations=None):
        self.text: str = text
        self.idx = idx
        self.annotations: dict = annotations or {}

    def __repr__(self):
        return '[{}]'.format(self.text)


class Symbol:
    """ The base class for Terminals and NonTerminals"""
    def __init__(self, name: str):
        self.name: str = name

    def sample(self) -> List:
        raise NotImplementedError()

    def deep_sample(self) -> List:
        raise NotImplementedError()


class NonTerminal(Symbol):
    def __init__(self, name: str):
        super(NonTerminal, self).__init__(name=name)
        self.productions: List[Production] = []

    def sample(self) -> List[Symbol]:
        # todo: use weights
        return random.choice(self.productions).rhs

    def deep_sample(self):
        # todo: restrict recursion somehow
        return [item for symbol in self.sample() for item in symbol.deep_sample()]


class Terminal(Symbol):
    def __init__(self, name: str, data):
        super(Terminal, self).__init__(name=name)
        self.data = data

    def matches(self, token: Token) -> bool:
        return self.matches_text(token.text)

    def sample(self):
        return [self]

    def deep_sample(self):
        return [self.data]

    def matches_text(self, text: str) -> bool:
        return text == self.data


class W2VTerminal(Terminal):
    # todo: handle non-terminals with same names but different matching strategies
    def __init__(self, name: str, data, model, threshold=0.5):
        super(W2VTerminal, self).__init__(name=name, data=data)
        self.model = model
        self.threshold = threshold
        self.vector = self.model(self.data)  # todo: make sure they are normalized

    def matches_text(self, text: str) -> bool:
        new_vector = self.model(text)
        dot = sum(l*r for l, r in zip(self.vector, new_vector))
        return dot >= self.threshold


class Production:
    def __init__(self, lhs: NonTerminal, rhs: Tuple[Symbol], weight: float = 1):
        self.lhs: Symbol = lhs
        self.rhs: Tuple[Symbol] = rhs
        self.weight: float = weight

    @property
    def lhs_name(self):
        return self.lhs.name

    @property
    def rhs_names(self):
        return tuple(r.name for r in self.rhs)

    @property
    def names(self):
        return self.lhs_name, self.rhs_names

    @property
    def size(self):
        return len(self.rhs)


def rules2symbols(rules, w2v=None):
    symbols: Dict[str, Symbol] = {}
    for lhs, rhs in rules:
        if lhs not in symbols:
            symbols[lhs] = NonTerminal(name=lhs)
        for symbol in rhs:
            if symbol not in symbols:
                # todo: change the way of telling non-terminals from terminals
                if symbol.isupper() or symbol.startswith('$'):
                    symbols[symbol] = NonTerminal(name=symbol)
                else:
                    if w2v:
                        symbols[symbol] = W2VTerminal(name=symbol, data=symbol, model=w2v)
                    else:
                        symbols[symbol] = Terminal(name=symbol, data=symbol)
        production = Production(lhs=symbols[lhs], rhs=tuple(symbols[s] for s in rhs))
        symbols[lhs].productions.append(production)
    return symbols
