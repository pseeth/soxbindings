from multiprocessing.dummy import Pool as ThreadPool
import numpy as np
import soxbindings as sox
from soxbindings import sox_context

@sox_context()
def test_multithreading():
    y1 = np.zeros((4000, 1))
    y2 = np.zeros((3000, 1))

    def do_transform(y):
        tfm = sox.Transformer()
        tfm.vol(0.5)
        y_out = tfm.build_array(input_array=y, sample_rate_in=1000)
        return y_out

    # single thread
    single_thread = []
    for y in [y1, y2]:
        res = do_transform(y)
        single_thread.append(res)

    # multithread
    pool = ThreadPool(2)
    multi_thread = pool.map(do_transform, [y1, y2])

    for a1, a2 in zip(single_thread, multi_thread):
        assert np.allclose(a1, a2)

def test_multithreading_with_context_block():
    y1 = np.zeros((4000, 1))
    y2 = np.zeros((3000, 1))

    def do_transform(y):
        tfm = sox.Transformer()
        tfm.vol(0.5)
        y_out = tfm.build_array(input_array=y, sample_rate_in=1000)
        return y_out

    # single thread
    single_thread = []
    for y in [y1, y2]:
        res = do_transform(y)
        single_thread.append(res)

    # multithread
    pool = ThreadPool(2)
    with sox_context():
        multi_thread = pool.map(do_transform, [y1, y2]) 
        for a1, a2 in zip(single_thread, multi_thread):
            assert np.allclose(a1, a2)

if __name__ == "__main__":
    test_multithreading()
    