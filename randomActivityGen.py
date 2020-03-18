"""RandomActivityGen.py
Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE

Input Options:
    -n, --net-file FILE     Input road network file to create activity for
    -s, --stat-file FILE    Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    -h --help           Show this screen.
    --version           Show version.
"""
from docopt import docopt

if __name__ == "__main__":
    args = docopt(__doc__, version="RandomActivityGen 0.1")
    print(f"Arguments: {args}")
