from abc import ABC, abstractmethod

import click
from aerich.enums import Color


class Output(ABC):
    @abstractmethod
    def success(self, message: str):
        pass

    @abstractmethod
    def warning(self, message: str):
        pass


class ClickOutput(Output):
    def success(self, message: str):
        click.secho(message, fg=Color.green)

    def warning(self, message: str):
        click.secho(message, fg=Color.yellow)


class PrintOutput(Output):
    def success(self, message: str):
        print(message)

    def warning(self, message: str):
        print(f"WARNING: {message}")
