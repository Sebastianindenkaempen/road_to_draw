import tomllib

from sqlalchemy import create_engine

# Classes here


class DataLoader:
    def get_db_connection(self, secrets_path: str, db_env: str):
        """
        Creates sqlalchemy cursor
        Args:
            secrets_path: path to secrets file
            db_env: ["dev", "prod"]

        Returns:
            sqlalchemy cursor
        """
        with open(secrets_path, "rb") as f:
            credentials = tomllib.load(f)
            user = credentials["database"]["user"]
            password = credentials["database"]["password"]

        engine = create_engine(
            f"postgresql+psycopg://{user}:{password}@localhost:5432/road_to_draw_{db_env}"
        )
        return engine

    def write_df_to_db(self):
        return NotImplementedError
