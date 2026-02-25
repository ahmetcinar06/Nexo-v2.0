"""
translator.py
Kolayca metin çevirisi yapmak için yardımcı fonksiyon içerir.
Harici 'translate' paketini kullanır. (pip install translate)
"""

from translate import Translator

def translate_text(text, to_lang, from_lang="auto"):
    """
    Verilen metni istenen dile çevirir.
    :param text: Çevrilecek metin (str)
    :param to_lang: Hedef dil kodu (ör: 'en', 'tr', 'de')
    :param from_lang: Kaynak dil kodu (varsayılan: 'auto')
    :return: Çevrilmiş metin veya hata mesajı (str)
    """
    try:
        translator = Translator(from_lang=from_lang, to_lang=to_lang)
        translation = translator.translate(text)
        return translation
    except Exception as e:
        return f"Translation Error: {str(e)}"