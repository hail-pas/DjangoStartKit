from enum import Enum


class Environment(str, Enum):
    development = "Development"
    test = "Test"
    production = "Production"
