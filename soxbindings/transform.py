from sox import Transformer as BaseTransformer
from sox.transform import ENCODINGS_MAPPING

# Need a hack for machines where the sox binary doesn't exist.
# But SoxBindings will still work.
import sox as pysox
pysox.transform.VALID_FORMATS = [
    '8svx', 'aif', 'aifc', 'aiff', 'aiffc', 'al', 'amb', 'au', 
    'avr', 'caf', 'cdda', 'cdr', 'cvs', 'cvsd', 'cvu', 'dat', 
    'dvms', 'f32', 'f4', 'f64', 'f8', 'fap', 'flac', 'fssd', 
    'gsm', 'gsrt', 'hcom', 'htk', 'ima', 'ircam', 'la', 'lpc', 
    'lpc10', 'lu', 'mat', 'mat4', 'mat5', 'maud', 'mp2', 'mp3', 
    'nist', 'ogg', 'opus', 'paf', 'prc', 'pvf', 'raw', 's1', 
    's16', 's2', 's24', 's3', 's32', 's4', 's8', 'sb', 'sd2', 
    'sds', 'sf', 'sl', 'sln', 'smp', 'snd', 'sndfile', 'sndr', 
    'sndt', 'sou', 'sox', 'sph', 'sw', 'txw', 'u1', 'u16', 'u2', 
    'u24', 'u3', 'u32', 'u4', 'u8', 'ub', 'ul', 'uw', 'vms', 'voc', 
    'vorbis', 'vox', 'w64', 'wav', 'wavpcm', 'wve', 'xa', 'xi'
]

from sox.log import logger
from .sox_cli import sox
from .audio import get_info
import numpy as np

class Transformer(BaseTransformer):
    def build(self, input_filepath=None, output_filepath=None,
              input_array=None, sample_rate_in=None,
              extra_args=None, return_output=False):
        
        if input_filepath is not None:
            channels = get_info(input_filepath)[0].channels
            self.set_input_format(
                channels=channels
            )
        input_format, input_filepath = self._parse_inputs(
            input_filepath, input_array, sample_rate_in
        )

        if output_filepath is None:
            raise ValueError("output_filepath is not specified!")

        args = []
        args.extend(self.globals)
        args.extend(self._input_format_args(input_format))
        args.append(input_filepath)
        args.extend(self._output_format_args(self.output_format))
        args.append(output_filepath)
        args.extend(self.effects)

        if extra_args is not None:
            if not isinstance(extra_args, list):
                raise ValueError("extra_args must be a list.")
            args.extend(extra_args)
        output_audio, sample_rate_out = sox(args, input_array, sample_rate_in)
        return output_audio, sample_rate_out

    def build_array(self, input_filepath=None, input_array=None,
                    sample_rate_in=None, extra_args=None):
        output_audio, sample_rate_out = self.build(input_filepath=input_filepath, 
            output_filepath='-', input_array=input_array, sample_rate_in=sample_rate_in, 
            extra_args=extra_args)
        return output_audio
