import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import isodate
import io
import zipfile

st.set_page_config(page_title="YouTube Transcriber", page_icon="🎥")
st.title('YouTube Transcriber')
st.write('Transcreva vídeos do YouTube facilmente!')

try:
    API_KEY = st.secrets["youtube_api_key"]
    youtube = build('youtube', 'v3', developerKey=API_KEY)
except Exception as e:
    st.error("❌ Erro ao configurar API do YouTube. Verifique sua API key.")
    st.stop()

def extract_video_id(url):
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1]
        elif 'youtube.com' in url:
            return url.split('v=')[1].split('&')[0]
        return None
    except Exception:
        return None

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
    except Exception:
        return 0

def get_channel_videos(channel_name, video_type):
    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)
        if '@' in channel_name:
            channel_handle = channel_name.split('@')[-1].split('/')[-1]
            search_query = f"@{channel_handle}"
        else:
            search_query = channel_name
        
        st.write(f"Buscando canal: {search_query}")
        
        channel_response = youtube.search().list(
            part='snippet',
            q=search_query,
            type='channel',
            maxResults=1
        ).execute()

        if not channel_response.get('items'):
            st.error("Canal não encontrado!")
            return []

        channel_id = channel_response['items'][0]['snippet']['channelId']
        channel_title = channel_response['items'][0]['snippet']['title']
        st.success(f"Canal encontrado: {channel_title}")

        videos = []
        with st.spinner('Buscando vídeos...'):
            playlist_response = youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()

            if playlist_response['items']:
                uploads_playlist_id = playlist_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                next_page_token = None
                
                while True:
                    playlist_items = youtube.playlistItems().list(
                        part='snippet',
                        playlistId=uploads_playlist_id,
                        maxResults=50,
                        pageToken=next_page_token
                    ).execute()

                    for item in playlist_items['items']:
                        video_id = item['snippet']['resourceId']['videoId']
                        duration = get_video_duration(youtube, video_id)
                        
                        if video_type == "Vídeos Longos (>10min)" and duration > 600:
                            videos.append({
                                'id': video_id,
                                'title': item['snippet']['title']
                            })
                        elif video_type == "Vídeos Curtos (<10min)" and duration <= 600:
                            videos.append({
                                'id': video_id,
                                'title': item['snippet']['title']
                            })

                    next_page_token = playlist_items.get('nextPageToken')
                    if not next_page_token or len(videos) >= 200:
                        break

        return videos
    except Exception as e:
        st.error(f"Erro ao buscar canal: {str(e)}")
        return []

# Interface principal
transcription_type = st.radio(
    "O que você deseja transcrever?",
    ["Um vídeo específico", "Vídeos de um canal"],
    horizontal=True,
    key="transcription_type_radio"
)

if transcription_type == "Um vídeo específico":
    video_url = st.text_input(
        'Cole a URL do vídeo:',
        placeholder='Ex: https://www.youtube.com/watch?v=...',
        key="single_video_url"
    )

    if st.button('Transcrever', type='primary', key="single_video_button"):
        if not video_url:
            st.warning("Por favor, insira a URL do vídeo!")
            st.stop()

        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("URL do vídeo inválida!")
            st.stop()

        try:
            with st.spinner('Gerando transcrição...'):
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                text = '\n'.join([entry['text'] for entry in transcript])
                
            st.success("Transcrição gerada com sucesso!")
            st.download_button(
                label="📄 Download da Transcrição",
                data=f"Vídeo: {video_url}\n\n{text}",
                file_name=f"transcricao_{video_id}.txt",
                mime="text/plain",
                key="single_video_download"
            )
        except Exception as e:
            st.error(f"Erro ao transcrever o vídeo: {str(e)}")
else:
    col1, col2 = st.columns([3, 1])
    with col1:
        channel = st.text_input(
            'Nome ou URL do Canal:',
            placeholder='Ex: @NomeDoCanal ou digite o nome do canal',
            key="channel_input"
        )
    with col2:
        video_type = st.selectbox(
            'Tipo de Vídeos:',
            ['Vídeos Longos (>10min)', 'Vídeos Curtos (<10min)'],
            key="video_type_select"
        )

    if st.button('Buscar Vídeos', type='primary', key="channel_button"):
        if channel:
            st.write("Iniciando busca...")
            videos = get_channel_videos(channel, video_type)
            
            if videos:
                st.success(f"Encontrados {len(videos)} vídeos!")
                transcripts = []
                videos_sem_legenda = []
                progress_bar = st.progress(0, key="transcription_progress")
                
                for i, video in enumerate(videos):
                    try:
                        transcript = YouTubeTranscriptApi.get_transcript(video['id'], languages=['pt', 'en'])
                        text = '\n'.join([entry['text'] for entry in transcript])
                        transcripts.append({
                            'video_id': video['id'],
                            'title': video['title'],
                            'text': text
                        })
                    except Exception as e:
                        videos_sem_legenda.append(video['title'])
                    finally:
                        progress_bar.progress((i + 1) / len(videos))

                if transcripts:
                    st.success(f"Transcrições geradas com sucesso! ({len(transcripts)} vídeos)")
                    
                    if videos_sem_legenda:
                        st.warning(f"Não foi possível transcrever {len(videos_sem_legenda)} vídeos por falta de legendas:")
                        for titulo in videos_sem_legenda:
                            st.write(f"- {titulo}")

                    download_option = st.radio(
                        "Como deseja baixar as transcrições?",
                        ["Arquivo Único", "Arquivos Separados (ZIP)"],
                        key="download_option_radio"
                    )

                    if download_option == "Arquivo Único":
                        all_text = "\n\n" + "="*80 + "\n\n".join([
                            f"Vídeo: {t['title']}\nURL: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
                            for t in transcripts
                        ])
                        
                        st.download_button(
                            label=f"📄 Download Arquivo Único ({len(transcripts)} transcrições)",
                            data=all_text,
                            file_name="todas_transcricoes.txt",
                            mime="text/plain",
                            key="channel_single_download"
                        )
                    else:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for t in transcripts:
                                content = f"Vídeo: {t['title']}\nURL: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
                                zip_file.writestr(f"transcricao_{t['video_id']}.txt", content)

                        st.download_button(
                            label=f"📚 Download ZIP ({len(transcripts)} arquivos)",
                            data=zip_buffer.getvalue(),
                            file_name="transcricoes.zip",
                            mime="application/zip",
                            key="channel_zip_download"
                        )
                else:
                    st.error("Nenhum dos vídeos possui legendas disponíveis!")
            else:
                st.error("Nenhum vídeo encontrado!")
        else:
            st.warning("Por favor, insira o nome ou URL do canal!")

st.markdown("---")
st.markdown("Desenvolvido com ❤️ por GMC")
