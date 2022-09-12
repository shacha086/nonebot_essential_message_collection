from pathlib import Path


class Object:
    @staticmethod
    def __main_path() -> Path:
        (path := Path(__file__).parent.parent.parent).mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def data_path() -> Path:
        (path := Object.__main_path() / 'data' / 'essential_message_collection').mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def db_path() -> Path:
        return Object.data_path() / 'database.db'

    @staticmethod
    def image_path() -> Path:
        (path := Object.data_path() / 'images').mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def resources_path() -> Path:
        return Path(__file__).parent / 'resources'

