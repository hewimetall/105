import jamspell
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import os
from vosk import Model, KaldiRecognizer
# Система параметризации структуры данных, написанная для встраивания контекста в объекты JSON
import json
import pymorphy2
import nltk

# for convert audio file
import pydub, wave

class Base():
    """
    provide base function :
        -convers file
        -save
        -recognation
    """
    str_path_wav = None

    def __loads(self):
        pass

    def _convert_file(self, file_path: str, id: str):
        """
        :param path_in, path_to,, mp3:
        :return wav_path:
        """
        str_mp3 = file_path
        file_path = os.path.dirname(file_path)
        str_wav = os.path.join(file_path, "{}.wav".format(id))
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
        self.str_path_wav = str_wav
        return str_wav

    def __del__(self):
        os.remove(self.str_path_wav)

class BaseDataAnaliz(Base):
    type_of = None
    model = None
    corrector = None
    raw_data = None

    def __loads(self):
        ## load base model
        if not os.path.exists("model"):
            raise ValueError
        self.corrector = jamspell.TSpellCorrector()
        if not self.corrector.LoadLangModel('ru_small.bin'):
            raise ValueError
        # Обученная модель для русского языка
        self.model = Model("model")
        self.morph = pymorphy2.MorphAnalyzer()

    def _get_data_in_audio(self,audio_wav_path: str):
        """
        :param audio_wav_path:
                    -path to wav
        :return:
        """

        wf = wave.open(audio_wav_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            # check file not bead
            return
        # список для объединения результатов
        result = list()
        # wf.getframerate()->Возвращает частоту дискретизации.
        rec = KaldiRecognizer(self.model, wf.getframerate())
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
        wf.close()
        self.raw_data = result
        return result

    def _norm_dict(self, token):
        data = []
        for word in self.corrector.GetCandidates([token, ], 0):
            # test data
            data_norm = [i.normal_form for i in self.morph.parse(word) if i.score > 0.25]
            if len(data_norm) == 0:
                data_norm = [self.morph.parse(word)[0].normal_form, ]
            data += data_norm
        return set(data)

    def _corrector_data(self, audio_wav_path: str):
        # THIS RECOGNATIONS SPITH TO TEXT
        res = self._get_data_in_audio(audio_wav_path)
        stop_words = stopwords.words("russian")
        mega_set = set()
        for l in res:
            for token in word_tokenize(l, language="russian"):
                if token in stop_words:
                    continue
                token_norm_set = self._norm_dict( token)
                mega_set |= token_norm_set
        return mega_set

    def get_data(self):
        return self.data_cor

    def __init__(self, id, file_path, dict=None):
        ## procces work file
        file_type = file_path.split(".")[1]
        if not os.path.isfile(file_path):
            return
        else:
            self.__loads()
        if file_type == "mp3":
            path_to_wav = self._convert_file(file_path,id=id)
        else:
            path_to_wav = file_path
        data_cor =  self._corrector_data(path_to_wav)
        self.data_cor = data_cor
        self.dict_f = dict


class CheckBox(BaseDataAnaliz):

    def __loads(self):
        nltk.download('punkt')
        nltk.download('stopwords')
        return super(CheckBox, self).__loads()

    def get_data(self):
        # mix_data_json = [
        #     "магнит",
        #     "максим",
        #     "сок"
        # ]
        morph = pymorphy2.MorphAnalyzer()
        data_norm = " ".join([" ".join([i.normal_form for i in morph.parse(word)]) for word in self.dict_f]).split(
            " ")

        # HAVE FILE DIR AND FILE TYPE WAV
        clr_data = self.data_cor & set(self.data_cor) & set(data_norm)
        return clr_data

class TextBox(BaseDataAnaliz):
    def get_data(self):
        data = " ".join(self.raw_data)
        return data

# path = "session_temp/1/mp3/1_1.mp3"
# mix_data_json = [
#     "магнит",
#     "максим",
#     "сок"
# ]

# test1 = CheckBox(12, path,dict = mix_data_json)
# data  = test1.get_data(mix_data_json)
# test2 = TextBox(12,path)
# data  = test2.get_data()
# print(data)
