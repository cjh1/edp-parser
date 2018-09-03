import pyparsing as pp
import json
import sys

def _build_ana_rcp_parser():
    separator = pp.Suppress(':')
    key = pp.Word(pp.printables, excludeChars=':')
    value = pp.Regex(r'[^\n\r]*') + pp.LineEnd().suppress()

    block_name = key + separator  + pp.LineEnd().suppress()

    platemap_keylist = pp.Literal('platemap_comp4plot_keylist') + separator +  pp.delimitedList(pp.Word(pp.alphas))
    run_ids = pp.Literal('run_ids') + separator +  pp.delimitedList(pp.Word(pp.nums))

    key_value = platemap_keylist | run_ids | key + separator + value


    indent_stack = [1]
    block = pp.Forward()
    block_body = ( block | key_value)

    indented_block = pp.Dict(pp.ungroup(pp.indentedBlock(block_body, indent_stack)))
    block << ( block_name + indented_block | key_value)

    return pp.OneOrMore( pp.Dict(pp.Group(block)))


def parse_ana_rcp(contents):
    parser = _build_ana_rcp_parser()
    tree = parser.parseString(contents)

    return tree.asDict()


def main():
    with open(sys.argv[1]) as f:
        contents = f.read()
        d = parse_ana_rcp(contents)
        print(json.dumps(d, indent=4))


if __name__ == "__main__":
    main()

