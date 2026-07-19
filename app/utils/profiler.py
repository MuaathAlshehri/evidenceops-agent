from time import perf_counter
from contextlib import contextmanager


class Profiler:
    def __init__(self):
        self.results = {}

    @contextmanager
    def measure(self, name: str):
        start = perf_counter()
        try:
            yield
        finally:
            elapsed = perf_counter() - start
            self.results.setdefault(name, []).append(elapsed)

    def report(self):
        print("\n" + "=" * 60)
        print("PERFORMANCE REPORT")
        print("=" * 60)

        total = 0

        for name, values in self.results.items():
            avg = sum(values) / len(values)
            total += sum(values)

            print(
                f"{name:<30}"
                f" calls={len(values):<3}"
                f" avg={avg:.3f}s"
                f" total={sum(values):.3f}s"
            )

        print("-" * 60)
        print(f"Total measured time: {total:.3f}s")
        print("=" * 60)


profiler = Profiler()