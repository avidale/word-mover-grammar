# word-mover-grammar
A constituency grammar parser with support of word embeddings

Approach 1: just hack the NLTK grammar by adding specific productions for each new text

```python
# 1. Create the basic grammar
from nltk import CFG
from nltk.parse import BottomUpLeftCornerChartParser

grammar = CFG.fromstring("""
S -> TURN COLOR_OF_DEVICE COLOR
COLOR -> 'синий' | 'зеленый'
TURN -> 'включи' | 'сделай' | 'поставь'
COLOR_OF_DEVICE -> COLOR_N | COLOR_N DEVICE
COLOR_N -> 'цвет' | 'свет'
DEVICE -> 'лампочки'
""")

# 2. Download a word2vec model
import compress_fasttext
small_model = compress_fasttext.models.CompressedFastTextKeyedVectors.load(
    'https://github.com/avidale/compress-fasttext/releases/download/v0.0.1/ft_freqprune_100K_20K_pq_100.bin'
)
small_model.init_sims()

# 3. Make the grammar enrichable
import word_mover_grammar
hacked_grammar = word_mover_grammar.grammar_tools.HackedGrammar(
    grammar=grammar, 
    w2v=small_model, 
    min_sims={'COLOR': 0.5},
)

# 4. Enrich the grammar for the new text and parse it
text = 'сделай цвет лампочки фиолетовый'
new_parser = BottomUpLeftCornerChartParser(hacked_grammar.enrich_grammar(text))

print(new_parser.parse_one(text.split()))
# (S
#   (TURN сделай)
#   (COLOR_OF_DEVICE (COLOR_N цвет) (DEVICE лампочки))
#   (COLOR фиолетовый))
```

Approach 2: code my own parser with fuzzy nonterminals (TODO)
