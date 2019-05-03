import subprocess

import keyring
from keyring.backend import KeyringBackend


class PasswordstoreKeyring(KeyringBackend):
    priority = 1

    def get_password(self, servicename, username):
        result = subprocess.run(
            ["pass", "show", servicename.rstrip("/")], stdout=subprocess.PIPE
        )
        if result.returncode != 0:
            return None
        password, login, *other = result.stdout.decode("utf-8").split("\n")
        if login != f"login: {username}":
            return None
        return password

    def set_password(self, servicename, username, password):
        subprocess.run(
            ["pass", "insert", "--force", "--multiline", servicename],
            stdout=subprocess.PIPE,
            input=f"{password}\nlogin: {username}".encode("utf-8"),
            check=True,
        )

    def delete_password(self, servicename, username, password):
        pass


def default(lancet, config_section):
    return keyring.get_keyring()


def passwordstore(lancet, config_section):
    return PasswordstoreKeyring()
