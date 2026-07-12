import json
import os
import sys
from types import SimpleNamespace

import pytest

import pre_build.class_f as class_f


class ParsedWord:
    def __init__(self, normal_form, score=1.0):
        self.normal_form = normal_form
        self.score = score


def test_identity_corrector_returns_selected_token_and_handles_empty_tokens():
    corrector = class_f.IdentityCorrector()

    assert corrector.GetCandidates(["один"], 0) == ["один"]
    assert corrector.GetCandidates([], 0) == []


def test_load_corrector_falls_back_without_jamspell():
    sys.modules.pop("jamspell", None)

    assert isinstance(class_f.load_corrector(), class_f.IdentityCorrector)


def test_load_corrector_uses_jamspell_when_available(monkeypatch):
    created = {}

    class FakeCorrector:
        def LoadLangModel(self, model_path):
            created["model_path"] = model_path
            return True

    fake_module = SimpleNamespace(TSpellCorrector=lambda: FakeCorrector())
    monkeypatch.setitem(sys.modules, "jamspell", fake_module)

    assert isinstance(class_f.load_corrector("model.bin"), FakeCorrector)
    assert created["model_path"] == "model.bin"


def test_load_corrector_raises_when_jamspell_model_is_missing(monkeypatch):
    fake_module = SimpleNamespace(
        TSpellCorrector=lambda: SimpleNamespace(LoadLangModel=lambda _path: False)
    )
    monkeypatch.setitem(sys.modules, "jamspell", fake_module)

    with pytest.raises(ValueError, match="JamSpell language model"):
        class_f.load_corrector("missing.bin")


def test_base_convert_file_converts_stereo_mp3_to_mono(monkeypatch, tmp_path):
    source = tmp_path / "input.mp3"
    source.write_bytes(b"mp3")
    removed = []
    opened = []

    class FakeWave:
        def __init__(self, channels):
            self.channels = channels
            self.closed = False

        def getnchannels(self):
            return self.channels

        def close(self):
            self.closed = True

    waves = iter([FakeWave(2), FakeWave(1)])

    class FakeSound:
        def __init__(self):
            self.channels = None

        def export(self, path, format):
            opened.append((path, format))
            return path

        def set_channels(self, channels):
            self.channels = channels
            return self

    monkeypatch.setattr(class_f.pydub.AudioSegment, "from_mp3", lambda _path: FakeSound())
    monkeypatch.setattr(class_f.pydub.AudioSegment, "from_wav", lambda _path: FakeSound())
    monkeypatch.setattr(class_f.wave, "open", lambda _path, _mode: next(waves))
    monkeypatch.setattr(class_f.os, "remove", lambda path: removed.append(path))

    converted = class_f.Base()._convert_file(str(source), "field")

    assert converted == str(tmp_path / "field.wav")
    assert opened == [(str(tmp_path / "field.wav"), "wav"), (str(tmp_path / "field.wav"), "wav")]
    assert removed == [str(tmp_path / "field.wav")]


def test_base_del_removes_existing_temp_file(tmp_path):
    temp_file = tmp_path / "field.wav"
    temp_file.write_text("data")
    base = class_f.Base()
    base.str_path_wav = str(temp_file)

    base.__del__()

    assert not temp_file.exists()


def test_loads_requires_model_directory(monkeypatch):
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    monkeypatch.setattr(class_f.os.path, "exists", lambda _path: False)

    with pytest.raises(ValueError):
        analyzer._loads()


def test_loads_initializes_model_corrector_and_morph(monkeypatch):
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    monkeypatch.setattr(class_f.os.path, "exists", lambda _path: True)
    monkeypatch.setattr(class_f, "load_corrector", lambda: "corrector")
    monkeypatch.setattr(class_f, "Model", lambda path: f"model:{path}")
    monkeypatch.setattr(class_f.pymorphy3, "MorphAnalyzer", lambda: "morph")

    analyzer._loads()

    assert analyzer.corrector == "corrector"
    assert analyzer.model == "model:model"
    assert analyzer.morph == "morph"


class FakeWave:
    def __init__(self, frames, channels=1, width=2, comptype="NONE"):
        self.frames = list(frames)
        self.channels = channels
        self.width = width
        self.comptype = comptype
        self.closed = False

    def getnchannels(self):
        return self.channels

    def getsampwidth(self):
        return self.width

    def getcomptype(self):
        return self.comptype

    def getframerate(self):
        return 16000

    def readframes(self, _size):
        return self.frames.pop(0)

    def close(self):
        self.closed = True


def test_get_data_in_audio_reads_partial_and_final_results(monkeypatch):
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    analyzer.model = "model"
    wave_file = FakeWave([b"chunk", b""])

    class FakeRecognizer:
        def __init__(self, model, rate):
            self.model = model
            self.rate = rate

        def AcceptWaveform(self, data):
            return data == b"chunk"

        def Result(self):
            return json.dumps({"text": "часть"})

        def FinalResult(self):
            return json.dumps({"result": [{}], "text": "финал"})

    monkeypatch.setattr(class_f.wave, "open", lambda _path, _mode: wave_file)
    monkeypatch.setattr(class_f, "KaldiRecognizer", FakeRecognizer)

    assert analyzer._get_data_in_audio("audio.wav") == ["часть", "финал"]
    assert analyzer.raw_data == ["часть", "финал"]
    assert wave_file.closed is True


