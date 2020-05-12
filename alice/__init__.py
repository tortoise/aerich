__version__ = '0.1.0'

from alice.cmd import CommandLine


def main(argv):
    command = CommandLine(argv)


if __name__ == '__main__':
    main(None)
