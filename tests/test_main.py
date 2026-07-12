import asyncio

from fastapi import BackgroundTasks

import main


def test_get_data_uses_checkbox_for_checkbox_items(monkeypatch):
    calls = {}

    class FakeCheckBox:
        def __init__(self, item_id, file_path, dict_data):
            calls["checkbox"] = (item_id, file_path, dict_data)

        def get_data(self):
            return {"matched"}

    class FakeTextBox:
        def __init__(self, *_args):
            raise AssertionError("TextBox should not be used for checkbox items")

    monkeypatch.setattr(main, "CheckBox", FakeCheckBox)
    monkeypatch.setattr(main, "TextBox", FakeTextBox)

    item = main.Item(type="checkbox", id="field-1", file="audio.wav", dict_data=["one"])

    assert main.get_data(item) == {"matched"}
    assert calls["checkbox"] == ("field-1", "audio.wav", ["one"])


def test_get_data_uses_textbox_for_non_checkbox_items(monkeypatch):
    calls = {}

    class FakeTextBox:
        def __init__(self, item_id, file_path):
            calls["textbox"] = (item_id, file_path)

        def get_data(self):
            return "recognized text"

    monkeypatch.setattr(main, "TextBox", FakeTextBox)

    item = main.Item(type="textbox", id="field-2", file="audio.wav")

    assert main.get_data(item) == "recognized text"
    assert calls["textbox"] == ("field-2", "audio.wav")


def test_create_item_resolves_file_path_and_returns_item_id(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen = {}

    def fake_get_data(item):
        seen["file"] = item.file
        return ["data"]

    monkeypatch.setattr(main, "get_data", fake_get_data)

    item = main.Item(type="textbox", id="field-3", file="sample.wav")
    response = asyncio.run(main.create_item(item, BackgroundTasks()))

    assert response == {"id": "field-3", "data": ["data"]}
    assert seen["file"] == str(tmp_path / "data_drive" / "sample.wav")


def test_route_registered_for_put_items():
    route_paths = {route.path for route in main.app.routes}

    assert "/put_items/" in route_paths
