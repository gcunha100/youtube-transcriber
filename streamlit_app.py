import streamlit as st
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import isodate
import io
import zipfile

# Configuração da página
st.set_page_config(
    page_title="YouTube Transcriber",
    page_icon="🎥",
    layout="wide"
)

# Título e descrição
st.title('YouTube Transcriber')
st.write('Transcreva vídeos do YouTube facilmente!')

# Usar secrets para a API key
API_KEY = st.secrets["youtube_api_key"]

def get_video_duration(youtube, video_id):
    try:
        response = youtube.videos().list(
            part='contentDetails',
            id=video_id
        ).execute()
        
        if response['items']:
            duration = response['items'][0]['contentDetails']['duration']
            seconds = isodate.parse_duration(duration).total_seconds()
            return seconds
        return 0
    except Exception as e:
        st.error(f"Erro ao verificar duração: {e}")
        return 0

def get_videos(channel_name, video_type):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # Busca o ID do canal
        channel_response = youtube.search().list(
            part='snippet',
            q=channel_name,
            type='channel',
            maxResults=1
        ).execute()

        if not channel_response.get('items'):
            st.error("Canal não encontrado!")
            return []

        channel_id = channel_response['items'][0]['snippet']['channelId']
        videos = []
        next_page_token = None
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while True:
            video_response = youtube.search().list(
                part='id',
                channelId=channel_id,
                maxResults=50,
                type='video',
                pageToken=next_page_token
            ).execute()
            
            for item in response['items']:
                video_id = item['id']['videoId']
                duration = get_video_duration(youtube, video_id)
                
                if video_type == 'Todos os Vídeos':
                    videos.append(video_id)
                elif video_type == 'Vídeos Longos (>1h)' and duration >= 3600:
                    videos.append(video_id)
                elif video_type == 'Shorts (<2min)' and duration <= 120:
                    videos.append(video_id)
                
                status_text.text(f"Vídeos encontrados: {len(videos)}")
                progress_bar.progress(min(len(videos)/100, 1.0))
            
            next_page_token = video_response.get('nextPageToken')
            if not next_page_token or len(videos) >= 500:
                break
        
        return videos
        
    except Exception as e:
        st.error(f"Erro ao buscar vídeos: {e}")
        return []

def get_transcripts(video_ids):
    transcripts = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, video_id in enumerate(video_ids):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
            text = '\n'.join([entry['text'] for entry in transcript])
            transcripts.append({
                'video_id': video_id,
                'text': text
            })
            
            progress = (i + 1) / len(video_ids)
            progress_bar.progress(progress)
            status_text.text(f"Processando vídeo {i+1} de {len(video_ids)}")
            
        except Exception as e:
            st.warning(f"Não foi possível transcrever o vídeo {video_id}: {e}")
    
    return transcripts

def extract_video_id(url):
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1]
        elif 'youtube.com' in url:
            return url.split('v=')[1].split('&')[0]
        return None
    except:
        return None

# Interface do usuário
with st.container():
    # Opção de escolha entre canal ou vídeo único
    input_type = st.radio(
        "O que você deseja transcrever?",
        ["Um vídeo específico", "Vídeos de um canal"]
            )
        
    if input_type == "Um vídeo específico":
        video_url = st.text_input(
            'URL do Vídeo:', 
            placeholder='Ex: https://www.youtube.com/watch?v=...'
            )
        
        if st.button('Transcrever Vídeo', type='primary'):
            if video_url:
                video_id = extract_video_id(video_url)
                if video_id:
                    with st.spinner('Gerando transcrição...'):
                        try:
                            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                            text = '\n'.join([entry['text'] for entry in transcript])
                            st.success("Transcrição gerada com sucesso!")
                                
                                # Opções de download
                            st.download_button(
                                label="📄 Download da Transcrição",
                                data=f"Vídeo: {video_url}\n\n{text}",
                                file_name=f"transcricao_{video_id}.txt",
                                mime="text/plain"
                            )
                            # Mostrar transcrição na tela
                            if st.checkbox("Mostrar transcrição na tela"):
                                st.write("### Transcrição:")
                                st.write(text)
                                    
                        except Exception as e:
                            st.error(f"Não foi possível transcrever o vídeo: {str(e)}")
                    st.error("URL do vídeo inválida. Certifique-se de usar uma URL do YouTube válida.")
            else:
                st.warning("Por favor, insira a URL do vídeo!")

    else:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            channel = st.text_input(
                'URL do Canal ou Nome:', 
                placeholder='Ex: @NomeDoCanal ou youtube.com/@NomeDoCanal'
            )
        
        with col2:
            video_type = st.selectbox(
                'Tipo de Vídeos:',
                ['Todos os Vídeos', 'Vídeos Longos (>1h)', 'Shorts (<2min)']
            )
        
        if st.button('Transcrever Canal', type='primary'):
            if channel:
                with st.spinner('Buscando vídeos...'):
                    videos = get_videos(channel, video_type)
                    
                    if videos:
                        st.success(f"Encontrados {len(videos)} vídeos!")
                        
                        with st.spinner('Gerando transcrições...'):
                            transcripts = get_transcripts(videos)
                            
                            if transcripts:
                                st.success("Transcrições geradas com sucesso!")
                                
                                # Opções de download
                                st.write("### Opções de Download:")
                                download_option = st.radio(
                                    "Escolha como deseja baixar as transcrições:",
                                    ["Arquivo único", "Arquivos separados (ZIP)"]
                                )
                                
                                if download_option == "Arquivo único":
                                    # Combina todas as transcrições em um único texto
                                    all_text = "\n\n" + "="*80 + "\n\n".join([
                                        f"Vídeo: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
                                        for t in transcripts
                                    ])
                                    
                                    st.download_button(
                                        label="📄 Download Arquivo Único",
                                        data=all_text,
                                        file_name="todas_transcricoes.txt",
                                        mime="text/plain"
                                    )
                                else:
                                    # Cria um arquivo ZIP com transcrições separadas
                                    zip_buffer = io.BytesIO()
                                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                        for t in transcripts:
                                            content = f"Vídeo: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
                                            zip_file.writestr(f"transcricao_{t['video_id']}.txt", content)
                                    
                                    st.download_button(
                                        label="📚 Download Arquivos Separados (ZIP)",
                                        data=zip_buffer.getvalue(),
                                        file_name="transcricoes.zip",
                                        mime="application/zip"
                                    )
                                
                                # Mostra as transcrições na tela
                                show_transcripts = st.checkbox("Mostrar transcrições na tela")
                                if show_transcripts:
                                    st.write("### Transcrições:")
                                    for t in transcripts:
                                        with st.expander(f"Vídeo: https://www.youtube.com/watch?v={t['video_id']}"):
                                            st.write(t['text'])
                            else:
                                st.error("Não foi possível gerar as transcrições.")
                    else:
                        st.error("Nenhum vídeo encontrado!")
            else:
                st.warning("Por favor, insira um canal!")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ por [Seu Nome]")
