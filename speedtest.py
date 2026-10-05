import dataclasses
import enum
import random
from argparse import ArgumentParser
import requests
import time
import statistics

class ChunkSize(enum.Enum):
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024

    KBI = 1000
    MBI = 1000000
    GBI = 1000000000


@dataclasses.dataclass
class SpeedtestResult:
    time: float
    size: int
    chunk_size: ChunkSize

    @property
    def speed(self):
        return self.size / self.time / self.chunk_size.value

    def __str__(self):
        return (
            f"{self.time:.3f} sec, "
            f"{self.size / self.chunk_size.value:.2f} "
            f"{self.chunk_size.name}, "
            f"{self.speed:.2f} {self.chunk_size.name}/s"
        )


def _speedtest_url(session: requests.Session, url: str, chunk_size: ChunkSize) -> SpeedtestResult:
    start = time.perf_counter()

    url = url if "://" in url else f"https://{url}"

    response = session.get(url, stream=True, timeout=60)
    response.raise_for_status()

    size = 0

    for chunk in response.iter_content(chunk_size.value):
        size += len(chunk)

    elapsed = time.perf_counter() - start

    return SpeedtestResult(
        elapsed,
        size,
        chunk_size,
    )

def _speedtest(
        url: str,
        retries: int = 10,
        delay: float = 0.5,
        jitter: float = 0.5,
        chunk_size: ChunkSize = ChunkSize.MB,
):
    results: list[SpeedtestResult] = []

    with requests.Session() as session:
        for i in range(retries):
            print(f'Request {i + 1}/{retries}...', end=" ", flush=True)
            retry_time = delay + random.random() * jitter
            try:
                result = _speedtest_url(session, url, chunk_size)
                print(result)
                results.append(result)
            except Exception as e:
                print(f'Has error in speedtest {e}, retry in {retry_time}', flush=True)
            time.sleep(retry_time)

    if not results:
        print("All requests failed, no statistics to show.")
        return

    avg_time = statistics.mean(r.time for r in results)
    avg_size = statistics.mean(r.size for r in results)
    avg_speed = statistics.mean(r.speed for r in results)
    all_sizes = sum(r.size for r in results)
    all_times = sum(r.time for r in results)
    total_speed = all_sizes / all_times / chunk_size.value

    print()
    print("========== Result ==========")
    print(f"Average time: {avg_time:.3f} sec")
    print(f"Average size: {avg_size / chunk_size.value:.2f} {chunk_size.name}")
    print(f"Average speed: {avg_speed:.2f} {chunk_size.name}/s")
    print(f"Total size: {all_sizes / chunk_size.value:.2f} {chunk_size.name}")
    print(f"Total speed: {total_speed:.2f} {chunk_size.name}/s")

def main():
    parser = ArgumentParser()
    parser.add_argument("-u", "--url", help="Url to test", type=str, required=True)
    parser.add_argument("-r", "--retries", help="Number of attempts", type=int, default=10, required=False)
    parser.add_argument("-d", "--delay", help="Delay between each request", type=float, default=0.5, required=False)
    parser.add_argument("-j", "--jitter", help="Jitter", type=float, default=0.5, required=False)
    parser.add_argument('-c','--chunk-size', help='Chunk size', type=str, default='MB', required=False)
    args = parser.parse_args()

    url = args.url
    retries = args.retries
    delay = args.delay
    jitter = args.jitter
    try:
        chunk_size = ChunkSize[args.chunk_size.upper()]
    except KeyError:
        print('Invalid chunk size, valid are: ', [c.name for c in ChunkSize], flush=True)
        print('Switch to default chunk size: MB', flush=True)
        chunk_size = ChunkSize.MB

    _speedtest(url, retries, delay, jitter, chunk_size)

if __name__ == "__main__":
    main()