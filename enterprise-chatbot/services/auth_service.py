import json


def is_allowed_user(username):

    with open("config/users.json", "r") as f:
        users = json.load(f)["users"]

    return username in users


def is_admin(username):

    with open("config/admins.json", "r") as f:
        admins = json.load(f)["admins"]

    return username in admins
