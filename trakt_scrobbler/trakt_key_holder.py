import base64

ID = b'YWIwMTMzYTIzNjViMmM2NGQ3MGZkMmFkZjNjN2U3NzVhNDEzMTQ3MWI1NjM0MDkzMzMzNWFmMWI5NDc4NWEzYQ=='
SECRET = b'YjU3NGFjZDU4NTczMTBmY2RjMWUxOTVjNTk1Mzc5NWZjNjFhMWQ4OWQ2OWZlYzE2NDk2MjRkNTRjYjY2NjIyMg=='


def get_id():
    return base64.b64decode(ID).decode('utf-8')


def get_secret():
    return base64.b64decode(SECRET).decode('utf-8')
