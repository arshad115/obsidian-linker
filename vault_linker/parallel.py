import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable, List, TypeVar

from tqdm import tqdm

T = TypeVar('T')
R = TypeVar('R')


def resolve_worker_count(jobs: int) -> int:
    if jobs < 0:
        raise ValueError("jobs must be >= 0")
    if jobs == 0:
        return min(32, os.cpu_count() or 4)
    return jobs


def map_parallel(
    items: Iterable[T],
    worker: Callable[[T], R],
    *,
    jobs: int,
    show_progress: bool,
    desc: str,
) -> List[R]:
    item_list = list(items)
    if not item_list:
        return []

    if jobs <= 1:
        return [worker(item) for item in item_list]

    results: List[R] = []
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(worker, item) for item in item_list]
        iterator = as_completed(futures)
        if show_progress:
            iterator = tqdm(iterator, total=len(futures), desc=desc)
        for future in iterator:
            results.append(future.result())
    return results
