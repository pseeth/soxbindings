#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <sox.h>
#include <sstream>

namespace py = pybind11;

/// Helper struct to safely close the sox_format_t descriptor.
/// from torchaudio
struct SoxDescriptor {
  explicit SoxDescriptor(sox_format_t* fd) noexcept : fd_(fd) {}
  SoxDescriptor(const SoxDescriptor& other) = delete;
  SoxDescriptor(SoxDescriptor&& other) = delete;
  SoxDescriptor& operator=(const SoxDescriptor& other) = delete;
  SoxDescriptor& operator=(SoxDescriptor&& other) = delete;
  ~SoxDescriptor() {
    if (fd_ != nullptr) {
      sox_close(fd_);
    }
  }
  sox_format_t* operator->() noexcept {
    return fd_;
  }
  sox_format_t* get() noexcept {
    return fd_;
  }

 private:
  sox_format_t* fd_;
};

/// Helper struct for holding Sox effects
struct SoxEffect {
  SoxEffect() : effect_name(""), effect_args({""})  { }
  std::string effect_name;
  std::vector<std::string> effect_args;
};

int64_t write_audio(SoxDescriptor& fd, py::array data) {
  std::vector<sox_sample_t> buffer(data.size());
  const sox_sample_t* data_ptr = static_cast<const sox_sample_t*>(data.data());
  std::copy(data_ptr, data_ptr + data.size(), buffer.begin());

  const auto samples_written =
      sox_write(fd.get(), buffer.data(), buffer.size());
  return samples_written;
}

void write_audio_file(
    const std::string& file_name,
    const py::array& data,
    sox_signalinfo_t* si,
    sox_encodinginfo_t* ei,
    const char* file_type) {

#if SOX_LIB_VERSION_CODE >= 918272 // >= 14.3.0
  si->mult = nullptr;
#endif

  SoxDescriptor fd(sox_open_write(
      file_name.c_str(),
      si,
      ei,
      file_type,
      /*oob=*/nullptr,
      /*overwrite=*/nullptr));

  if (fd.get() == nullptr) {
    throw std::runtime_error(
        "Error writing audio file: could not open file for writing");
  }

  const auto samples_written = write_audio(fd, data);

  if (samples_written != data.size()) {
    throw std::runtime_error(
        "Error writing audio file: could not write entire buffer");
  }
}

py::array read_audio(
    SoxDescriptor& fd,
    int64_t buffer_length) {
  std::vector<sox_sample_t> buffer(buffer_length);

  int number_of_channels = fd->signal.channels;
  const int64_t samples_read = sox_read(fd.get(), buffer.data(), buffer_length);
  if (samples_read == 0) {
    throw std::runtime_error(
        "Error reading audio file: empty file or read failed in sox_read");
  }
  return py::array(buffer.size(), buffer.data());
}

std::tuple<int, int, py::array> read_audio_file(
    const std::string& file_name,
    int64_t nframes,
    int64_t offset,
    sox_signalinfo_t* si,
    sox_encodinginfo_t* ei,
    const char* ft) {

  SoxDescriptor fd(sox_open_read(file_name.c_str(), si, ei, ft));
  if (fd.get() == nullptr) {
    throw std::runtime_error("Error opening audio file");
  }

  // signal info

  const int number_of_channels = fd->signal.channels;
  const int sample_rate = fd->signal.rate;
  const int64_t total_length = fd->signal.length;

  // multiply offset and number of frames by number of channels
  offset *= number_of_channels;
  nframes *= number_of_channels;

  if (total_length == 0) {
    throw std::runtime_error("Error reading audio file: unknown length");
  }
  if (offset > total_length) {
    throw std::runtime_error("Offset past EOF");
  }

  // calculate buffer length
  int64_t buffer_length = total_length;
  if (offset > 0) {
      buffer_length -= offset;
  }
  if (nframes > 0 && buffer_length > nframes) {
      buffer_length = nframes;
  }

  // seek to offset point before reading data
  if (sox_seek(fd.get(), offset, 0) == SOX_EOF) {
    throw std::runtime_error("sox_seek reached EOF, try reducing offset or num_samples");
  }

  return std::make_tuple(sample_rate, number_of_channels, read_audio(fd, buffer_length));
}