def test_get_data_in_audio_returns_empty_for_invalid_wave(monkeypatch):
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    analyzer.model = "model"
    wave_file = FakeWave([b""], channels=2)
    monkeypatch.setattr(class_f.wave, "open", lambda _path, _mode: wave_file)

    assert analyzer._get_data_in_audio("audio.wav") == []
    assert wave_file.closed is True


def test_norm_dict_uses_candidates_and_fallback_parse(monkeypatch):
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    analyzer.corrector = SimpleNamespace(GetCandidates=lambda _tokens, _index: ["магнит", "пусто"])
    analyzer.morph = SimpleNamespace(
        parse=lambda word: [ParsedWord(f"{word}-low", 0.1), ParsedWord(f"{word}-norm", 0.9)]
        if word == "магнит"
        else [ParsedWord("fallback", 0.1)]
    )

    assert analyzer._norm_dict("магн") == {"магнит-norm", "fallback"}


def test_corrector_data_filters_stopwords_and_unions_norms(monkeypatch):
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    analyzer._get_data_in_audio = lambda _path: ["и магнит сок"]
    analyzer._norm_dict = lambda token: {f"{token}-norm"}
    monkeypatch.setattr(class_f, "stopwords", SimpleNamespace(words=lambda language: ["и"]))
    monkeypatch.setattr(class_f, "word_tokenize", lambda text, language: text.split())

    assert analyzer._corrector_data("audio.wav") == {"магнит-norm", "сок-norm"}


def test_base_loads_noop_and_base_data_get_data():
    base = class_f.Base()
    analyzer = object.__new__(class_f.BaseDataAnaliz)
    analyzer.data_cor = {"value"}

    assert base._loads() is None
    assert analyzer.get_data() == {"value"}


def test_base_data_init_handles_missing_file(monkeypatch):
    monkeypatch.setattr(class_f.os.path, "isfile", lambda _path: False)

    analyzer = class_f.BaseDataAnaliz("field", "missing.wav", dict=["a"])

    assert analyzer.data_cor == set()
    assert analyzer.raw_data == []
    assert analyzer.dict_f == ["a"]


def test_base_data_init_processes_mp3(monkeypatch):
    monkeypatch.setattr(class_f.os.path, "isfile", lambda _path: True)
    monkeypatch.setattr(class_f.BaseDataAnaliz, "_loads", lambda self: None)
    monkeypatch.setattr(
        class_f.BaseDataAnaliz,
        "_convert_file",
        lambda self, file_path, id: f"{id}:{os.path.basename(file_path)}.wav",
    )
    monkeypatch.setattr(
        class_f.BaseDataAnaliz,
        "_corrector_data",
        lambda self, path: {path},
    )

    analyzer = class_f.BaseDataAnaliz("field", "/tmp/input.mp3")

    assert analyzer.data_cor == {"field:input.mp3.wav"}


def test_base_data_init_processes_wav_without_conversion(monkeypatch):
    monkeypatch.setattr(class_f.os.path, "isfile", lambda _path: True)
    monkeypatch.setattr(class_f.BaseDataAnaliz, "_loads", lambda self: None)
    monkeypatch.setattr(
        class_f.BaseDataAnaliz,
        "_convert_file",
        lambda self, _file_path, _id: pytest.fail("wav files should not be converted"),
    )
    monkeypatch.setattr(class_f.BaseDataAnaliz, "_corrector_data", lambda self, path: {path})

    analyzer = class_f.BaseDataAnaliz("field", "/tmp/input.wav")

    assert analyzer.data_cor == {"/tmp/input.wav"}


def test_checkbox_loads_downloads_nltk_data_and_delegates(monkeypatch):
    downloads = []
    delegated = []
    checkbox = object.__new__(class_f.CheckBox)
    monkeypatch.setattr(class_f.nltk, "download", lambda name: downloads.append(name))
    monkeypatch.setattr(class_f.BaseDataAnaliz, "_loads", lambda self: delegated.append(self))

    checkbox._loads()

    assert downloads == ["punkt", "stopwords"]
    assert delegated == [checkbox]


def test_checkbox_get_data_intersects_normalized_dictionary(monkeypatch):
    checkbox = object.__new__(class_f.CheckBox)
    checkbox.data_cor = {"магнит", "сок"}
    checkbox.dict_f = ["магнит", "чай"]
    monkeypatch.setattr(
        class_f.pymorphy3,
        "MorphAnalyzer",
        lambda: SimpleNamespace(parse=lambda word: [ParsedWord(word)]),
    )

    assert checkbox.get_data() == {"магнит"}


def test_textbox_get_data_joins_raw_segments():
    textbox = object.__new__(class_f.TextBox)
    textbox.raw_data = ["один", "два"]

    assert textbox.get_data() == "один два"
