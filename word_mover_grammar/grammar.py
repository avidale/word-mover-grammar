import random
import re

from typing import Dict, List, Tuple


class MatchingMode:
    EXACT = 'exact'
    LEMMA = 'lemma'
    REGEX = 'regex'
    W2V = 'w2v'


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

    def compile(self, **kwargs) -> None:
        pass


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
    def __init__(self, name: str, data, threshold=0.5):
        super(W2VTerminal, self).__init__(name=name, data=data)
        self.w2v = None
        self.threshold = threshold
        self.vector = None

    def compile(self, w2v, w2v_threshold=0.5, **kwargs) -> None:
        if not w2v:
            raise ValueError('W2V Terminal need to be compiled with `w2v` argument')
        if w2v_threshold is not None:
            self.threshold = w2v_threshold
        self.w2v = w2v
        self.vector = w2v(self.data)

    def matches_text(self, text: str) -> bool:
        if not self.w2v:
            raise ValueError('W2V Terminal not compiled')
        new_vector = self.w2v(text)
        dot = sum(l*r for l, r in zip(self.vector, new_vector))
        return dot >= self.threshold


class LemmaTerminal(Terminal):
    # todo: handle non-terminals with same names but different matching strategies
    def __init__(self, name: str, data, lemmas=None):
        super(LemmaTerminal, self).__init__(name=name, data=data)
        self.lemmer = None
        self.lemmas = lemmas

    def compile(self, lemmer, **kwargs) -> None:
        if not lemmer:
            raise ValueError('Lemma Terminal need to be compiled with `lemmer` argument')
        self.lemmer = lemmer
        self.lemmas = set(self.lemmer(self.data))

    def matches_text(self, text: str) -> bool:
        if not self.lemmer:
            raise ValueError('Lemma Terminal not compiled')
        new_lemmas = set(self.lemmer(text))
        return bool(new_lemmas.intersection(self.lemmas))


class RegexTerminal(Terminal):
    # todo: handle non-terminals with same names but different matching strategies
    def __init__(self, name: str, data):
        super(RegexTerminal, self).__init__(name=name, data=data)
        self.regex = re.compile('^{}$'.format(self.data))

    def matches_text(self, text: str) -> bool:
        return bool(self.regex.match(text))


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

    def __repr__(self):
        return 'Production({}->{})'.format(self.lhs_name, ' '.join(self.rhs_names))


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
