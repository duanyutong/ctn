import os
import pickle

import pandas as pd

from . import lib

CACHE_DB_PATH = os.path.join(os.path.expanduser("~"), "tweet_cache.pkl")


def parse_request_table(path):
    """Return a dict of userid mapped to keywords."""
    table = pd.read_excel(path).dropna()
    table["username"] = table["Link"].str.split("/").str[-1]
    return table


class TweetNotifier:
    def __init__(self, path_table):
        self.bearer_token = lib.get_bearer_token()
        self.load_cache()
        self.table = parse_request_table(path_table)
        self.update_db()
        self.save_db()

    def load_cache(
        self,
    ):
        """Keep track of known userids and their last update time.

        self.db is a dict mapping usernames to userids and last tweet ids.
        """
        if os.path.isfile(CACHE_DB_PATH):
            with open(CACHE_DB_PATH, "rb") as f:
                self.db = pickle.load(f)
        else:
            self.db = {}

    def update_db(self):
        # find which userids are missing in the db
        mask = self.table["username"].apply(lambda x: x not in self.db)
        usernames = self.table["username"][mask].tolist()
        if usernames:
            userids = lib.lookup_user(self.bearer_token, usernames)
            for username, userid in zip(usernames, userids):
                self.db[username] = {"userid": userid}

        print("db")
        print(self.db)

    def save_db(self):
        os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)
        with open(CACHE_DB_PATH, "wb") as f:
            pickle.dump(self.db, f)

    def refresh(self):
        pass
