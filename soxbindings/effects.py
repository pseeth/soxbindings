import numpy as np
from contextlib import contextmanager

MAX_NUM_EFFECTS_ARGS = 20
SOX_UNSPEC = 0

def get_available_effects():
    from . import _soxbindings
    return _soxbindings.get_effect_names()

def initialize_sox():
    from . import _soxbindings
    return _soxbindings.sox_init()

def quit_sox():
    from . import _soxbindings
    return _soxbindings.sox_quit()

@contextmanager
def sox_context_manager():
    try:
        yield initialize_sox()
    finally:
        # Code to release resource, e.g.:
        quit_sox()

@sox_context_manager()
def build_flow_effects(input_data, sample_rate_in, sox_effects_chain, 
                       in_channels=None, in_precision=16, out_channels=None,
                       sample_rate_out=None, out_precision=None):
    from . import _soxbindings

    input_signal_info = _soxbindings.sox_signalinfo_t()
    input_signal_info.rate = float(sample_rate_in)
    if in_channels is None:
        in_channels = (
            1 if len(input_data.shape) == 1 else input_data.shape[-1]
        )
    input_signal_info.channels = in_channels
    input_signal_info.length = input_data.size
    input_signal_info.precision = in_precision

    if sample_rate_out is None:
        sample_rate_out = sample_rate_in
    if out_precision is None:
        out_precision = in_precision
    if out_channels is None:
        out_channels = in_channels

    target_signal_info = _soxbindings.sox_signalinfo_t()
    target_signal_info.rate = float(sample_rate_out)
    target_signal_info.channels = out_channels
    target_signal_info.length = SOX_UNSPEC
    target_signal_info.precision = out_precision

    target_encoding = _soxbindings.sox_encodinginfo_t()
    target_encoding.encoding = _soxbindings.SOX_ENCODING_SIGN2
    target_encoding.bits_per_sample = out_precision
    target_encoding.compression = 0.0
    target_encoding.reverse_bytes = _soxbindings.sox_option_default
    target_encoding.reverse_nibbles = _soxbindings.sox_option_default
    target_encoding.reverse_bits = _soxbindings.sox_option_default
    target_encoding.opposite_endian = _soxbindings.sox_false
    
    input_data = input_data.reshape(-1)
    input_data = input_data * (1 << 31)
    input_data = input_data.astype(np.int32)

    sample_rate, num_channels, data = _soxbindings.build_flow_effects(
        input_data, input_signal_info,
        target_signal_info, target_encoding, 
        sox_effects_chain, MAX_NUM_EFFECTS_ARGS
    )
    data = data.reshape(-1, out_channels)
    data = data / (1 << 31)
    return data, sample_rate

def SoxEffect():
    r"""Create an object for passing sox effect information between python and c++
    Returns:
        SoxEffect: An object with the following attributes: ename (str) which is the
        name of effect, and eopts (List[str]) which is a list of effect options.
    """

    from . import _soxbindings
    return _soxbindings.SoxEffect()