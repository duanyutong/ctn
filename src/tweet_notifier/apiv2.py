"""Lowest level functions that invoke twitter API v2."""

import requests


def create_headers(bearer_token):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    return headers


def connect_to_endpoint(bearer_token, url, params=None):
    response = requests.request(
        "GET", url, headers=create_headers(bearer_token), params=params
    )
    if response.status_code != 200:
        raise Exception(
            f"Request returned error {response.status_code}: {response.text}"
        )
    return response.json()
