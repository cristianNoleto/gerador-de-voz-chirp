import os
import base64
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify, render_template, send_from_directory
from google.cloud import texttospeech

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__, template_folder='templates')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
client = texttospeech.TextToSpeechClient()

# --- CONSTANTES E CONFIGURAÇÃO DE ARMAZENAMENTO ---
AUDIO_HISTORY_PATH = 'audio_history'
os.makedirs(AUDIO_HISTORY_PATH, exist_ok=True)

# DICIONÁRIO DE AMOSTRAS COMPLETO PARA TODOS OS IDIOMAS
PREVIEW_SENTENCES = {
    'pt-BR': 'Olá, esta é uma demonstração da minha voz em português.',
    'en-US': 'Hello, this is a demonstration of my voice in English.',
    'en-GB': 'Hello, this is a demonstration of my voice in English.',
    'es-ES': 'Hola, esta es una demostración de mi voz en español.',
    'it-IT': 'Ciao, questa è una dimostrazione della mia voce in italiano.',
    'de-DE': 'Hallo, dies ist eine Demonstration meiner Stimme auf Deutsch.',
    'fr-FR': 'Bonjour, ceci est une démonstration de ma voix en français.',
    'ja-JP': 'こんにちは、これは日本語での私の声のデモンストレーションです。',
    'ko-KR': '안녕하세요, 이것은 한국어로 된 제 목소리 시연입니다.',
    'ru-RU': 'Здравствуйте, это демонстрация моего голоса на русском языке.',
    'cmn-CN': '你好，这是我的中文声音演示。',
    'hi-IN': 'नमस्ते, यह हिंदी में मेरी आवाज़ का प्रदर्शन है।',
    'ar-XA': 'مرحبًا، هذا عرض توضيحي لصوتي باللغة العربية.',
    'bn-IN': 'হ্যালো, এটি বাংলায় আমার ভয়েসের একটি প্রদর্শনী।',
    'da-DK': 'Hej, dette er en demonstration af min stemme på dansk.',
    'nl-BE': 'Hallo, dit is een demonstratie van mijn stem in het Nederlands.',
    'nl-NL': 'Hallo, dit is een demonstratie van mijn stem in het Nederlands.',
    'en-AU': 'Hello, this is a demonstration of my voice in English.',
    'en-IN': 'Hello, this is a demonstration of my voice in English.',
    'fi-FI': 'Hei, tämä on esittely äänestäni suomeksi.',
    'fr-CA': 'Bonjour, ceci est une démonstration de ma voix en français.',
    'gu-IN': 'નમસ્તે, આ ગુજરાતીમાં મારા અવાજનું પ્રદર્શન છે.',
    'id-ID': 'Halo, ini adalah demonstrasi suara saya dalam bahasa Indonesia.',
    'kn-IN': 'ನಮಸ್ಕಾರ, ಇದು ಕನ್ನಡದಲ್ಲಿ ನನ್ನ ಧ್ವನಿಯ ಪ್ರಾತ್ಯಕ್ಷಿಕೆ.',
    'ml-IN': 'നമസ്കാരം, ഇത് മലയാളത്തിലുള്ള എൻ്റെ ശബ്ദത്തിൻ്റെ ഒരു ഡെമോ ആണ്.',
    'mr-IN': 'नमस्कार, हे माझ्या मराठी आवाजाचे प्रात्यक्षिक आहे.',
    'nb-NO': 'Hei, dette er en demonstrasjon av min stemme på norsk.',
    'pl-PL': 'Cześć, to jest demonstracja mojego głosu w języku polskim.',
    'sv-SE': 'Hej, det här är en demonstration av min röst på svenska.',
    'sw-KE': 'Habari, hii ni onyesho la sauti yangu kwa Kiswahili.',
    'ta-IN': 'வணக்கம், இது தமிழில் என் குரலின் செயல்விளக்கம்.',
    'te-IN': 'నమస్కారం, ఇది తెలుగులో నా వాయిస్ యొక్క ప్రదర్శన.',
    'th-TH': 'สวัสดี นี่คือการสาธิตเสียงของฉันในภาษาไทย',
    'tr-TR': 'Merhaba, bu benim Türkçe sesimin bir gösterimidir.',
    'uk-UA': 'Привіт, це демонстрація мого голосу українською мовою.',
    'ur-IN': 'ہیلو، یہ اردو میں میری آواز کا مظاہرہ ہے۔',
    'vi-VN': 'Xin chào, đây là phần trình diễn giọng nói của tôi bằng tiếng Việt.',
    'es-US': 'Hola, esta es una demostración de mi voz en español.',
}

