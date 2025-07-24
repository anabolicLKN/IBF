import math
import random
import hashlib
import binascii
from collections import deque


# Cantor pairing functions

def cantor_pair(u, v):
    return (u + v) * (u + v + 1) // 2 + v

def cantor_unpair(z):
    s = math.isqrt(8 * z + 1)
    w = (s - 1) // 2
    t = w * (w + 1) // 2
    v = z - t
    u = w - v
    return u, v

class InvertibleBloomFilter:
    """Simple IBF implementation without external dependencies."""
    def __init__(self, items_count, mem_fac, get_digest):
        self.size = max(1, math.ceil(items_count * mem_fac))
        self.hash_count = max(2, int(self.size / items_count * math.log(2) + 0.5))
        self.count_array = [0] * self.size
        self.idSum_array = [0] * self.size
        self.hashSum_array = [0] * self.size
        self.get_digest = get_digest

    def hashsum_hash(self, z):
        return binascii.crc32(str(z).encode('utf-8'))

    def _hash_indices(self, z):
        for i in range(self.hash_count):
            h1 = self.get_digest(str(z), i)
            h2 = int(hashlib.sha256(f"{z}-{i}".encode('utf-8')).hexdigest(), 16)
            yield (h1 + h2) % self.size

    def encode(self, edge):
        u, v = edge
        if u > v:
            u, v = v, u
        z = cantor_pair(u, v)
        h = self.hashsum_hash(z)
        for pos in self._hash_indices(z):
            self.count_array[pos] += 1
            self.idSum_array[pos] ^= z
            self.hashSum_array[pos] ^= h

    def delete(self, edge):
        u, v = edge
        if u > v:
            u, v = v, u
        z = cantor_pair(u, v)
        h = self.hashsum_hash(z)
        for pos in self._hash_indices(z):
            self.count_array[pos] -= 1
            self.idSum_array[pos] ^= z
            self.hashSum_array[pos] ^= h

    def subtract(self, other):
        for i in range(self.size):
            self.count_array[i] -= other.count_array[i]
            self.idSum_array[i] ^= other.idSum_array[i]
            self.hashSum_array[i] ^= other.hashSum_array[i]

    def decode(self):
        result = []
        pure = deque(i for i in range(self.size) if abs(self.count_array[i]) == 1)
        while pure:
            idx = pure.popleft()
            c = self.count_array[idx]
            if abs(c) != 1:
                continue
            z = self.idSum_array[idx]
            if self.hashSum_array[idx] != self.hashsum_hash(z):
                continue
            u, v = cantor_unpair(z)
            result.append((u, v))
            h = self.hashsum_hash(z)
            for pos in self._hash_indices(z):
                self.count_array[pos] -= c
                self.idSum_array[pos] ^= z
                self.hashSum_array[pos] ^= h
                if abs(self.count_array[pos]) == 1:
                    pure.append(pos)
        if any(self.count_array):
            return None
        return result

def write_edges(path, edges):
    with open(path, "w") as f:
        for u, v in sorted(edges):
            f.write(f"{u} {v}\n")


def load_edges(path):
    edges = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            u, v = map(int, line.split())
            if u > v:
                u, v = v, u
            edges.add((u, v))
    return edges


def generate_edge_files():
    rng = random.Random(0)
    nodes = list(range(1, 21))

    all_edges = [(u, v) for i, u in enumerate(nodes) for v in nodes[i + 1 :]]
    edges_A = set(rng.sample(all_edges, 60))

    change = max(1, int(len(edges_A) * 0.05))
    removed = set(rng.sample(list(edges_A), change))
    remaining = edges_A - removed

    available = list(set(all_edges) - edges_A)
    added = set(rng.sample(available, change))
    edges_B = remaining | added

    write_edges("graph_A.edges", edges_A)
    write_edges("graph_B.edges", edges_B)

    return "graph_A.edges", "graph_B.edges"

if __name__ == "__main__":
    a_path, b_path = generate_edge_files()

    A = load_edges(a_path)
    B = load_edges(b_path)

    diff_size = len(A ^ B)

    get_digest = lambda s, i: int(hashlib.sha256(f"{i}:{s}".encode("utf-8")).hexdigest(), 16)
    ibf_A = InvertibleBloomFilter(diff_size, 2.0, get_digest)
    ibf_B = InvertibleBloomFilter(diff_size, 2.0, get_digest)

    for e in A:
        ibf_A.encode(e)
    for e in B:
        ibf_B.encode(e)

    ibf_A.subtract(ibf_B)
    recovered = ibf_A.decode()

    if recovered is None:
        raise RuntimeError("Decoding failed")

    with open("decoded_edges.txt", "w") as f:
        for u, v in recovered:
            f.write(f"{u} {v}\n")
