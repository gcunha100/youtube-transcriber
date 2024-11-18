import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
import isodate
import io
import zipfile

# Configuração inicial
st.set_page_config(page_title="YouTube Transcriber", page_icon="🎥")
st.title('YouTube Transcriber')
st.write('Transcreva vídeos do YouTube facilmente!')

# Configuração segura da API Key
try:
    API_KEY = st.secrets["youtube_api_key"]
except Exception as e:
    st.error("Erro: API Key não configurada corretamente nos secrets.")
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
        # Debug para ver o que está sendo enviado
        st.sidebar.write("Buscando canal:", channel_name)
        st.sidebar.write("Tipo de vídeo:", video_type)

        youtube = build('youtube', 'v3', developerKey=API_KEY)
        
        # Tenta primeiro buscar como handle do YouTube
        if '@' in channel_name:
            channel_handle = channel_name.split('@')[-1]
            channel_response = youtube.search().list(
                part='snippet',
                q=f"@{channel_handle}",
                type='channel',
                maxResults=1
            ).execute()
        else:
            # Se não for handle, busca como nome normal
            channel_response = youtube.search().list(
                part='snippet',
                q=channel_name,
                type='channel',
                maxResults=1
            ).execute()

        if not channel_response.get('items'):
            st.error(f"Canal não encontrado: {channel_name}")
            return []

        channel_id = channel_response['items'][0]['snippet']['channelId']
        channel_title = channel_response['items'][0]['snippet']['title']
        
        # Mostra informações do canal encontrado
        st.write(f"Canal encontrado: {channel_title}")
        st.write(f"ID do canal: {channel_id}")

        videos = []
        next_page_token = None
        
        with st.spinner('Buscando vídeos...'):
            progress_bar = st.progress(0)
            videos_checked = 0
            
            while True:
                video_response = youtube.search().list(
                    part='id,snippet',
                    channelId=channel_id,
                    maxResults=50,
                    type='video',
                    pageToken=next_page_token,
                    order='date'  # Ordenar por data
                ).execute()
                
                for item in video_response['items']:
                    video_id = item['id']['videoId']
                    video_title = item['snippet']['title']
                    
                    # Debug para ver cada vídeo encontrado
                    st.sidebar.write(f"Verificando vídeo: {video_title}")
                    
                    duration = get_video_duration(youtube, video_id)
                    
                    if video_type == "Vídeos Longos (>10min)" and duration > 600:
                        videos.append({
                            'id': video_id,
                            'title': video_title,
                            'duration': duration
                        })
                    elif video_type == "Vídeos Curtos (<10min)" and duration <= 600:
                        videos.append({
                            'id': video_id,
                            'title': video_title,
                            'duration': duration
                        })
                    
                    videos_checked += 1
                    progress_bar.progress(min(videos_checked/200, 1.0))
                
                next_page_token = video_response.get('nextPageToken')
                if not next_page_token or videos_checked >= 200:  # Limite de 200 vídeos
                    break
            
            st.write(f"Total de vídeos encontrados: {len(videos)}")
            return videos

    except Exception as e:
        st.error(f"Erro ao buscar vídeos: {str(e)}")
        st.write("Detalhes do erro para debug:", str(e))
        return []

# Interface principal
transcription_type = st.radio(
    "O que você deseja transcrever?",
    ["Um vídeo específico", "Vídeos de um canal"],
    horizontal=True
)

# Lógica para vídeo único
if transcription_type == "Um vídeo específico":
    video_url = st.text_input(
        'Cole a URL do vídeo:',
        placeholder='Ex: https://www.youtube.com/watch?v=...'
    )
    
    if st.button('Transcrever', type='primary'):
        if video_url:
            video_id = extract_video_id(video_url)
            if video_id:
                try:
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
                        
                        st.write("### Visualizar Transcrição:")
                        st.write(text)
                except Exception as e:
                    st.error(f"Erro ao transcrever o vídeo: {str(e)}")
        else:
            st.error("URL do vídeo inválida!")
    else:
            st.warning("Por favor, insira a URL do vídeo!")
        
# Lógica para canal
else:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        channel = st.text_input(
            'Nome ou URL do Canal:',
            placeholder='Ex: @NomeDoCanal ou digite o nome do canal'
        )
    
    with col2:
        video_type = st.selectbox(
            'Tipo de Vídeos:',
            ['Vídeos Longos (>10min)', 'Vídeos Curtos (<10min)']
        )
    
    if st.button('Buscar Vídeos', type='primary'):
        if channel:
            st.write("Iniciando busca...")
            videos = get_channel_videos(channel, video_type)
            
            if videos:
                st.success(f"Encontrados {len(videos)} vídeos!")
                
                transcripts = []
                progress_bar = st.progress(0)
                
                for i, video in enumerate(videos):
                    try:
                        transcript = YouTubeTranscriptApi.get_transcript(video['id'], languages=['pt', 'en'])
                        text = '\n'.join([entry['text'] for entry in transcript])
                        transcripts.append({
                            'video_id': video['id'],
                            'title': video['title'],
                            'text': text
                        })
                        progress_bar.progress((i + 1) / len(videos))
                    except Exception as e:
                        st.warning(f"Não foi possível transcrever o vídeo: {video['title']}")
                        st.sidebar.write(f"Erro na transcrição: {str(e)}")
                
                if transcripts:
                    st.success("Transcrições geradas com sucesso!")
                    
                    download_option = st.radio(
                        "Como deseja baixar as transcrições?",
                        ["Arquivo Único", "Arquivos Separados (ZIP)"]
                    )
                    
                    if download_option == "Arquivo Único":
                        all_text = "\n\n" + "="*80 + "\n\n".join([
                            f"Vídeo: {t['title']}\nURL: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
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
                                content = f"Vídeo: {t['title']}\nURL: https://www.youtube.com/watch?v={t['video_id']}\n\n{t['text']}"
                                zip_file.writestr(f"transcricao_{t['video_id']}.txt", content)
                        
                        st.download_button(
                            label="📚 Download ZIP",
                            data=zip_buffer.getvalue(),
                            file_name="transcricoes.zip",
                            mime="application/zip"
                        )
                    
                    if st.checkbox("Visualizar transcrições"):
                        for t in transcripts:
                            with st.expander(f"Vídeo: {t['title']}"):
                                st.write(t['text'])
            else:
                st.error("Nenhum vídeo encontrado!")
        else:
            st.warning("Por favor, insira o nome ou URL do canal!")

# Rodapé
st.markdown("---")
st.markdown("Desenvolvido com ❤️ por GMC")
