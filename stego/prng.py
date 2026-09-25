import hashlib


def seed_from_key(stego_key: str) -> int:
    digest = hashlib.sha256(stego_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class LCG:

    MOD = 2 ** 64
    A = 6364136223846793005
    C = 1442695040888963407

    def __init__(self, seed: int):
        self.state = seed % self.MOD

    def next(self) -> int:
        self.state = (self.A * self.state + self.C) % self.MOD
        return self.state


def permutation(n: int, stego_key: str):

    rng = LCG(seed_from_key(stego_key))
    idx = list(range(n))
    # Fisher-Yates shuffle
    for i in range(n - 1, 0, -1):
        j = rng.next() % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    return idx
