import copy
import random

from collections import defaultdict
from typing import Dict

from word_mover_grammar.grammar import Production, Symbol, NonTerminal, Terminal


class State:
    def __init__(self, lhs, rhs, dot=0, left=0, right=0):
        self.lhs = lhs
        self.rhs = rhs
        self.dot = dot
        self.left = left
        self.right = right

    @property
    def tuple(self):
        return self.lhs, self.rhs, self.dot, self.left, self.right

    @property
    def finished(self):
        return self.dot >= len(self.rhs)

    @property
    def current_token(self):
        return None if self.finished else self.rhs[self.dot]

    @property
    def rule(self):
        return self.lhs, self.rhs

    @property
    def span(self):
        return self.left, self.right

    def advance(self):
        return State(self.lhs, self.rhs, self.dot + 1, self.left)

    def __hash__(self):
        return hash(self.tuple)

    def __repr__(self):
        return str(self.tuple)

    def __eq__(self, other):
        return self.tuple == other.tuple


class ParseResult:
    def __init__(self, tokens, forest, final_state):
        self.tokens = tokens
        self.forest = forest
        self.final_state = final_state

    @property
    def success(self):
        return self.final_state in self.forest

    def print(self, node=None, depth=0):
        """ Text representation of the forest """
        if not self.success:
            print('Empty parse result')
            return
        if node is None:
            node = self.final_state
        if node.finished:
            l = '{} {} -> {}'.format('  ' * depth, node.lhs, ' '.join(node.rhs))
            print('{:30} {}'.format(l, node.span))
        if depth > 20:
            return
        for i, pair in enumerate(self.forest[node]):
            if i > 0:
                print('  ' * (depth + 1), '____')
            for j, c in enumerate(pair):
                self.print(c, depth=depth + c.finished)

    def sample_a_tree(self, node=None, tree=None, last_parent=None):
        if not self.success:
            raise ValueError('Cannot sample trees from an empty parse result')
        if node is None:
            node = self.final_state
        if tree is None:
            tree = defaultdict(list)
        if last_parent and node.finished:
            tree[last_parent].append(node)

        # todo: somehow take into account production probabilities
        if self.forest[node]:
            pair = random.choice(list(self.forest[node]))
            for j, c in enumerate(pair):
                self.sample_a_tree(c, tree=tree, last_parent=node if node.finished else last_parent)
        return tree

    def iter_trees(self, node=None, tree=None, last_parent=None):
        """ Loop over all possible parse trees (their number might be exponential) """
        if not self.success:
            return
            yield
        if node is None:
            node = self.final_state
        if tree is None:
            tree = defaultdict(list)
        if last_parent and node.finished:
            tree[last_parent].append(node)

        children = self.forest[node]
        new_parent = node if node.finished else last_parent

        def combine(children):
            for ltree in self.iter_trees(children[0], tree=None, last_parent=new_parent):
                # todo: don't loop over and over
                for rtree in self.iter_trees(children[1], tree=None, last_parent=new_parent):
                    new_tree = copy.deepcopy(tree)
                    for k, v in ltree.items():
                        new_tree[k].extend(v)
                    for k, v in rtree.items():
                        new_tree[k].extend(v)
                    yield new_tree

        if not children:
            yield tree
        else:
            for pair in children:
                for t in combine(pair):
                    yield t

    def sample_top_trees(self):
        # todo: implement top-k (or even top-p) beam search sampling of parse trees
        raise NotImplementedError()


class EarleyParser:
    def __init__(self, symbols, root_symbol=None, w2v=None, w2v_threshold=None, lemmer=None):
        if root_symbol is None:
            for symbol in ['^', 'S', 'root']:
                if symbol in symbols:
                    root_symbol = symbol
                    break
        if not root_symbol:
            raise ValueError('Could not guess the root symbol')
        elif root_symbol not in symbols:
            raise ValueError('Root symbol {} does not belong to the grammar'.format(root_symbol))
        self.root_symbol = root_symbol
        self.symbols: Dict[str, Symbol] = symbols
        for _, symbol in self.symbols.items():
            symbol.compile(w2v=w2v, w2v_threshold=w2v_threshold, lemmer=lemmer)
        self.root = Production(NonTerminal('.'), (self.symbols[self.root_symbol], ))

    def parse(self, words, verbose=False):
        initial_state = State(*self.root.names)
        states = [set() for i in range(len(words) + 1)]
        states[0].add(initial_state)

        forest = defaultdict(set)

        for k, token in enumerate(words + ['^']):
            old_states = {s for s in states[k]}
            for i in range(1000):
                if not old_states:
                    break
                state: State = old_states.pop()
                # print(state)
                if state.finished:
                    # completer: move pointer within a parent rule if we matched a non-terminal
                    prev_state: State
                    for prev_state in states[state.left]:
                        if state.lhs == prev_state.current_token:
                            new_state = prev_state.advance()
                            new_state.right = k
                            if new_state not in states[k]:
                                states[k].add(new_state)
                                old_states.add(new_state)
                                if verbose:
                                    print('adding new state from completer', new_state)
                                # we add even non-unique children, because they belong to different parses
                            children = prev_state, state
                            forest[new_state].add(children)

                else:
                    current_symbol = self.symbols[state.current_token]
                    if isinstance(current_symbol, NonTerminal):
                        # predictor: create possible child non-terminals
                        for production in current_symbol.productions:
                            new_state = State(*production.names, 0, k)
                            new_state.right = k
                            if new_state not in states[k]:
                                if verbose:
                                    print('adding new state from predictor', new_state)
                                old_states.add(new_state)
                                states[k].add(new_state)
                    elif isinstance(current_symbol, Terminal):
                        # scanner: move pointer within the rule if we matched a terminal
                        if current_symbol.matches_text(token):
                            new_state = state.advance()
                            new_state.right = k + 1
                            if verbose:
                                print('adding new state from scanner', new_state)
                            states[k + 1].add(new_state)

                            terminal_state = State(
                                lhs=current_symbol.name,
                                rhs=(token,),
                                left=k,
                                right=k+1,
                                dot=1,
                            )
                            children = (state, terminal_state)
                            forest[new_state].add(children)
                    else:
                        raise ValueError(
                            'Current symbol must be Terminal or Nonterminal, got {} instead'.format(current_symbol)
                        )
        final_state = State(*self.root.names, self.root.size, left=0, right=len(words))
        return ParseResult(tokens=words, forest=forest, final_state=final_state)


def print_tree_vertically(tree, root: State, depth=0):
    l = '{} {} -> {}'.format('  ' * depth, root.lhs, ' '.join(root.rhs))
    print('{:30} {}'.format(l, root.span))
    for child in tree[root]:
        print_tree_vertically(tree, child, depth=depth+1)


def print_tree(tree, root, w=15):
    """ Print a constituency tree in a nice horizontal way. """
    # todo: calcualte w automatically by looking at the leaf lengths
    has_children = True
    prev_layer = [(root, True)]
    while has_children:
        has_children = False
        new_layer = []
        print('|', end='')
        for part, visible in prev_layer:
            f = '{:^' + str(w * (part.right-part.left)-1) + '}|'
            print(f.format(part.lhs if visible else ''), end='')
            if tree[part]:
                has_children = True
                for child in tree[part]:
                    new_layer.append((child, True))
            else:
                new_layer.append((part, False))
        print('')
        prev_layer = new_layer
    f = '{:^' + str(w-1) + '}|'
    print('|', end='')
    for word, visible in prev_layer:
        print(f.format(word.rhs[0]), end='')
    print('')
