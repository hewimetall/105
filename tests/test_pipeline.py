import json
import sys
from types import SimpleNamespace

import pytest

import pre_build.pipeline as pipeline
from tests.test_class_f import FakeWave, ParsedWord


def test_pars_file_name_accepts_supported_audio_names():
    assert pipeline.pars_file_name("12_1.mp3") == {
        "id_session": 12,
        "status": 1,
        "formats": "mp3",
    }
    assert pipeline.pars_file_name("7_2.wav") == {
        "id_session": 7,
        "status": 2,
        "formats": "wav",
    }


@pytest.mark.parametrize("name", ["bad.mp3", "1_2.ogg", "x_2.wav"])
def test_pars_file_name_exits_for_invalid_names(name):
    with pytest.raises(SystemExit) as exc:
        pipeline.pars_file_name(name)

    assert exc.value.code == 2


def test_create_or_clean_creates_session_tree(tmp_path):
    paths = pipeline.create_or_clean(3, 1, str(tmp_path))

    assert paths == {
        "mp3_path": str(tmp_path / "3" / "mp3"),
        "wav_path": str(tmp_path / "3" / "wav"),
        "text_path": str(tmp_path / "3" / "text"),
    }
    assert (tmp_path / "3" / "mp3").is_dir()
    assert (tmp_path / "3" / "wav").is_dir()
    assert (tmp_path / "3" / "text").is_dir()


def test_create_or_clean_reports_existing_session_as_create_failure(tmp_path):
    (tmp_path / "3").mkdir()

    with pytest.raises(SystemExit) as exc:
        pipeline.create_or_clean(3, 1, str(tmp_path))

    assert exc.value.code == 3


def test_create_or_clean_status_other_than_one_only_returns_paths(tmp_path):
    paths = pipeline.create_or_clean(3, 2, str(tmp_path))

    assert paths["mp3_path"] == str(tmp_path / "3" / "mp3")
    assert not (tmp_path / "3").exists()


def test_conv_mp3_to_wav_converts_stereo_to_mono(monkeypatch, tmp_path):
    mp3_dir = tmp_path / "mp3"
    wav_dir = tmp_path / "wav"
    mp3_dir.mkdir()
    wav_dir.mkdir()
    removed = []
    exports = []

    class FakeSound:
        def export(self, path, format):
            exports.append((path, format))
            return path

        def set_channels(self, channels):
            assert channels == 1
            return self

    waves = iter([FakeWave([b""], channels=2), FakeWave([b""], channels=1)])

    monkeypatch.setattr(pipeline.pydub.AudioSegment, "from_mp3", lambda _path: FakeSound())
    monkeypatch.setattr(pipeline.pydub.AudioSegment, "from_wav", lambda _path: FakeSound())
    monkeypatch.setattr(pipeline.wave, "open", lambda _path, _mode: next(waves))
    monkeypatch.setattr(pipeline.os, "remove", lambda path: removed.append(path))

    result = pipeline.conv_mp3_to_wav(str(mp3_dir), str(wav_dir), "sample.mp3")

    assert result == str(wav_dir / "sample.wav")
    assert exports == [(str(wav_dir / "sample.wav"), "wav"), (str(wav_dir / "sample.wav"), "wav")]
    assert removed == [str(wav_dir / "sample.wav")]


def test_get_data_in_audio_requires_model(monkeypatch):
    monkeypatch.setattr(pipeline.os.path, "exists", lambda _path: False)

    with pytest.raises(SystemExit) as exc:
        pipeline.get_data_in_audio("audio.wav")

    assert exc.value.code == 4


def test_get_data_in_audio_rejects_invalid_wave(monkeypatch):
    monkeypatch.setattr(pipeline.os.path, "exists", lambda _path: True)
    monkeypatch.setattr(pipeline.wave, "open", lambda _path, _mode: FakeWave([b""], width=1))

    with pytest.raises(SystemExit) as exc:
        pipeline.get_data_in_audio("audio.wav")

    assert exc.value.code == 5


def test_get_data_in_audio_returns_partial_and_final_text(monkeypatch):
    monkeypatch.setattr(pipeline.os.path, "exists", lambda _path: True)
    monkeypatch.setattr(pipeline.wave, "open", lambda _path, _mode: FakeWave([b"chunk", b""]))
    monkeypatch.setattr(pipeline, "Model", lambda path: f"model:{path}")

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

    monkeypatch.setattr(pipeline, "KaldiRecognizer", FakeRecognizer)

    assert pipeline.get_data_in_audio("audio.wav") == ["часть", "финал"]


def test_pipeline_identity_corrector_and_loader(monkeypatch):
    assert pipeline.IdentityCorrector().GetCandidates(["токен"], 0) == ["токен"]
    assert pipeline.IdentityCorrector().GetCandidates([], 0) == []
    sys.modules.pop("jamspell", None)
    assert isinstance(pipeline.load_corrector(), pipeline.IdentityCorrector)

    fake_module = SimpleNamespace(
        TSpellCorrector=lambda: SimpleNamespace(LoadLangModel=lambda _path: False)
    )
    monkeypatch.setitem(sys.modules, "jamspell", fake_module)
    with pytest.raises(ValueError):
        pipeline.load_corrector()


def test_norm_dict_normalizes_candidates(monkeypatch):
    corrector = SimpleNamespace(GetCandidates=lambda _tokens, _index: ["молоко", "чай"])
    monkeypatch.setattr(
        pipeline.pymorphy3,
        "MorphAnalyzer",
        lambda: SimpleNamespace(
            parse=lambda word: [ParsedWord(f"{word}-low", 0.1), ParsedWord(f"{word}-norm", 0.9)]
            if word == "молоко"
            else [ParsedWord("fallback", 0.1)]
        ),
    )

    assert pipeline.norm_dict(corrector, "молк") == {"молоко-norm", "fallback"}


def test_corrector_data_uses_argument_and_filters_stopwords(monkeypatch):
    seen = {}

    def fake_get_data(path):
        seen["path"] = path
        return ["и магнит сок"]

    monkeypatch.setattr(pipeline, "get_data_in_audio", fake_get_data)
    monkeypatch.setattr(pipeline, "load_corrector", lambda: "corrector")
    monkeypatch.setattr(pipeline.stopwords, "words", lambda language: ["и"])
    monkeypatch.setattr(pipeline, "word_tokenize", lambda text, language: text.split())
    monkeypatch.setattr(pipeline, "norm_dict", lambda corrector, token: {f"{corrector}:{token}"})

    assert pipeline.corrector_data("expected.wav") == {"corrector:магнит", "corrector:сок"}
    assert seen["path"] == "expected.wav"
