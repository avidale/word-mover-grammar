import word_mover_grammar as wmg

from word_mover_grammar.earley import EarleyParser
from word_mover_grammar.grammar import rules2symbols

fruit_productions = [
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

fruit_symbols = wmg.grammar.Grammar(rules2symbols(fruit_productions), start_symbol='S')

slotted_granet = """
root:
    включи $What $Where
slots:
    what:
        source: $What                   
    where:
        source: $Where
$What:
    свет | кондиционер
$Where:
    в $Room
    на $Room
$Room:
    ванне | кухне | спальне
"""


def test_simple_parse():
    words = 'bananas flies'.split()
    parser = EarleyParser(fruit_symbols)
    result = parser.parse(words)
    assert result.success
    result.print()
    print(result.sample_a_tree())
    assert len(list(result.iter_trees())) == 1


def test_bad_parse():
    words = 'bananas bananas'.split()
    parser = EarleyParser(fruit_symbols)
    result = parser.parse(words)
    assert not result.success


def test_two_way_parse():
    words = 'fruit flies like bananas'.split()
    parser = EarleyParser(fruit_symbols)
    result = parser.parse(words)
    assert result.success
    assert len(list(result.iter_trees())) == 2


def test_granet_slots():
    g = wmg.text_to_grammar.load_granet(slotted_granet)
    assert 'what' in g.slots
    assert g.slots['what']['source'] == '$What'

    parser = wmg.earley.EarleyParser(g)

    result = parser.parse('включи свет в спальне'.split())
    assert set(result.slots.keys()) == {'what', 'where'}
    assert result.slots['what'].text == 'свет'
