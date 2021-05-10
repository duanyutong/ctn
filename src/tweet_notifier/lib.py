"""Wrappers of APIv2 to perform certain twitter functions."""

import os

from . import apiv2


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
    """
    Tweet fields are adjustable.
    Options include:
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
    return resp["meta"], resp["data"]