std::vector<std::string> get_effect_names() {
  sox_effect_fn_t const * fns = sox_get_effect_fns();
  std::vector<std::string> sv;
  for(int i = 0; fns[i]; ++i) {
    const sox_effect_handler_t *eh = fns[i] ();
    if(eh && eh->name)
      sv.push_back(eh->name);
  }
  return sv;
}

std::tuple<sox_signalinfo_t, sox_encodinginfo_t> get_info(
    const std::string& file_name
  ) {
  SoxDescriptor fd(sox_open_read(
      file_name.c_str(),
      /*signal=*/nullptr,
      /*encoding=*/nullptr,
      /*filetype=*/nullptr));
  if (fd.get() == nullptr) {
    throw std::runtime_error("Error opening audio file");
  }
  return std::make_tuple(fd->signal, fd->encoding);
}

std::tuple<int, int, py::array> build_flow_effects(
  py::array input_data,
  sox_signalinfo_t* input_signal,
  sox_signalinfo_t* target_signal,
  sox_encodinginfo_t* target_encoding,
  std::vector<SoxEffect> effects,
  int max_num_effect_args) {

  /* This function builds an effects flow and puts the results into a tensor.
     It can also be used to re-encode audio using any of the available encoding
     options in SoX including sample rate and channel re-encoding.              */

  // open input
  
#ifdef __APPLE__
  char tmp_in_name[] = "/tmp/fileXXXXXX.wav";
  int tmp_in_fd = mkstemp(tmp_in_name);
  close(tmp_in_fd);

  write_audio_file(tmp_in_name, input_data, input_signal, NULL, NULL);
  sox_format_t* input = sox_open_read(tmp_in_name, nullptr, nullptr, nullptr);

#else
  std::vector<sox_sample_t> input_buffer(input_signal->length);

  const sox_sample_t* data_ptr = static_cast<const sox_sample_t*>(input_data.data());
  std::copy(data_ptr, data_ptr + input_signal->length, input_buffer.begin());

  size_t buffer_size = sizeof(input_buffer[0]) * input_buffer.size();

  sox_format_t* input = sox_open_mem_read(input_buffer.data(), buffer_size, 
                                          input_signal, NULL, "s32");
#endif
  if (input == nullptr) {
    throw std::runtime_error("Error reading audio data.");
  }

  // only used if target signal or encoding are null
  sox_signalinfo_t empty_signal;
  sox_encodinginfo_t empty_encoding;

  // set signalinfo and encodinginfo if blank
  if(target_signal == nullptr) {
    target_signal = &empty_signal;
    target_signal->rate = input_signal->rate;
    target_signal->channels = input_signal->channels;
    target_signal->length = SOX_UNSPEC;
    target_signal->precision = input_signal->precision;
#if SOX_LIB_VERSION_CODE >= 918272 // >= 14.3.0
    target_signal->mult = nullptr;
#endif
  }
  if(target_encoding == nullptr) {
    target_encoding = &empty_encoding;
    target_encoding->encoding = SOX_ENCODING_SIGN2; // Sample format
    target_encoding->bits_per_sample = target_signal->precision; // Bits per sample
    target_encoding->compression = 0.0; // Compression factor
    target_encoding->reverse_bytes = sox_option_default; // Should bytes be reversed
    target_encoding->reverse_nibbles = sox_option_default; // Should nibbles be reversed
    target_encoding->reverse_bits = sox_option_default; // Should bits be reversed (pairs of bits?)
    target_encoding->opposite_endian = sox_false; // Reverse endianness
  }

  // check for rate or channels effect and change the output signalinfo accordingly
  for (SoxEffect effect : effects) {
    if (effect.effect_name == "rate") {
      target_signal->rate = std::stod(effect.effect_args.back());
    } else if (effect.effect_name == "channels") {
      target_signal->channels = std::stoi(effect.effect_args[0]);
    }
  }
  // create interm_signal for effects, intermediate steps change this in-place
  sox_signalinfo_t interm_signal = input->signal;

  // According to Mozilla Deepspeech sox_open_memstream_write doesn't work
  // with OSX
  
  char tmp_name[] = "/tmp/fileXXXXXX";
  int tmp_fd = mkstemp(tmp_name);
  close(tmp_fd);
  sox_format_t* output = sox_open_write(tmp_name, target_signal,
                                        target_encoding, "wav", nullptr, 
                                        nullptr);
  if (output == nullptr) {
    throw std::runtime_error("Error opening output memstream/temporary file");
  }
  // Setup the effects chain to decode/resample
  sox_effects_chain_t* chain =
    sox_create_effects_chain(&input->encoding, &output->encoding);

  sox_effect_t* e = sox_create_effect(sox_find_effect("input"));
  char* io_args[1];
  io_args[0] = (char*)input;
  sox_effect_options(e, 1, io_args);
  sox_add_effect(chain, e, &interm_signal, &input->signal);
  free(e);

  for(SoxEffect tae : effects) {
    if(tae.effect_name == "no_effects") break;
    e = sox_create_effect(sox_find_effect(tae.effect_name.c_str()));
    e->global_info->global_info->verbosity = 1;
    if(tae.effect_args[0] == "") {
      sox_effect_options(e, 0, nullptr);
    } else {
      int num_opts = tae.effect_args.size();
      char* sox_args[max_num_effect_args];
      for(std::vector<std::string>::size_type i = 0; i != tae.effect_args.size(); i++) {
        sox_args[i] = (char*) tae.effect_args[i].c_str();
      }
      if(sox_effect_options(e, num_opts, sox_args) != SOX_SUCCESS) {
        unlink(tmp_name);
        throw std::runtime_error("invalid effect options, see SoX docs for details");
      }
    }
    sox_add_effect(chain, e, &interm_signal, &output->signal);
    free(e);
  }

  e = sox_create_effect(sox_find_effect("output"));
  io_args[0] = (char*)output;
  sox_effect_options(e, 1, io_args);
  sox_add_effect(chain, e, &interm_signal, &output->signal);
  free(e);
  // Finally run the effects chain
  int err;
  err = sox_flow_effects(chain, nullptr, nullptr);
  sox_delete_effects_chain(chain);

  // Close sox handles, buffer does not get properly sized until these are closed
  sox_close(output);
  sox_close(input);

  std::tuple<int, int, py::array> output_audio_tuple;
  // Read the in-memory audio buffer or temp file that we just wrote.
  /*
     Temporary filetype must have a valid header.  Wav seems to work here while
     raw does not.  Certain effects like chorus caused strange behavior on the mac.
  */
  // read_audio_file reads the temporary file and returns the sr and otensor
  output_audio_tuple = read_audio_file(tmp_name, 0, 0, target_signal, 
                                       target_encoding, "wav");
  // delete temporary audio file
  unlink(tmp_name);

  // return sample rate, output tensor modified in-place
  return output_audio_tuple;
}