# --- FUNÇÃO DE LIMPEZA (sem alterações) ---
def cleanup_old_files():
    # ... (código inalterado) ...
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    deleted_count = 0
    for filename in os.listdir(AUDIO_HISTORY_PATH):
        file_path = os.path.join(AUDIO_HISTORY_PATH, filename)
        try:
            file_mtime_ts = os.path.getmtime(file_path)
            file_mtime = datetime.fromtimestamp(file_mtime_ts, timezone.utc)
            if file_mtime < seven_days_ago:
                os.remove(file_path)
                deleted_count += 1
        except Exception as e:
            print(f"Erro ao processar o arquivo {filename} para limpeza: {e}")
    if deleted_count > 0:
        print(f"Limpeza concluída. {deleted_count} arquivos antigos foram removidos.")

cleanup_old_files()

# --- ROTAS DA APLICAÇÃO (sem alterações) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview-voice', methods=['POST'])
def preview_voice():
    try:
        data = request.get_json()
        language_code = data.get('language')
        # AQUI ESTÁ A CORREÇÃO: Usa o dicionário completo com um fallback seguro
        preview_text = PREVIEW_SENTENCES.get(language_code, PREVIEW_SENTENCES['en-US'])
        payload = {
            'text': preview_text, 'language': data.get('language'), 'voice': data.get('voice'),
            'speaking_rate': 1.0, 'format': 'MP3'
        }
        response_content = _generate_audio_from_api(payload)
        audio_base64 = base64.b64encode(response_content).decode('utf-8')
        return jsonify({'audio_content': audio_base64, 'audio_format': 'MP3'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ... (Restante do app.py permanece o mesmo) ...
@app.route('/synthesize', methods=['POST'])
def synthesize():
    try:
        payload = request.get_json()
        audio_format_str = payload.get('format', 'MP3').lower()
        response_content = _generate_audio_from_api(payload)
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{audio_format_str}"
        file_path = os.path.join(AUDIO_HISTORY_PATH, filename)
        with open(file_path, 'wb') as out:
            out.write(response_content)
        return jsonify({'audio_url': f'/history/{filename}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history-list', methods=['GET'])
def history_list():
    try:
        files = sorted(os.listdir(AUDIO_HISTORY_PATH), key=lambda f: os.path.getmtime(os.path.join(AUDIO_HISTORY_PATH, f)), reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/history/<path:filename>')
def serve_history_audio(filename):
    return send_from_directory(AUDIO_HISTORY_PATH, filename)

# --- NOVA ROTA DE EXCLUSÃO ---
@app.route('/history/delete/<path:filename>', methods=['DELETE'])
def delete_history_audio(filename):
    """Exclui um arquivo de áudio específico do histórico."""
    try:
        # --- VERIFICAÇÃO DE SEGURANÇA CRUCIAL ---
        # Constrói o caminho completo e seguro para o arquivo
        history_dir_real = os.path.realpath(AUDIO_HISTORY_PATH)
        file_path_real = os.path.realpath(os.path.join(AUDIO_HISTORY_PATH, filename))

        # Garante que o arquivo a ser excluído está DENTRO da pasta de histórico
        if not file_path_real.startswith(history_dir_real):
            return jsonify({'error': 'Acesso negado.'}), 403 # Forbidden

        if os.path.exists(file_path_real):
            os.remove(file_path_real)
            return jsonify({'success': True, 'message': 'Arquivo excluído com sucesso.'})
        else:
            # Se o arquivo não existe, a operação é considerada um sucesso.
            return jsonify({'success': True, 'message': 'Arquivo já não existia.'})

    except Exception as e:
        print(f"Erro ao excluir o arquivo {filename}: {e}")
        return jsonify({'error': 'Erro interno ao tentar excluir o arquivo.'}), 500

def _generate_audio_from_api(payload):
    text_input = payload.get('text')
    if '[pause' in text_input:
        synthesis_input = texttospeech.SynthesisInput(markup=text_input)
    else:
        synthesis_input = texttospeech.SynthesisInput(text=text_input)
    voice_params = texttospeech.VoiceSelectionParams(language_code=payload.get('language'), name=f"{payload.get('language')}-Chirp3-HD-{payload.get('voice')}")
    encoding_map = {'MP3': texttospeech.AudioEncoding.MP3, 'WAV': texttospeech.AudioEncoding.LINEAR16, 'OGG': texttospeech.AudioEncoding.OGG_OPUS}
    audio_config = texttospeech.AudioConfig(audio_encoding=encoding_map.get(payload.get('format', 'MP3')), speaking_rate=payload.get('speaking_rate', 1.0))
    try:
        response = client.synthesize_speech(input=synthesis_input, voice=voice_params, audio_config=audio_config)
        return response.audio_content
    except Exception as e:
        if "Could not find voice" in str(e) or "is not supported for the language" in str(e):
            raise Exception(f'A voz "{payload.get("voice")}" não é válida para o idioma "{payload.get("language")}".')
        raise e

if __name__ == '__main__':
    app.run(debug=True, port=5000)