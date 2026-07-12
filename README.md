# 105

Сервис распознавания русской речи на FastAPI. API принимает описание поля и
имя аудиофайла из каталога `data_drive`, распознает речь через Vosk, исправляет
и нормализует текст через JamSpell/NLTK/pymorphy2, затем возвращает текстовое
значение или пересечение с вариантами чекбокса.

## Используемые модели

Для локального запуска нужны внешние модели, которые не хранятся в репозитории:

1. Vosk: <https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip>
2. JamSpell (optional): <https://github.com/bakwc/JamSpell-models/raw/master/ru.tar.gz>

После распаковки в корне проекта должны появиться:

- `model/` - каталог модели Vosk;
- `ru_small.bin` - языковая модель JamSpell, если пакет `jamspell`
  установлен отдельно.

## Требования

- Python 3.12;
- `ffmpeg` для конвертации MP3 через `pydub`;
- системные инструменты сборки, если платформа не предоставляет готовые колеса
  для аудио/NLP-зависимостей.

Пакет `jamspell==0.0.12` не входит в стандартный `req_dev.txt`, потому что
официальный sdist не собирается на Python 3.12. Если в окружении уже доступен
совместимый JamSpell, сервис загрузит `ru_small.bin` и использует его; иначе
нормализация продолжит работу без контекстного исправления опечаток.

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r req_dev.txt
```

Загрузка моделей:

```bash
wget https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip
unzip vosk-model-ru-0.10.zip
mv vosk-model-* model

wget https://github.com/bakwc/JamSpell-models/raw/master/ru.tar.gz
tar -xvf ru.tar.gz
```

## Переменные окружения и локальные данные

Обязательных переменных окружения нет. Перед запуском создайте каталог для
загружаемых аудиофайлов:

```bash
mkdir -p data_drive
```

Файлы, переданные в поле `file`, ищутся относительно `data_drive` в текущем
рабочем каталоге процесса.

## Запуск API

```bash
source .venv/bin/activate
uvicorn main:app --reload
```

Пример запроса:

```bash
curl -X POST http://127.0.0.1:8000/put_items/ \
  -H 'content-type: application/json' \
  -d '{"type":"textbox","id":"12","file":"sample.wav"}'
```

Для чекбокса передайте варианты в `dict_data`:

```bash
curl -X POST http://127.0.0.1:8000/put_items/ \
  -H 'content-type: application/json' \
  -d '{"type":"checkbox","id":"12","file":"sample.wav","dict_data":["магнит","сок"]}'
```

## Тесты и покрытие

```bash
source .venv/bin/activate
python -m pytest --cov=. --cov-report=term-missing
```

Целевой порог покрытия для репозитория - не ниже 93%.

## Аудит зависимостей

```bash
source .venv/bin/activate
python -m pip_audit -r req_dev.txt
```

`pre_build/req_dev.txt` используется только для устаревшего скрипта подготовки
данных в `pre_build/pipeline.py`. Основной API устанавливается из корневого
`req_dev.txt`.
