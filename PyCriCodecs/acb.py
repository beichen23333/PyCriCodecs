from struct import iter_unpack
from .chunk import *
from .utf import UTF, UTFBuilder
from .awb import AWB, AWBBuilder
from .hca import HCA
import os
import io
from pydub import AudioSegment

class ACB(UTF):
    __slots__ = ["filename", "payload", "awb"]
    payload: list
    filename: str
    awb: AWB

    def __init__(self, filename) -> None:
        self.payload = UTF(filename).get_payload()
        self.filename = filename
        self.acbparse(self.payload)
    
    def acbparse(self, payload: list) -> None:
        for dict_entry in range(len(payload)):
            for k, v in payload[dict_entry].items():
                if v[0] == UTFTypeValues.bytes:
                    if v[1].startswith(UTFType.UTF.value):
                        par = UTF(v[1]).get_payload()
                        payload[dict_entry][k] = par
                        self.acbparse(par)
        self.load_awb()
    
    def load_awb(self) -> None:
        if self.payload[0]['AwbFile'][1] == b'':
            if isinstance(self.filename, str):
                awb_path = os.path.join(os.path.dirname(self.filename), self.payload[0]['Name'][1]+".awb")
                awbObj = AWB(awb_path)
            else:
                awbObj = AWB(self.payload[0]['Name'][1]+".awb")
        else:
            awbObj = AWB(self.payload[0]['AwbFile'][1])
        self.awb = awbObj

    def extract(self, decode: bool = False, key: int = 0, dirname: str = ""):
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        pl = self.payload[0]
        cue_names_and_indexes = [(entry["CueIndex"], entry["CueName"]) for entry in pl["CueNameTable"]]
        sorted_cue_names = sorted(cue_names_and_indexes, key=lambda x: x[0])
        cue_names = [name[1][1] if isinstance(name[1], tuple) else name[1] for name in sorted_cue_names]

        for idx, file_data in enumerate(self.awb.getfiles()):
            encode_type = pl["WaveformTable"][idx]["EncodeType"][1]
            extension = self.get_extension(encode_type)
            
            base_name = cue_names[idx] if idx < len(cue_names) else str(idx)
            
            if decode and extension == ".hca":
                hca_data = HCA(file_data, key=key, subkey=self.awb.subkey).decode()
                out_filename = base_name + ".ogg"
                out_path = os.path.join(dirname, out_filename)
                
                if AudioSegment:
                    with io.BytesIO(hca_data) as wav_io:
                        audio = AudioSegment.from_wav(wav_io)
                        audio.export(out_path, format="ogg")
                else:
                    with open(out_path.replace(".ogg", ".wav"), "wb") as f:
                        f.write(hca_data)
            else:
                out_filename = base_name + extension
                with open(os.path.join(dirname, out_filename), "wb") as out_file:
                    out_file.write(file_data)
    
    def get_extension(self, EncodeType: int) -> str:
        mapping = {
            0: ".adx", 3: ".adx",
            2: ".hca", 6: ".hca",
            7: ".vag", 10: ".vag",
            8: ".at3",
            9: ".bcwav",
            11: ".at9", 18: ".at9",
            12: ".xma",
            13: ".dsp", 4: ".dsp", 5: ".dsp",
            19: ".m4a"
        }
        return mapping.get(EncodeType, "")

class ACBBuilder(UTFBuilder):
    pass
