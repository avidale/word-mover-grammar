from word_mover_grammar.earley import EarleyParser

fruit_productions = [
    ['^', ('S',)],
    ['S', ('NP', 'VP',)],
    ['NP', ('N',)],
    ['NP', ('A', 'NP',)],
    ['VP', ('V',)],
    ['VP', ('VP', 'NP',)],
    ['VP', ('VP', 'PP',)],
    ['PP', ('P', 'NP',)],
    ['N', ('fruit',)],
    ['N', ('flies',)],
    ['N', ('bananas',)],
    ['A', ('fruit',)],
    ['V', ('like',)],
    ['V', ('flies',)],
    ['P', ('like',)],
]


def test_simple_parse():
    words = 'bananas flies'.split()
    parser = EarleyParser(fruit_productions)
    result = parser.parse(words)
    assert result.success
    result.print()
    print(result.sample_a_tree())
    assert len(list(result.iter_trees())) == 1


def test_bad_parse():
    words = 'bananas bananas'.split()
    parser = EarleyParser(fruit_productions)
    result = parser.parse(words)
    assert not result.success


def test_twoway_parse():
    words = 'fruit flies like bananas'.split()
    parser = EarleyParser(fruit_productions)
    result = parser.parse(words)
    assert result.success
    assert len(list(result.iter_trees())) == 2
