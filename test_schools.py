from pathlib import Path
from sys import stderr


class TestInstance:
    def __init__(self, name: str, gen_stats_file: str, real_stats_file: str):
        self.name = name
        self.gen_stats_file = gen_stats_file
        self.real_stats_file = real_stats_file

        try:
            Path(self.gen_stats_file).resolve(strict=True)
            Path(self.real_stats_file).resolve(strict=True)
        except FileNotFoundError:
            print(f"Files for test instance: {self.name} does not exist", file=stderr)
            exit(1)


test_instances = [
    TestInstance("Esbjerg", "out/cities/esbjerg.stat.xml", "stats/esbjerg.stat.xml"),
    TestInstance("Slagelse", "out/cities/slagelse.stat.xml", "stats/slagelse.stat.xml")
]


def main():
    
    pass


if __name__ == '__main__':
    main()
