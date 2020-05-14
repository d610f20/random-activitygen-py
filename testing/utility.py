from pathlib import Path
from pprint import pprint
from sys import stderr


class TestInstance:
    def __init__(self, name: str, net_file: str, gen_stats_in_file: str, gen_stats_out_file: str, real_stats_file: str,
                 centre: str):
        self.name = name
        self.net_file = net_file
        self.gen_stats_in_file = gen_stats_in_file
        self.gen_stats_out_file = gen_stats_out_file
        self.real_stats_file = real_stats_file
        self.centre = centre

        try:
            Path(self.net_file).resolve(strict=True)
            Path(self.gen_stats_in_file).resolve(strict=True)
            Path(self.gen_stats_out_file).resolve(strict=True)
            Path(self.real_stats_file).resolve(strict=True)
        except FileNotFoundError:
            print(f"Files for test instance: {self.name} does not exist", file=stderr)
            pprint(self.__dict__)
            exit(1)


# Define paths and attributes for tests
test_instances = [
    TestInstance("Aalborg", "../in/cities/aalborg.net.xml", "../in/cities/aalborg.stat.xml",
                 "../out/cities/aalborg.stat.xml", "../stats/aalborg.stat.xml", "9396,12766"),
    TestInstance("Esbjerg", "../in/cities/esbjerg.net.xml", "../in/cities/esbjerg.stat.xml",
                 "../out/cities/esbjerg.stat.xml", "../stats/esbjerg.stat.xml", "7476,1712"),
    TestInstance("Randers", "../in/cities/randers.net.xml", "../in/cities/randers.stat.xml",
                 "../out/cities/randers.stat.xml", "../stats/randers.stat.xml", "19516,6606"),
    TestInstance("Slagelse", "../in/cities/slagelse.net.xml", "../in/cities/slagelse.stat.xml",
                 "../out/cities/slagelse.stat.xml", "../stats/slagelse.stat.xml", "6073,4445"),
    TestInstance("Vejen", "../in/cities/vejen.net.xml", "../in/cities/vejen.stat.xml",
                 "../out/cities/vejen.stat.xml", "../stats/vejen.stat.xml", "37800,3790")
]
