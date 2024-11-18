import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import isodate
import io
import zipfile

st.set_page_config(page_title="YouTube Transcriber", page_icon="🎥")
st.title('YouTube Transcriber')
st.write('Transcreva vídeos do YouTube facilmente!')

# Sua API Key do YouTube
API_KEY = "SUA_API_KEY"

def extract_video_id(url):
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1]
        elif 'youtube.com' in url:
            return url.split('v=')[1].split('&')[0]
        return None
    except:
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
    except:
        return 0

def get_channel_videos(channel_name, video_type):
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
        with st.spinner('Buscando vídeos...'):
            progress_bar = st.progress(0)
            videos_checked = 0
            
            while True:
                video_response = youtube.search().list(
                    part='id',
                    channelId=channel_id,
                    maxResults=50,
                    type='video',
                    pageToken=next_page_token
                ).execute()
                
                for item in video_response['items']:
                    video_id = item['id']['videoId']
                    duration = get_video_duration(youtube, video_id)
                    
                    # Filtrar por duração
                    if video_type == "Vídeos Longos (>10min)" and duration > 600:  # 10 minutos
                        videos.append(video_id)
                    elif video_type == "Vídeos Curtos (<10min)" and duration <= 600:
                        videos.append(video_id)
                    
                    videos_checked += 1
                    progress_bar.progress(min(videos_checked/200, 1.0))
                
                next_page_token = video_response.get('nextPageToken')
                if not next_page_token or videos_checked >= 200:  # Limite de 200 vídeos
                    break
                        
        return videos
            except Exception as e:
        st.error(f"Erro ao buscar vídeos: {str(e)}")
        return []

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
    col1, col2 = st.columns([3, 1])
    
    with col1:
        channel = st.text_input(
            'Nome ou URL do Canal:', 
            placeholder='Ex: @NomeDoCanal ou youtube.com/@NomeDoCanal'
        )
    
    with col2:
        video_type = st.selectbox(
            'Tipo de Vídeos:',
            ['Vídeos Longos (>10min)', 'Vídeos Curtos (<10min)']
        )
    
    if st.button('Buscar Vídeos', type='primary'):
        if channel:
            videos = get_channel_videos(channel, video_type)
            
            if videos:
                st.success(f"Encontrados {len(videos)} vídeos!")
                
                transcripts = []
                progress_bar = st.progress(0)
                
                for i, video_id in enumerate(videos):
                    try:
                        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                        text = '\n'.join([entry['text'] for entry in transcript])
                        transcripts.append({
                            'video_id': video_id,
                            'text': text
                        })
                        progress_bar.progress((i + 1) / len(videos))
                    except:
                        st.warning(f"Não foi possível transcrever o vídeo: {video_id}")
                
                if transcripts:
                    st.success("Transcrições geradas com sucesso!")
                    
                    # Opções de download
                    download_option = st.radio(
                        "Como deseja baixar as transcrições?",
                        ["Arquivo Único", "Arquivos Separados (ZIP)"]
                    )
                    
                    if download_option == "Arquivo Único":
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
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for t in transcripts:
                                content = f"Vídeo: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
                                zip_file.writestr(f"transcricao_{t['video_id']}.txt", content)
                        
                        st.download_button(
                            label="📚 Download ZIP",
                            data=zip_buffer.getvalue(),
                            file_name="transcricoes.zip",
                            mime="application/zip"
                        )
                    
                    # Opção para visualizar
                    if st.checkbox("Visualizar transcrições"):
                        for t in transcripts:
                            with st.expander(f"Vídeo: {t['video_id']}"):
                                st.write(t['text'])
            else:
                st.error("Nenhum vídeo encontrado!")
        else:
            st.warning("Por favor, insira o nome ou URL do canal!")
st.markdown("---")
st.markdown("Desenvolvido com ❤️ por [Seu Nome]")
