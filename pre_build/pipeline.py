import sys, os
from shutil import copyfile
from vosk import Model, KaldiRecognizer
# Система параметризации структуры данных, написанная для встраивания контекста в объекты JSON
import json
import pymorphy2

# for convert audio file
import pydub, wave

""" 
:raise
    1 - file not found 
    2 - format 
    3 - dir create fail 
    4 - not model 
    5 - file bead 
"""


def pars_file_name(file_str: str):
    """
    this function  pars file name
    get name audio file format {id_session}_{status}.{wav||mp3}

    :param file_str:
    :return:id_session ,status,formats;
    """
    try:
        id_session, other = file_str.split("_")
        id_session = int(id_session)
        status, formats = other.split(".")
        status = int(status)
        if formats != "mp3" and formats != "wav":
            raise ValueError
    except ValueError:
        sys.exit(2)
    return {"id_session": id_session, "status": status, "formats": formats}


def create_or_clean(id_session, status, path_to_save):
    """
    * id_session
        * wav
        * mp3
        * text
    :param id_session:
    :param status:
    :param path:
    :return:
    """
    session_path = os.path.join(path_to_save, str(id_session))
    mp3_path = os.path.join(session_path, "mp3")
    wav_path = os.path.join(session_path, "wav")
    text_path = os.path.join(session_path, "text")

    # check is create
    if status == 1:
        try:
            os.mkdir(session_path)
            os.mkdir(mp3_path)
            os.mkdir(wav_path)
            os.mkdir(text_path)
        except:
            sys.exit(3)
    return {"mp3_path": mp3_path, "wav_path": wav_path, "text_path": text_path}


def conv_mp3_to_wav(path_in: str, path_to: str, mp3: str):
    """
    :param path_in, path_to,, mp3:
    :return wav_path:
    """
    str_mp3 = path_in + "/" + mp3
    str_wav = path_to + "/" + mp3.replace('mp3', 'wav')
    sound = pydub.AudioSegment.from_mp3(str_mp3)
    wav = sound.export(str_wav, format="wav")

    # открывает файл в формате wav
    wf = wave.open(str_wav, "rb")

    # перевод из стерео в моно
    if wf.getnchannels() != 1:
        wf.close()
        sound_new = pydub.AudioSegment.from_wav(str_wav)
        sound_new = sound_new.set_channels(1)
        os.remove(str_wav)
        sound_new.export(str_wav, format="wav")
        wf = wave.open(str_wav, "rb")

    wf.close()
    return str_wav


def get_data_in_audio(audio_wav_path: str):
    """

    :param audio_wav_path:
                -path to wav
    :return:
    """
    if not os.path.exists("model"):
        sys.exit(4)

    wf = wave.open(audio_wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        # check file not bead
        sys.exit(5)
    # список для объединения результатов
    result = list()
    # Обученная модель для русского языка
    model = Model("model")
    # wf.getframerate()->Возвращает частоту дискретизации.
    rec = KaldiRecognizer(model, wf.getframerate())
    while True:
        data = wf.readframes(1000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            # get result in JSON
            data = rec.Result()
            jsonData = json.loads(data)
            result.append(jsonData['text'])
    jsonData = json.loads(rec.FinalResult())
    # data is void
    if 'result' in jsonData:
        result.append(jsonData.get('text'))

    # перевожу обратно в JSON формат
    # final = json.dumps(result, ensure_ascii=False)

    wf.close()
    return result


def norm_dict(corrector,token):
    data = [ ]
    morph = pymorphy2.MorphAnalyzer()
    for word in corrector.GetCandidates([token,], 0):
        # test data
        data_norm= [ i.normal_form for i in morph.parse(word) if i.score >0.25 ]
        if len(data_norm) == 0:
            data_norm = [morph.parse(word)[0].normal_form, ]
        data += data_norm
    return set(data)

def corrector_data(audio_wav_path: str):
    # THIS RECOGNATIONS SPITH TO TEXT
    res = get_data_in_audio(audio_wav)
    import jamspell
    from nltk.tokenize import RegexpTokenizer
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize
    corrector = jamspell.TSpellCorrector()
    corrector.LoadLangModel('ru_small.bin')
    # data = [[[i.normal_form for i in morph.parse(j) if i.score == 1 or i.score == 0.5] for j in
    #          corrector.GetCandidates([i, ], 0)] for i in raw]
    # tokenizer = RegexpTokenizer(r'\w+')
    stop_words = stopwords.words("russian")
    mega_set = set()
    for l in res:
        for token in word_tokenize(l, language="russian"):
            if token in stop_words:
                continue
            token_norm_set = norm_dict(corrector, token)
            mega_set |= token_norm_set
    return mega_set


if __name__ == '__main__':
    """
    - get file 
    - convers file in mp3 to wav ?
    - magick
    - parsing sound file
        - get text 
        - gramm analiz text
    - save data to save_file
    @TODO:
        - websoket server
    """

    dirs = {
        "audio_temp":"audio_temp",
        "session_temp":"session_temp"
    }
    audio_file = sys.argv[1]
    audio_file_path = os.path.join(dirs['audio_temp'],audio_file)

    # check arg is file
    if not os.path.isfile(audio_file_path):
        # file not found
        sys.exit(1)
    data = pars_file_name(audio_file)
    # create dirs temp for sessions
    session_path = create_or_clean(data["id_session"],data["status"],dirs["session_temp"])
    # copy and remove file
    if data['formats'] == "mp3":
        copyfile(audio_file_path, os.path.join(session_path['mp3_path'], audio_file))
        os.remove(audio_file_path)
    else:
        copyfile(audio_file_path, os.path.join(session_path["wav_path"], audio_file))
        os.remove(audio_file_path)

    # convers file to format
    if data["formats"] == "mp3":
        # convers file to wav and save to sesion id
        audio_wav = conv_mp3_to_wav(session_path["mp3_path"],session_path["wav_path"],audio_file)
    else:
        audio_wav = audio_file
    sys.stdout.flush()

    data['formats'] = "wav"
    ## init
    audio_wav = 'session_temp/1/wav/1_1.wav'
    data_cor = corrector_data(audio_wav)
    ## For checkbox
    import nltk
    mix_data_json = [
        "магнит",
        "максим",
        "сок"
    ]
    morph = pymorphy2.MorphAnalyzer()
    data_norm = " ".join([" ".join([i.normal_form for i in morph.parse(word) ]) for word in mix_data_json ]).split(" ")
    nltk.download('punkt')
    nltk.download('stopwords')
    # HAVE FILE DIR AND FILE TYPE WAV
    def_data = data_cor & set(mix_data_json) & set(data_norm)
    print(def_data)
    # For text fields
    print(data_cor)

# {
#   "type": "checkbox",
#   "id":"12",
#   "dict": [
#     "data","pass","war"
#     ],
#   "file":"/tmp/test.mp3"
# }
