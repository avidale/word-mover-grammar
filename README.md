# word-mover-grammar
This package implements a context-free grammar parser with rather flexible
 matching of terminals. The supported matching modes are:
* standard exact matching (like e.g. in [NLTK](https://www.nltk.org/book/ch08.html)); 
* regex matching (like e.g. in [Lark](https://github.com/lark-parser/lark));
* lemma matching (like e.g. in [Yandex Alice](https://yandex.ru/dev/dialogs/alice/doc/nlu-docpage/));
* word embedding matching (no known Python implementation).

The mission of this package is to enable easy creation of custom
grammars for various NLU problems, such as sentence classification
or extraction of semantic slots.

It is called "word mover grammar", because, just like word-mover-distance,
it applies word embeddings to sentence templates, 
but in a more structured way.

#### Table of Contents
1. [Installation](#installation)
1. [Basic parsing](#basic-parsing)
1. [Ambiguous phrases](#ambiguous-phrases)
1. [Inexact matcing](#inexact-matching)
1. [Forms and slots](#forms-and-slots)
1. [Future plans](#future-plans)

## Installation

`pip install word-mover-grammar`

## Basic parsing
WMG production rules can be described in a text file with the following syntax:

- Lowercase tokens represent terminals, and capitalized tokens - terminals. 
You can also prepend non-terminals with `$` symbol
and/or put terminals into single brackets. 
- Left- and right-hand sides of productions can be separated 
with `:` or `->` tokens.
- Different right-hand-sides of the same production can be separated 
with `|` symbol or with newline followed by several whitespaces.
In the latter case, each RHS can be prepended with `-`, which makes
the format YAML-compatible.
- One-line comments can start with `#` symbol.

The snippet below shows how to create a simple grammar and parser:
```python
import word_mover_grammar as wmg
rules = """
S : NP VP
NP: N | A NP
VP: V | VP NP | VP PP
PP: P NP
N: fruit | flies | bananas
A: fruit
V: like | flies | are
P: like
"""
grammar = wmg.text_to_grammar.load_granet(rules)
parser = wmg.earley.EarleyParser(grammar, root_symbol='S')
```
The main inference method is `parser.parse(tokens)`, where `tokens` 
is a list of strings. This method returns a `ParseResult` object, 
that stores the parse trees.
```python
result = parser.parse('bananas are fruit'.split())
print(result.success)
for tree in result.iter_trees():
    wmg.earley.print_tree(tree, result.final_state)
    print('=======')
```
The output of the code above is given below. 
The parser has correctly inferred that the sentence "bananas are fruit"
consists of the noun phrase "bananas" and the verb phrase "are fruit",
which in turn consists of the verb "are" and the noun "fruit".
```
True
|                     .                      |
|                     S                      |
|      NP      |             VP              |
|      N       |      VP      |      NP      |
|   bananas    |      V       |      N       |
|              |     are      |    fruit     |
|   bananas    |     are      |    fruit     |
=======
```
If the phrase cannot be parsed, `result.success` will be 
`False` - e.g. here:
```python
result = parser.parse('bananas bananas bananas'.split())
print(result.success)  # False
```

## Ambiguous phrases
Some phrases can be parsed in more that one way. In this case, 
`result.success` will still be `True`, but the number of trees will be
more than one. 
```python
result = parser.parse('fruit flies like bananas'.split())
print(result.success)
for tree in result.iter_trees():
    wmg.earley.print_tree(tree, result.final_state)
    print('=======')
```
The phrase above can be understood in two ways: 
* that particular insects are fond of bananas;
* that the style of flying of some fruit resembles that of bananas.
The parsing result has trees for both interpretations:
```
|                             .                             |
|                             S                             |
|      NP      |                     VP                     |
|      N       |      VP      |             PP              |
|    fruit     |      V       |      P       |      NP      |
|              |    flies     |     like     |      N       |
|              |              |              |   bananas    |
|    fruit     |    flies     |     like     |   bananas    |
=======
|                             .                             |
|                             S                             |
|             NP              |             VP              |
|      A       |      NP      |      VP      |      NP      |
|    fruit     |      N       |      V       |      N       |
|              |    flies     |     like     |   bananas    |
|    fruit     |    flies     |     like     |   bananas    |
=======
```

## Inexact matching
By default, WMG uses only exact matching of tokens.
However, several more matching ways can be activated by special directives:
* `%w2v`: words are considered equal, 
if the dot product of their embeddings is above the threshold 
(default one is `0.5`). If this mode is used, parser constructor
requires one more argument `w2v` - a callable that transforms a word
into a vector.
* `%lemma`: words are considered equal, if at least some of their
normal forms coincide. If this mode is used, parser constructor
requires one more argument `lemmer` - a callable that transforms a word
into a list of normal forms.
* `%regex`: a word is matched, if it can be parsed by the regular expression.
* `%exact`: words are considered equal, only if they are the same word.

If a directive is inserted within a non-terminal, it is active
until the end of this non-terminal. 
If a directive is inserted outside of non-terminals, it is active until 
the next directive outside of non-terminals, but can be temporarily 
overridden within non-terminals.

The code below shows an example of inexact matching 
for a simple Russian grammar.
```python
grammar = wmg.text_to_grammar.load_granet("""
root:
    включи $What $Where
$What:
    %w2v
    свет | кондиционер
    %regex
    .+[аеиюя]т[ое]р
$Where:
    в $Room
    на $Room
$Room:
    %lemma
    ванна | кухня | спальня
""")
```

As a lemmer, we can use pymorphy2
```python
from pymorphy2 import MorphAnalyzer

analyzer = MorphAnalyzer()

def lemmer(text):
    return [p.normal_form for p in analyzer.parse(text)]
```

For embeddings, we can use a compressed FastText model
```python
import compress_fasttext

small_model = compress_fasttext.models.CompressedFastTextKeyedVectors.load(
    'https://github.com/avidale/compress-fasttext/releases/download/v0.0.1/ft_freqprune_100K_20K_pq_100.bin'
)
small_model.init_sims()

def w2v(text):
    return small_model.word_vec(text, use_norm=True)
```

The parser combines all the objects from above:
```python
parser = wmg.earley.EarleyParser(grammar, w2v=w2v, w2v_threshold=0.5, lemmer=lemmer)
```
The phrase below contains an OOV word `пылесос`, but its embedding is
 close to that of `вентилятор`, so the match succeeds. 
Another problem
is that `спальне` is not equal to `спальня`, but their normal forms
coinside and therefore match is possible.
```python
tokens = 'включи пылесос в спальне'.split()
result = parser.parse(tokens)
print(result.success)
for tree in result.iter_trees():
    wmg.earley.print_tree(tree, result.final_state, w=16)
    print('=======')
```
The output is following:
```
True
|                               .                               |
|                             root                              |
|    включи     |     $What     |            $Where             |
|               |  кондиционер  |       в       |     $Room     |
|               |               |               |    спальня    |
|    включи     |    пылесос    |       в       |    спальне    |
=======
```

## Forms and slots
In dialogue systems, phrases are often viewed as *forms* - containers of information.
Each meaningful piece of information can be stored in a typed *slot*. 
In WMG, each slot is a associated with some non-terminal symbol. 
This association can be configured in the same file as the production rules.

```python
import word_mover_grammar as wmg
cfg = """
root:
    turn the $What $Where on
    turn on the $What $Where
$What: light | conditioner
$Where: in the $Room
$Room: bathroom | kitchen | bedroom | living room
slots:
    what:
        source: $What                   
    room:
        source: $Room
"""
grammar = wmg.text_to_grammar.load_granet(cfg)
parser = wmg.earley.EarleyParser(grammar)
result = parser.parse('turn on the light in the living room'.split())
print(result.slots)
```
The result will be a 
[yandex-compatible(https://yandex.ru/dev/dialogs/alice/doc/nlu-docpage/#data_to_skill)] 
map of slot names to the slots found in the phrase.
```
{'what': {'type': 'string', 'value': 'light', 'text': 'light', 'tokens': {'start': 3, 'end': 4}},
 'room': {'type': 'string', 'value': 'living room', 'text': 'living room', 'tokens': {'start': 6, 'end': 8}}}
```


## Future plans
In the future, we plan to enhance the library in the following ways:
* Conversion to and from NLTK grammars
* Support of quantifiers and brackets
* Probabilistic parsing
* Extraction of intents and slots from parse trees
* Full compatibility with Yandex Alice syntax
* You name it!