PYBIND11_MODULE(_soxbindings, m) {
    m.doc() = R"pbdoc(
        Pybind11 example plugin
        -----------------------

        .. currentmodule:: python_example

        .. autosummary::
           :toctree: _generate

           add
           subtract
    )pbdoc";
    
    m.def("sox_init", &sox_init, R"pbdoc(
      "Initialize sox."
    )pbdoc");

    m.def("sox_quit", &sox_quit, R"pbdoc(
      "Quit sox."
    )pbdoc");

    m.def(
      "read_audio_file",
      &read_audio_file,
      "Opens a decoding session for a file. Returned handle must be closed with " 
      "sox_close(). @returns The handle for the new session, or null on failure.");

    m.def(
      "write_audio_file",
      &write_audio_file,
      "Opens a decoding session for a file. Returned handle must be closed with " 
      "sox_close(). @returns The handle for the new session, or null on failure.");

    m.def(
      "get_info",
      &get_info,
      "Gets information about an audio file");

    m.def(
      "get_effect_names",
      &get_effect_names,
      "Gets list of available effects.");

    m.def(
      "build_flow_effects",
      &build_flow_effects,
      "Builds a flow of effects.");

    /*
    Class for holding effects.
    */
    py::class_<SoxEffect>(m, "SoxEffect")
        .def(py::init<>())
        .def("__repr__", [](const SoxEffect &self) {
          std::stringstream ss;
          std::string sep;
          ss << "SoxEffect (" << self.effect_name << " ,[";
          for(std::string s : self.effect_args) {
            ss << sep << "\"" << s << "\"";
            sep = ", ";
          }
          ss << "])\n";
          return ss.str();
        })
        .def_readwrite("effect_name", &SoxEffect::effect_name)
        .def_readwrite("effect_args", &SoxEffect::effect_args);

    /*
    Binding all of the enums and structs.
    */
    py::enum_<sox_error_t>(m, "sox_error_t")
        .value("SOX_SUCCESS", sox_error_t::SOX_SUCCESS) /**< Function succeeded = 0 */
        .value("SOX_EOF", sox_error_t::SOX_EOF)         /**< End Of File or other error = -1 */
        .value("SOX_EHDR", sox_error_t::SOX_EHDR)       /**< Invalid Audio Header = 2000 */
        .value("SOX_EFMT", sox_error_t::SOX_EFMT)       /**< Unsupported data format = 2001 */
        .value("SOX_ENOMEM", sox_error_t::SOX_ENOMEM)   /**< Can't alloc memory = 2002 */
        .value("SOX_EPERM", sox_error_t::SOX_EPERM)     /**< Operation not permitted = 2003 */
        .value("SOX_ENOTSUP", sox_error_t::SOX_ENOTSUP) /**< Operation not supported = 2004 */
        .value("SOX_EINVAL", sox_error_t::SOX_EINVAL)   /**< Invalid argument = 2005 */
        .export_values();
    
    py::enum_<sox_option_t>(m, "sox_option_t")
        .value("sox_option_no", sox_option_t::sox_option_no)
        .value("sox_option_yes", sox_option_t::sox_option_yes) 
        .value("sox_option_default", sox_option_t::sox_option_default)
        .export_values();

    py::enum_<sox_bool>(m, "sox_bool")
        .value("sox_bool_dummy", sox_bool::sox_bool_dummy)
        .value("sox_false", sox_bool::sox_false)
        .value("sox_true", sox_bool::sox_true)
        .export_values();

    py::class_<sox_encodinginfo_t>(m, "sox_encodinginfo_t")
       .def(py::init<>())
       .def("__repr__", [](const sox_encodinginfo_t &self) {
         std::stringstream ss;
         ss << "sox_encodinginfo_t {\n"
            << "  encoding-> " << self.encoding << "\n"
            << "  bits_per_sample-> " << self.bits_per_sample << "\n"
            << "  compression-> " << self.compression << "\n"
            << "  reverse_bytes-> " << self.reverse_bytes << "\n"
            << "  reverse_nibbles-> " << self.reverse_nibbles << "\n"
            << "  reverse_bits-> " << self.reverse_bits << "\n"
            << "  opposite_endian-> " << self.opposite_endian << "\n"
            << "}\n";
         return ss.str();
       })
       .def_readwrite("encoding", &sox_encodinginfo_t::encoding)
       .def_readwrite("bits_per_sample", &sox_encodinginfo_t::bits_per_sample)
       .def_readwrite("compression", &sox_encodinginfo_t::compression)
       .def_readwrite("reverse_bytes", &sox_encodinginfo_t::reverse_bytes)
       .def_readwrite("reverse_nibbles", &sox_encodinginfo_t::reverse_nibbles)
       .def_readwrite("reverse_bits", &sox_encodinginfo_t::reverse_bits)
       .def_readwrite("opposite_endian", &sox_encodinginfo_t::opposite_endian);

    py::enum_<sox_encoding_t>(m, "sox_encoding_t")
        .value("SOX_ENCODING_UNKNOWN", sox_encoding_t::SOX_ENCODING_UNKNOWN)
        .value("SOX_ENCODING_SIGN2", sox_encoding_t::SOX_ENCODING_SIGN2)
        .value("SOX_ENCODING_UNSIGNED", sox_encoding_t::SOX_ENCODING_UNSIGNED)
        .value("SOX_ENCODING_FLOAT", sox_encoding_t::SOX_ENCODING_FLOAT)
        .value("SOX_ENCODING_FLOAT_TEXT", sox_encoding_t::SOX_ENCODING_FLOAT_TEXT)
        .value("SOX_ENCODING_FLAC", sox_encoding_t::SOX_ENCODING_FLAC)
        .value("SOX_ENCODING_HCOM", sox_encoding_t::SOX_ENCODING_HCOM)
        .value("SOX_ENCODING_WAVPACK", sox_encoding_t::SOX_ENCODING_WAVPACK)
        .value("SOX_ENCODING_WAVPACKF", sox_encoding_t::SOX_ENCODING_WAVPACKF)
        .value("SOX_ENCODING_ULAW", sox_encoding_t::SOX_ENCODING_ULAW)
        .value("SOX_ENCODING_ALAW", sox_encoding_t::SOX_ENCODING_ALAW)
        .value("SOX_ENCODING_G721", sox_encoding_t::SOX_ENCODING_G721)
        .value("SOX_ENCODING_G723", sox_encoding_t::SOX_ENCODING_G723)
        .value("SOX_ENCODING_CL_ADPCM", sox_encoding_t::SOX_ENCODING_CL_ADPCM)
        .value("SOX_ENCODING_CL_ADPCM16", sox_encoding_t::SOX_ENCODING_CL_ADPCM16)
        .value("SOX_ENCODING_MS_ADPCM", sox_encoding_t::SOX_ENCODING_MS_ADPCM)
        .value("SOX_ENCODING_IMA_ADPCM", sox_encoding_t::SOX_ENCODING_IMA_ADPCM)
        .value("SOX_ENCODING_OKI_ADPCM", sox_encoding_t::SOX_ENCODING_OKI_ADPCM)
        .value("SOX_ENCODING_DPCM", sox_encoding_t::SOX_ENCODING_DPCM)
        .value("SOX_ENCODING_DWVW", sox_encoding_t::SOX_ENCODING_DWVW)
        .value("SOX_ENCODING_DWVWN", sox_encoding_t::SOX_ENCODING_DWVWN)
        .value("SOX_ENCODING_GSM", sox_encoding_t::SOX_ENCODING_GSM)
        .value("SOX_ENCODING_MP3", sox_encoding_t::SOX_ENCODING_MP3)
        .value("SOX_ENCODING_VORBIS", sox_encoding_t::SOX_ENCODING_VORBIS)
        .value("SOX_ENCODING_AMR_WB", sox_encoding_t::SOX_ENCODING_AMR_WB)
        .value("SOX_ENCODING_AMR_NB", sox_encoding_t::SOX_ENCODING_AMR_NB)
        .value("SOX_ENCODING_LPC10", sox_encoding_t::SOX_ENCODING_LPC10)
        //.value("SOX_ENCODING_OPUS", sox_encoding_t::SOX_ENCODING_OPUS)  // creates a compile error
        .value("SOX_ENCODINGS", sox_encoding_t::SOX_ENCODINGS)
        .export_values();

    py::class_<sox_signalinfo_t>(m, "sox_signalinfo_t")
        .def(py::init())
        .def("__repr__", [](const sox_signalinfo_t &self) {
            std::stringstream ss;
            ss << "sox_signalinfo_t {\n"
                << "  rate-> " << self.rate << "\n"
                << "  channels-> " << self.channels << "\n"
                << "  precision-> " << self.precision << "\n"
                << "  length-> " << self.length << "\n"
                << "  mult-> " << self.mult << "\n"
                << "}\n";
            return ss.str();
        })
        .def_readwrite("rate", &sox_signalinfo_t::rate)
        .def_readwrite("channels", &sox_signalinfo_t::channels)
        .def_readwrite("precision", &sox_signalinfo_t::precision)
        .def_readwrite("length", &sox_signalinfo_t::length)
        .def_readwrite("mult", &sox_signalinfo_t::mult);


#ifdef VERSION_INFO
    m.attr("__version__") = VERSION_INFO;
#else
    m.attr("__version__") = "dev";
#endif
}
