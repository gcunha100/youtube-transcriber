import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
# Configuração da página
st.set_page_config(
    page_title="YouTube Transcriber",
    page_icon="🎥"
)
        
# Título e descrição
st.title('YouTube Transcriber')
st.write('Transcreva vídeos do YouTube facilmente!')

def extract_video_id(url):
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1]
        elif 'youtube.com' in url:
            return url.split('v=')[1].split('&')[0]
        return None
    except:
        return None

# Escolha inicial
transcription_type = st.radio(
    "O que você deseja transcrever?",
    ["Um vídeo específico", "Vídeos de um canal"],
    horizontal=True
)
    
if transcription_type == "Um vídeo específico":
    video_url = st.text_input(
        'Cole a URL do vídeo:', 
        placeholder='Ex: https://www.youtube.com/watch?v=...'
    )
    
    if st.button('Transcrever', type='primary'):
        if video_url:
            try:
                video_id = extract_video_id(video_url)
                if video_id:
                    with st.spinner('Gerando transcrição...'):
                        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                        text = '\n'.join([entry['text'] for entry in transcript])
                        
                        st.success("Transcrição gerada com sucesso!")
                        
                        st.download_button(
                            label="📄 Download da Transcrição",
                            data=f"Vídeo: {video_url}\n\n{text}",
                            file_name=f"transcricao_{video_id}.txt",
                            mime="text/plain"
                        )
                        
                        if st.checkbox("Visualizar transcrição"):
                            st.write("### Transcrição:")
                            st.write(text)
                else:
                    st.error("URL do vídeo inválida!")
            except Exception as e:
                st.error(f"Erro ao transcrever o vídeo: {str(e)}")
        else:
            st.warning("Por favor, insira a URL do vídeo!")
else:
    st.warning("Opção para transcrever vários vídeos em desenvolvimento.")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ por [Seu Nome]")
