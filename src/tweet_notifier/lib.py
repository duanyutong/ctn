"""Wrappers of APIv2 to perform certain twitter functions."""

import logging
import logging.handlers
import os
import sys
import time
from typing import cast

from . import apiv2


def countdown_sec(t):  # in seconds
    t = int(t)
    for i in reversed(range(t)):
        sys.stderr.write(f"\rSleeping... ({i:2d} s / {t} s)")
        time.sleep(1)
        sys.stdout.flush()
    print(f"\nSleep finished ({t} s)")


def get_logger(
    name=None,
    level="DEBUG",
    stream=True,
    logpath=None,
    mode="w",
    rotate=False,
):
    """Initiialise and configure a new logger."""
    _logger = logging.getLogger(name)
    if not _logger.handlers:  # configure the newly created logger
        _logger.setLevel(logging.DEBUG)  # text log always has debug and above
        formatter = logging.Formatter(  # log format for each line
            fmt=(
                "%(asctime)s [%(levelname)-8s] "
                "%(name)s.%(funcName)s+%(lineno)s: %(message)s"
            ),
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        if logpath:  # write to log file
            os.makedirs(os.path.dirname(logpath), exist_ok=True)
            open(logpath, "a").close()  # create log file if it does not exist
            if rotate:
                # mypy doesn't recognise TimedRotatingFileHandler as a
                # subclass of FileHandler
                fh = cast(
                    logging.FileHandler,
                    logging.handlers.TimedRotatingFileHandler(
                        logpath, when="midnight", encoding="utf-8"
                    ),
                )
            else:
                fh = logging.FileHandler(logpath, mode=mode, encoding="utf-8")
            fh.setFormatter(formatter)
            fh.setLevel(logging.DEBUG)  # text log always has debug and above
            _logger.addHandler(fh)
        if stream:
            sh = logging.StreamHandler()  # add stream handler
            sh.setLevel(logging.getLevelName(level))  # level only applies here
            sh.setFormatter(formatter)
            _logger.addHandler(sh)
    return _logger


def get_bearer_token():
    token = os.getenv("TWITTER_BEARER_TOKEN")
    if not token:
        raise ValueError("Bearer token not found in environment.")
    return token


def lookup_user(bearer_token, usernames, userfields=None):
    """
    List of usernames.

    Specify the usernames that you want to lookup below
    You can enter up to 100 comma-separated values.
    usernames = "usernames=TwitterDev,TwitterAPI"
    userfields = "user.fields=id"
    User fields are adjustable, options include:
    created_at, description, entities, id, location, name,
    pinned_tweet_id, profile_image_url, protected,
    public_metrics, url, username, verified, and withheld
    """
    params = {"usernames": ",".join(usernames)}
    if userfields is None:
        params["user.fields"] = "id"
    else:
        params["user.fields"] = ",".join(userfields)
    url = "https://api.twitter.com/2/users/by"
    resp = apiv2.connect_to_endpoint(bearer_token, url, params=params)
    return [user["id"] for user in resp["data"]]


def consolidate_pagination_responses(prev_resp, next_resp):
    resp = prev_resp.copy()
    resp["meta"]["oldest_id"] = next_resp["meta"]["oldest_id"]
    resp["meta"]["result_count"] += next_resp["meta"]["result_count"]
    resp["meta"]["previous_token"] = next_resp["meta"].get("previous_token")
    if "next_token" in next_resp["meta"]:  # continue pagination
        resp["meta"]["next_token"] = next_resp["meta"]["next_token"]
    else:  # done with pagination
        resp["meta"].pop("next_token")
    resp["data"].extend(next_resp["data"])
    return resp


def get_user_tweets(bearer_token, userid, since_id=None, tweetfields=None):
    """Get user tweets.

    Tweet fields are adjustable. Options include:
    attachments, author_id, context_annotations,
    conversation_id, created_at, entities, geo, id,
    in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
    possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
    source, text, and withheld

    If since_id isn't specified, only fetch the latest few tweets.
    """
    params = {"since_id": since_id, "max_results": 5}
    if tweetfields is None:
        params["tweet.fields"] = "created_at"
    else:
        params = {"tweet.fields": ",".join(tweetfields)}
    url = f"https://api.twitter.com/2/users/{userid}/tweets"
    resp = apiv2.connect_to_endpoint(bearer_token, url, params=params)
    if since_id:
        while "next_token" in resp["meta"]:
            params["pagination_token"] = resp["meta"]["next_token"]
            next_resp = apiv2.connect_to_endpoint(
                bearer_token, url, params=params
            )
            resp = consolidate_pagination_responses(resp, next_resp)
    return resp["meta"], resp.get("data")  # 'data' is missing when 0 count
