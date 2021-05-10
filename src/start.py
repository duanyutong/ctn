import os

from tweet_notifier import TweetNotifier

if __name__ == "__main__":
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "tables",
        "sample.xlsx",
    )
    notifier = TweetNotifier(path)
