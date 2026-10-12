from road_to_draw.models import TransfermarktScraper

ts = TransfermarktScraper()

df = ts.get_league_market_values(season_id=2025)

conn = ts.get_db_connection("C:/Code/road_to_draw/secrets.toml", "dev")

df.write_database("market_values", connection=conn, engine="sqlalchemy")
