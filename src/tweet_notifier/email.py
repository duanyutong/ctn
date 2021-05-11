import inspect
import itertools
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

SUBJECT_TWEET_LIMIT = 140
# Create a secure SSL context
SSL_CONTEXT = ssl.create_default_context()


def get_smtp_config():
    address = os.environ["SMTP_ADDRESS"]
    config = {
        "address": address,
        "host": os.getenv("SMTP_HOST"),
        "port": os.getenv("SMTP_PORT"),
        "username": address.split("@")[0],
        "password": os.getenv("SMTP_PASSWORD"),
    }

    if not all(config.values()):
        raise ValueError("Complete SMTP config not found in environment.")
    return config


def create_from_tweet(username, tweet, address, receiver):
    """TODO: support different display timezones."""
    digest = " ".join(tweet["text"].splitlines())
    if len(tweet["text"]) > SUBJECT_TWEET_LIMIT:
        digest = f"{digest[:SUBJECT_TWEET_LIMIT]}..."
    msg = EmailMessage()
    msg["Subject"] = f"New tweet from @{username}: {digest}"
    msg["From"] = f"TweetNotifier <{address}>"
    msg["To"] = receiver
    content = f"""\
    @{username}: {tweet['text']}

    ---

    https://twitter.com/{username}/status/{tweet['id']}
    {tweet['created_at']}

    ---

    """ + (
        "You are receiving this email because "
        "you are subscribed to the latest updates. "
        'To unsubscribe, reply with "unsubscribe".'
    )
    msg.set_content(inspect.cleandoc(content))
    return msg


def send_emails(
    twitter_username,
    tweets,
    receivers,
    address,
    host,
    port,
    username,
    password,
):
    logger = logging.getLogger("TweetNotifier")
    logger.info("Authenticating SMTPs...")
    with smtplib.SMTP_SSL(host, port, context=SSL_CONTEXT) as server:
        server.login(username, password)
        i, n_total = 0, len(receivers) * len(tweets)
        for receiver, tweet in itertools.product(receivers, tweets):
            # compose email on the fly
            i += 1
            msg = create_from_tweet(twitter_username, tweet, address, receiver)
            logger.info(f"{i}/{n_total} sending email to {receiver}...")
            server.send_message(msg)
    logger.info(f"Done sending {n_total} emails")
