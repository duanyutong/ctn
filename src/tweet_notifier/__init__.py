import os
import pickle
import string
from typing import Dict, List, Set

import pandas as pd

from . import email, lib

USER_MAP_PATH = os.path.join(os.path.expanduser("~"), "user_map.pkl")
LOG_PATH = os.path.join(os.path.expanduser("~"), "tweet.log")


def parse_request_table(path: str) -> pd.DataFrame:
    """Return a dict of userid mapped to keywords.

    Capitalised columns are in the original file.
    Derived columns are all lower case.
    """
    table = pd.read_excel(path).dropna()
    table["username"] = table["Link"].str.split("/").str[-1]
    return table


def filter_tweets(
    tweets: List[Dict[str, str]], keywords: Set[str]
) -> List[Dict[str, str]]:
    """Filter a list of tweets from json response given a list of keywords."""

    def tweet_is_matched(tweet):
        words = set(
            tweet["text"]
            .lower()
            .translate(str.maketrans("", "", string.punctuation))
            .split()
        )
        return bool(words & keywords)

    return list(filter(tweet_is_matched, tweets))


class TweetNotifier:
    def __init__(self, path_table: str, receivers: List[str]):
        self.logger = lib.get_logger(
            "TweetNotifier", logpath=LOG_PATH, rotate=True
        )
        self.bearer_token = lib.get_bearer_token()
        self.smtp_config = email.get_smtp_config()
        df = parse_request_table(path_table)
        self.user_map = self.read_user_map()
        self.update_user_map(df["username"])
        self.save_user_map()
        self.tracked = self.generate_tracking_table(df)
        self.receivers = receivers

    def read_user_map(
        self,
    ):
        """Keep track of known userids and their last update time.

        user_map is a dict usernames to userids and last tweet ids.
        """
        if os.path.isfile(USER_MAP_PATH):
            with open(USER_MAP_PATH, "rb") as f:
                return pickle.load(f)
        return {}

    def update_user_map(self, username_column):
        # find which userids are missing in the db
        mask = username_column.apply(lambda x: x not in self.user_map)
        usernames = username_column[mask].tolist()
        if usernames:
            userids = lib.lookup_user(self.bearer_token, usernames)
            for username, userid in zip(usernames, userids):
                self.user_map[username] = {"userid": userid}

        self.logger.debug(f"Updated user map:\n{self.user_map}")

    def save_user_map(self):
        os.makedirs(os.path.dirname(USER_MAP_PATH), exist_ok=True)
        with open(USER_MAP_PATH, "wb") as f:
            pickle.dump(self.user_map, f)

    def generate_tracking_table(self, df, kw_delimiter="/"):
        return {
            self.user_map[username]["userid"]: {
                "username": username,
                "keywords": set(keywords),
                "last_tweet_id": None,
            }
            for username, keywords in zip(
                df["username"], df["Keywords"].str.split(kw_delimiter)
            )
        }

    def refresh(self, forward=True):
        for userid in self.tracked:
            meta, tweets = lib.get_user_tweets(
                self.bearer_token,
                userid,
                since_id=self.tracked[userid]["last_tweet_id"],
            )
            if tweets:  # got new tweets since last tweet id
                self.logger.info(
                    f"Found {meta['result_count']} new tweets "
                    f"for userid: {userid}"
                )
                self.tracked[userid]["last_tweet_id"] = meta["newest_id"]
                tweets_filtered = filter_tweets(
                    tweets, self.tracked[userid]["keywords"]
                )
                self.logger.info(
                    f"{len(tweets_filtered)}/{meta['result_count']} matched "
                    f"for userid: {userid}, "
                    f"username: {self.tracked[userid]['username']}"
                )
                if tweets_filtered and forward:
                    self.forward(
                        self.tracked[userid]["username"], tweets_filtered
                    )
            else:
                self.logger.info(f"No new tweets found for userid: {userid}")

    def forward(self, username, tweets):
        """Forward a list of tweets from a given username."""
        self.logger.info(
            f"Forwarding {len(tweets)} new matching tweets from @{username}"
        )
        msgs = [email.create_from_tweet(username, tweet) for tweet in tweets]
        email.send_emails(msgs, self.receivers, **self.smtp_config)

    def main_loop(self):
        self.logger.info("Refreshing for initial load...")
        self.refresh(forward=False)
        while True:
            self.logger.info("Sleeping...")
            lib.countdown_sec(10)
            self.logger.info("Refreshing...")
            self.refresh(forward=True)
