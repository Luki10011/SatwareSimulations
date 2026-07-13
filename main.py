import pyfiglet
from utils.welcome import welcome

PROJECT_NAME = "SatWare Simullations"
PROJECT_VERSION = "0.1.0"


def main() -> None:
    welcome(PROJECT_NAME, PROJECT_VERSION)


if __name__ == "__main__":
    main()