import numpy as np

MAX_NUM_EFFECTS_ARGS = 20

def get_available_effects():
    from . import _soxbindings
    return _soxbindings.get_effect_names()

def initialize_sox():
    from . import _soxbindings
    return _soxbindings.sox_init()

def quit_sox():
    from . import _soxbindings
    return _soxbindings.sox_quit()

def build_flow_effects(input_data, sample_rate, sox_effects_chain, 
                       precision=16, target_signal_info=None, 
                       target_encoding=None):
    from . import _soxbindings
    initialize_sox()

    input_signal_info = _soxbindings.sox_signalinfo_t()
    input_signal_info.rate = float(sample_rate)
    input_signal_info.channels = (
        1 if len(input_data.shape) == 1 else input_data.shape[-1]
    )
    input_signal_info.length = input_data.size
    input_signal_info.precision = precision
    
    input_data = input_data.reshape(-1)
    input_data = input_data * (1 << 31)
    input_data = input_data.astype(np.int32)

    sample_rate, num_channels, data = _soxbindings.build_flow_effects(
        input_data, input_signal_info,
        target_signal_info, target_encoding, 
        sox_effects_chain, MAX_NUM_EFFECTS_ARGS
    )
    data = data.reshape(-1, num_channels)
    data = data / (1 << 31)

    quit_sox()
    return data, sample_rate

def SoxEffect():
    r"""Create an object for passing sox effect information between python and c++
    Returns:
        SoxEffect: An object with the following attributes: ename (str) which is the
        name of effect, and eopts (List[str]) which is a list of effect options.
    """

    from . import _soxbindings
    return _soxbindings.SoxEffect()