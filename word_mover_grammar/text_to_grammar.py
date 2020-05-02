import yaml

from word_mover_grammar.grammar import Symbol, NonTerminal, Production, MatchingMode
from word_mover_grammar.grammar import Terminal, AnyTerminal, W2VTerminal, LemmaTerminal, RegexTerminal
from word_mover_grammar.grammar import Grammar


from typing import Dict


def add_production(symbols: Dict[str, Symbol], lhs, rhs, mode=MatchingMode.EXACT):
    if lhs not in symbols:
        symbols[lhs] = NonTerminal(name=lhs)
    lhs_symbol: NonTerminal = symbols[lhs]
    new_rhs = []
    for symbol in rhs:
        is_terminal = False
        if symbol.startswith("'") and symbol.endswith("'"):
            symbol = symbol.strip("'")
            is_terminal = True
        new_rhs.append(symbol)
        if symbol in symbols:
            continue
        if not is_terminal and (symbol[0].isupper() or symbol.startswith('$')):
            symbols[symbol] = NonTerminal(name=symbol)
        else:
            if symbol == '.':
                symbols[symbol] = AnyTerminal(name=symbol, data=symbol)
            elif mode == MatchingMode.EXACT:
                symbols[symbol] = Terminal(name=symbol, data=symbol)
            elif mode == MatchingMode.W2V:
                symbols[symbol] = W2VTerminal(name=symbol, data=symbol)
            elif mode == MatchingMode.LEMMA:
                symbols[symbol] = LemmaTerminal(name=symbol, data=symbol)
            elif mode == MatchingMode.REGEX:
                symbols[symbol] = RegexTerminal(name=symbol, data=symbol)
            else:
                raise ValueError('Matching mode `{}` not supported'.format(mode))
    production = Production(lhs=lhs_symbol, rhs=tuple(symbols[s] for s in new_rhs))
    lhs_symbol.productions.append(production)


def load_granet(text) -> Grammar:
    lhs = None
    mode = 'exact'
    child_mode = mode
    symbols: Dict[str, Symbol] = {}
    slots = None

    def add(lhs, rhs_text, mode):
        parts = [p.strip() for p in rhs_text.split('|')]
        for part in parts:
            if not part.strip():
                continue
            rhs = tuple(part.split())
            add_production(symbols, lhs, rhs, mode=mode)

    in_slots = False
    slots_lines = []
    for i, line in enumerate(text.split('\n')):
        # slots are parsed as YAML, but the rest is not necessarily YAML
        if in_slots:
            if line.startswith(' '):
                slots_lines.append(line)
                continue
            else:
                in_slots = False
                slots = yaml.safe_load('\n'.join(slots_lines)).get('slots')
        if line.startswith('slots:'):
            in_slots = True
            slots_lines.append(line)
            continue

        if '#' in line:
            with_comment = line.split('#', 1)
            line = with_comment[0]

        # exit the previous non-terminal
        if not line.strip():
            lhs = None
            child_mode = mode
            continue
        # change global mode
        if line.startswith('%'):
            # todo: check if the directive is recognized
            mode = line.strip()[1:]
            child_mode = mode
        if line.startswith('  '):
            if not lhs:
                raise SyntaxError('LHS undefined on line {}.'.format(i))
            line = line.strip()
            if line.startswith('-'):
                line = line[1:]
            if line.startswith('%'):
                child_mode = line.strip()[1:]
                continue
            add(lhs, line, mode=child_mode)
        else:
            # parse lhs
            if ':' in line and '->' in line:
                raise SyntaxError('Both ":" and "->" are present in the line {}.'.format(i))
            elif ':' in line:
                parts = line.strip().split(':')
            elif '->' in line:
                parts = line.strip().split('->')
            else:
                raise SyntaxError('Expected a separator (":" or "->") in line {}, but found none.'.format(i))
            if len(parts) > 2:
                raise SyntaxError('Multiple separators within the line {}.'.format(i))
            lhs = parts[0].strip()
            child_mode = mode
            if len(parts) == 2:
                add(lhs, parts[1], mode=child_mode)

    # todo: infer the start symbol
    # todo: validate the slots
    return Grammar(start_symbol='root', symbols=symbols, slots=slots)
