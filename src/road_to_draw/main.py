import random
import time

from loguru import logger

from road_to_draw.models import TransfermarktScraper

logger.add("261018_logging.log")
ts = TransfermarktScraper()
conn = ts.get_db_connection("C:/Code/road_to_draw/secrets.toml", "dev")

# Pull club ids per season
# for i in range(2005, 2027):
#     df = ts.get_club_ids(season_id=i)
#     df.write_database(
#         "club_ids",
#         connection=conn,
#         engine="sqlalchemy",
#         if_table_exists='append'
#         )
#     time.sleep(random.randint(1,4))

# Pull player per club and season
# query = "select * from club_ids"
# df = ts.run_query(
#     query=query,
#     secrets_path="C:/Code/road_to_draw/secrets.toml",
#     db_env="dev"
# )

# for id, year in df.select("id", "season_from").iter_rows():
#     df = ts.get_club_player(season_id=year, club_id=id)
#     df.write_database(
#         "club_player",
#         connection=conn,
#         engine="sqlalchemy",
#         if_table_exists='append'
#         )
#     time.sleep(random.randint(1,4))

# Pull market value history per player

query = "select distinct id from club_player where id not in (select distinct player_id from player_market_values)"
df = ts.run_query(
    query=query, secrets_path="C:/Code/road_to_draw/secrets.toml", db_env="dev"
)

print(df.shape[0])

for id in df["id"]:
    df = ts.get_player_market_values(id)
    df.write_database(
        "player_market_values",
        connection=conn,
        engine="sqlalchemy",
        if_table_exists="append",
    )
    time.sleep(random.randint(3, 6))
