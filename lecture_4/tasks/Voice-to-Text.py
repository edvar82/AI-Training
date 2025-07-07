from vosk import Model, KaldiRecognizer
import soundfile as sf
import gradio as gr
import wave
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'model', 'vosk-model-en-us-0.22-lgraph')

if not os.path.exists(MODEL_PATH):
    raise RuntimeError("Modelo Vosk não encontrado. Baixe e extraia para ./model. Veja instruções no início do arquivo.")

model = Model(MODEL_PATH)

def transcribe_audio(audio_file):
    if audio_file is None:
        return "Nenhum áudio enviado."
    # Converte para WAV mono 16kHz se necessário
    wav_path = audio_file
    if not audio_file.lower().endswith('.wav'):
        data, samplerate = sf.read(audio_file)
        wav_path = audio_file + '.wav'
        sf.write(wav_path, data, samplerate, subtype='PCM_16')
    wf = wave.open(wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
        # Converte para mono 16kHz 16bit
        data, samplerate = sf.read(wav_path)
        sf.write(wav_path, data, 16000, subtype='PCM_16')
        wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)
    final_result = rec.FinalResult()
    import json
    try:
        text = json.loads(final_result)['text']
    except Exception as e:
        text = f"Erro ao transcrever o áudio: {e}"
    return text

iface = gr.Interface(
    fn=transcribe_audio,
    inputs=gr.Audio(sources=["upload", "microphone"], type="filepath", label="Envie ou grave um áudio"),
    outputs=gr.Textbox(label="Transcrição"),
    title="Transcritor de Voz para Texto",
    description="Envie ou grave uma mensagem de voz e receba a transcrição automática usando Vosk.",
    allow_flagging="never",
)

if __name__ == "__main__":
    iface.launch(inbrowser=True)
