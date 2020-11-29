# 105
Для работы использовались открытые модели 
 1. `https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip`
 1. `https://github.com/bakwc/JamSpell-models/raw/master/ru.tar.gz`

## Инструкция по развертыванию сервиса распознования
```bash
pip install -r req_dev.txt
wget https://alphacephei.com/vosk/models/vosk-model-ru-0.10.zip
unzip vosk-model-ru-0.10.zip
mv vosk-model.* model
wget https://github.com/bakwc/JamSpell-models/raw/master/ru.tar.gz
tar -xvf ru.tar.gz
uvicorn main:app --reload
```
## Инструкция по развертыванию сервиса 1c
