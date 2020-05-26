import numpy as np

def read(audio_path, nframes=0, offset=0, signal_info=None, 
         encoding_info=None, file_type=None):
    from . import _soxbindings
    sample_rate, num_channels, data = _soxbindings.read_audio_file(
        audio_path, nframes, offset, signal_info, 
        encoding_info, file_type)
    data = data.reshape(-1, num_channels)
    data = data / (1 << 31)
    return data, sample_rate

def write(audio_path, data, sample_rate, 
          precision=16, encoding_info=None):
    from . import _soxbindings
    si = _soxbindings.sox_signalinfo_t()

    si.rate = float(sample_rate)
    si.channels = 1 if len(data.shape) == 1 else data.shape[-1]
    si.length = data.size
    si.precision = precision
    file_type = None

    data = data * (1 << 31)
    data = data.astype(np.int32)

    _soxbindings.write_audio_file(
        audio_path, data, si, encoding_info, file_type
    )

def get_info(audio_path):
    from . import _soxbindings
    return _soxbindings.get_info(audio_path)