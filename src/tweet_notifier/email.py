import inspect
import itertools
import logging
import os
import smtplib
import ssl

SUBJECT_TWEET_LIMIT = 140
# Create a secure SSL context
SSL_CONTEXT = ssl.create_default_context()


def get_smtp_config():
    config = {
        "host": os.getenv("SMTP_HOST"),
        "port": os.getenv("SMTP_PORT"),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
    }

    if not all(config.values()):
        raise ValueError("Complete SMTP config not found in environment.")
    return config


def create_from_tweet(username, tweet):
    """TODO: support different display timezones."""
    if len(tweet["text"]) < SUBJECT_TWEET_LIMIT:
        digest = tweet["text"]
    else:
        digest = f"{tweet['text'][:SUBJECT_TWEET_LIMIT]}..."
    msg = f"""\
    Subject: New tweet from @{username}: {digest}

    @{username}: {tweet['text']}
    https://twitter.com/{username}/status/{tweet['id']}
    {tweet['created_at']}
    """ + (
        "\nYou are receiving this email because "
        "you are subscribed to the latest updates. "
        'To unsubscribe, reply with "unsubscribe"'
    )
    return inspect.cleandoc(msg)


def send_emails(msgs, receivers, host, port, username, password):
    logger = logging.getLogger("TweetNotifier")
    logger.info("Authenticating SMTPs...")
    with smtplib.SMTP_SSL(host, port, context=SSL_CONTEXT) as server:
        server.login(username, password)
        i, n_total = 0, len(receivers) * len(msgs)
        for receiver, msg in itertools.product(receivers, msgs):
            i += 1
            logger.info(f"{i}/{n_total} sending email to {receiver}...")
            server.sendmail(username, receiver, msg)
    logger.info(f"Done sending {n_total} emails")
