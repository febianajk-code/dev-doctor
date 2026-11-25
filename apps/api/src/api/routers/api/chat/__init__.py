"""Grup chat: endpoint agent dev-doctor untuk pengunjung website.

Anonim secara sengaja: request membawa API key gateway milik pengunjung, sehingga
server tidak menyimpan kredensial apa pun.
"""

from fastapi import params

segment = "chat"

dependencies: tuple[params.Depends, ...] = ()
