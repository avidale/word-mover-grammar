import nltk.grammar
import random
import sys


from collections import defaultdict


from nltk.grammar import Nonterminal


def c2t(constituent, taggable):
    c = str(constituent)
    if c in taggable:
        return 'B-' + taggable[c]
    return 'O'


def sample_tags(grammar, start=None, depth=None, taggable=None):
    if not start:
        start = grammar.start()
    if depth is None:
        depth = sys.maxsize
    if not taggable:
        taggable = {}
    return _sample_all_tags(grammar, [(start, c2t(start, taggable))], depth, taggable)


def _sample_all_tags(grammar, items, depth, taggable):
    if items:
        frag1 = _sample_one_tag(grammar, items[0], depth, taggable)
        frag2 = _sample_all_tags(grammar, items[1:], depth, taggable)
        return frag1 + frag2
    else:
        return []


def _sample_one_tag(grammar, item, depth, taggable):
    try:
        item, tag = item
    except TypeError as e:
        print(item)
        raise e
    if depth > 0:
        if isinstance(item, Nonterminal):
            new_tag = c2t(item, taggable)
            if new_tag == 'O' and tag != 'O':
                new_tag = tag
            prod = random.choice(grammar.productions(lhs=item))
            new_items = [[c, new_tag] for c in prod.rhs()]
            if new_tag.startswith('B-'):
                for new_item in new_items[1:]:
                    new_item[1] = 'I-' + new_item[1][2:]
            frag = _sample_all_tags(grammar, new_items, depth - 1, taggable)
            return frag
        else:
            return [(item, tag)]


def get_top_label(text, parser):
    tree = try_parse(text, parser)
    if tree is None:
        return None
    return tree[0].label()


def try_parse(text, parser):
    try:
        tree = parser.parse_one(text.lower().split())
    except ValueError:
        return None
    return tree


class HackedGrammar:
    def __init__(self, grammar, w2v, min_sims):
        """
        :param grammar: nltk.grammar.CFG, the base grammar
        :param w2v: dict[str, np.array] - like model for fuzzy word matching
        :param min_sims: dict[str, float] - cosine similarity thresholds for each nonterminal
        """
        self.grammar = grammar
        self.w2v = w2v
        self.min_sims = min_sims
        self.keywords = defaultdict(list)
        self.nonterms = {}
        self.key_vectors = {}
        self.find_key_vectors()

    def find_key_vectors(self):
        """ Extract key vectors from self.grammar """
        for p in self.grammar.productions():
            lhs = p.lhs()
            if lhs.symbol() not in self.min_sims:
                continue
            if not isinstance(lhs, nltk.grammar.Nonterminal):
                continue
            self.nonterms[lhs.symbol()] = lhs
            rhs = p.rhs()
            if not isinstance(rhs, tuple):
                continue
            if len(rhs) != 1:  # todo: work with multiword expressions as well !
                continue
            self.keywords[lhs.symbol()].append(rhs[0])

        self.key_vectors = {
            k: [self.w2v.word_vec(w, use_norm=True) for w in v]
            for k, v in self.keywords.items()
        }

    def enrich_grammar(self, text):
        toks = text.split()

        new_productions = []

        for tok in toks:
            new_vec = self.w2v.word_vec(tok, use_norm=True)
            for key, vecs in self.key_vectors.items():
                for vec in vecs:
                    if new_vec.dot(vec) > self.min_sims[key]:
                        new_productions.append([key, tok])
                        break

        new_grammar = nltk.grammar.CFG(
            productions=list(self.grammar.productions()) + [
                nltk.grammar.Production(self.nonterms[l], (r,)) for l, r in new_productions
            ],
            start=self.grammar.start(),
        )
        return new_grammar
