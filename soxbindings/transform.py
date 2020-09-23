from sox import Transformer as BaseTransformer
from sox.transform import ENCODINGS_MAPPING

from sox.log import logger
from .sox_cli import sox
from .audio import get_info
import numpy as np

class Transformer(BaseTransformer):
    def build(self, input_filepath=None, output_filepath=None,
              input_array=None, sample_rate_in=None,
              extra_args=None, return_output=False):
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
