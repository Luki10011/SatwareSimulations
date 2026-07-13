
import pyfiglet


def welcome(projectName : str, projectVersion : str) -> None:
    ascii_art = pyfiglet.figlet_format("SatWare", font = "doom")
    print(ascii_art)
    print(f"Project: {projectName}")
    print(f"Version: {projectVersion}")