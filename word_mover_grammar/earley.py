import random

from collections import defaultdict


class State:
    def __init__(self, lhs, rhs, dot=0, origin=0):
        self.lhs = lhs
        self.rhs = rhs
        self.dot = dot
        self.origin = origin

    @property
    def tuple(self):
        return self.lhs, self.rhs, self.dot, self.origin

    @property
    def finished(self):
        return self.dot >= len(self.rhs)

    @property
    def current_token(self):
        return None if self.finished else self.rhs[self.dot]

    @property
    def rule(self):
        return self.lhs, self.rhs

    def advance(self):
        return State(self.lhs, self.rhs, self.dot+1, self.origin)

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
        self.final_node = self.final_state, len(self.tokens)

    @property
    def success(self):
        return self.final_node in self.forest

    def print(self, node=None, depth=0):
        """ Text representation of the forest """
        if node is None:
            node = self.final_node
        if node[0].finished:
            l = '{} {} -> {}'.format('  ' * depth, node[0].lhs, ' '.join(node[0].rhs))
            print('{:30} {}'.format(l, [node[0].origin, node[1]]))
        if depth > 20:
            return
        for i, pair in enumerate(self.forest[node]):
            if i > 0:
                print('  ' * (depth + 1), '____')
            for j, c in enumerate(pair):
                self.print(c, depth=depth + c[0].finished)

    def sample_a_tree(self, node=None, tree=None, last_parent=None):
        if node is None:
            node = self.final_node
        if tree is None:
            tree = defaultdict(list)
        if last_parent and node[0].finished:
            tree[last_parent].append(node)

        # todo: somehow take into account production probabilities
        if self.forest[node]:
            pair = random.choice(list(self.forest[node]))
            for j, c in enumerate(pair):
                self.sample_a_tree(c, tree=tree, last_parent=node if node[0].finished else last_parent)
        return tree

    def sample_top_trees(self):
        # todo: implement top-k (or even top-p) beam search sampling of parse trees
        raise NotImplementedError()


class EarleyParser:
    def __init__(self, rules):
        self.rules = rules

    @property
    def root(self):
        return self.rules[0]

    def parse(self, words):
        initial_state = State(*self.root)
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
                    for prev_state in states[state.origin]:
                        if state.lhs == prev_state.current_token:
                            new_state = prev_state.advance()
                            if new_state not in states[k]:
                                states[k].add(new_state)
                                old_states.add(new_state)
                                # print('adding new state from completer', new_state)
                                # we add even non-unique children, because they belong to different parses
                            children = (prev_state, state.origin), (state, k)
                            forest[(new_state, k)].add(children)

                else:
                    if state.current_token.isupper():  # todo: check non-terminals by class
                        # predictor: create possible child non-terminals
                        for rule in self.rules:
                            # todo: loop over the dict element
                            if rule[0] != state.current_token:
                                continue
                            new_state = State(*rule, 0, k)
                            if new_state not in states[k]:
                                # print('adding new state from predictor', new_state)
                                old_states.add(new_state)
                                states[k].add(new_state)
                    else:
                        # scanner: move pointer within the rule if we matched a terminal
                        # todo: replace string-only terminals with regex/w2v matchers
                        if state.current_token == token:
                            states[k + 1].add(state.advance())
        final_state = State(*self.root, len(self.root[1]), 0)
        return ParseResult(tokens=words, forest=forest, final_state=final_state)
