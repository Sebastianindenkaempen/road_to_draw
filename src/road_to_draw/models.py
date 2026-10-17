import re
import tomllib

import polars as pl
import requests
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import create_engine


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


class TransfermarktScraper(DataLoader):
    def __init__(self):
        self.HEADERS = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.BASE_URL = "https://www.transfermarkt.de/bundesliga/startseite/"

    def get_value_from_string(self, mw_string) -> float:
        """
        Strips raw market value from transfermarkt and
        transforms it into a float value

        Args:
            mw_string: market value in string format

        Returns:
            Market value in float format
        """
        mw_string = mw_string.replace(",", ".")

        mrd_pattern = re.compile(r"\bMrd\. €", re.IGNORECASE)
        mio_pattern = re.compile(r"\bMio\. €", re.IGNORECASE)
        tsd_pattern = re.compile(r"\bTsd\. €", re.IGNORECASE)
        multiplier = 0

        if mrd_pattern.search(mw_string):
            multiplier = 1000000000
            mw = re.sub(mrd_pattern, "", mw_string)
        elif mio_pattern.search(mw_string):
            multiplier = 1000000
            mw = re.sub(mio_pattern, "", mw_string)
        elif tsd_pattern.search(mw_string):
            multiplier = 1000
            mw = re.sub(tsd_pattern, "", mw_string)
        else:
            logger.warning(f"No matching pattern found for {mw_string}")

        return float(mw) * multiplier

    def get_league_market_values(
        self, season_id: int, competition_id: str = "L1"
    ) -> pl.DataFrame:
        url = self.BASE_URL + f"wettbewerb/{competition_id}/plus/?saison_id={season_id}"

        response = requests.get(url, headers=self.HEADERS)

        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.select_one("table.items > tbody")

        if not table:
            return pl.DataFrame()

        clubs = []
        for row in table.find_all("tr", recursive=False):
            name_elem = row.select_one("td.hauptlink a")
            value_elem = row.select_one("td.rechts a")
            avg_value = row.select_one("td.rechts")

            if name_elem and value_elem:
                clubs.append(
                    {
                        "club": name_elem.get_text(strip=True),
                        "total_market_value": value_elem.get_text(strip=True),
                        "average_market_value": avg_value.get_text(strip=True)
                        if avg_value
                        else 0,
                    }
                )

        df = pl.DataFrame(clubs)

        df = df.with_columns(
            pl.col("total_market_value")
            .map_elements(self.get_value_from_string, return_dtype=pl.Float64)
            .round(0)
            .cast(pl.Int64)
            .alias("total_market_value_new")
        ).with_columns(
            pl.col("average_market_value")
            .map_elements(self.get_value_from_string, return_dtype=pl.Float64)
            .round(0)
            .cast(pl.Int64)
            .alias("average_market_value_new")
        )
        df = (
            df.drop("total_market_value")
            .drop("average_market_value")
            .with_columns(
                (pl.col("total_market_value_new") / pl.col("average_market_value_new"))
                .round()
                .cast(pl.Int16)
                .alias("squad_size")
            )
            .with_columns(season_from=season_id)
            .with_columns(season_to=season_id + 1)
        )

        return df

    def get_club_ids(self, season_id: int, competition_id: str = "L1") -> pl.DataFrame:

        api_url = f"https://transfermarkt-api.fly.dev/competitions/{competition_id}/clubs?season_id={season_id}"

        response = requests.get(api_url)
        if response.status_code == 200:
            logger.info("Data successfully recieved")
        else:
            raise ConnectionError(
                f"Connection failed response code: {response.status_code}"
            )

        clubs = response.json()["clubs"]
        df = pl.DataFrame(
            {
                "id": [club["id"] for club in clubs],
                "name": [club["name"] for club in clubs],
                "season_from": season_id,
                "season_to": season_id + 1,
            }
        )
        df.with_columns(pl.col("id").cast(pl.Int32))

        return df

    def get_club_player(
        self, season_id: int, competition_id: str = "L1"
    ) -> pl.DataFrame:

        api_url = f"https://transfermarkt-api.fly.dev/clubs/{competition_id}/players?season_id={season_id}"
        response = requests.get(api_url)
        if response.status_code == 200:
            logger.info("Data successfully recieved")
        else:
            raise ConnectionError(
                f"Connection failed response code: {response.status_code}"
            )

        players = response.json()["players"]
        df = pl.DataFrame(
            {
                "id": [p["id"] for p in players],
                "name": [p["name"] for p in players],
                "position": [p["position"] for p in players],
                "shirt_number": [p["shirtNumber"] for p in players],
                "is_captain": [p["isCaptain"] for p in players],
                "date_of_birth": [p["dateOfBirth"] for p in players],
                "nationality": [p["nationality"] for p in players],
                "height": [p["height"] for p in players],
                "joined_on": [p["joinedOn"] for p in players],
            }
        )

        return df

    # def get_player_market_values(self, season_id: int, competition_id: str = "L1") -> pl.DataFrame:
