import os
import openai
import streamlit as st
from io import BytesIO
import clipboard
from langdetect import detect
import requests
import base64
from PIL import Image
from moviepy.editor import *




initial_prompt = [
    {"role": "system", "content": "Create a scenario by input a keyword."}
]

def translate_text(text, target_language="en"):
    client_id = "your key"
    client_secret ="your key"
    url = "https://openapi.naver.com/v1/papago/n2mt"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    data = {
        "source": "ko",
        "target": target_language,
        "text": text
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        translated_text = response.json()["message"]["result"]["translatedText"]
        return translated_text
    else:
        return None


class Translator:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def translate(self, text, target_language="en"):
        translated_text = translate_text(text, target_language)
        return translated_text

def save_text_as_file(text):
    with open("ai_response.txt", "w", encoding="utf-8") as f:
        f.write(text)
    st.success("Text file saved as ai_response.txt")
    text_file = open("ai_response.txt", "rb")
    text_bytes = text_file.read()
    text_base64 = base64.b64encode(text_bytes).decode("utf-8")
    href = f'<a href="data:text/plain;base64,{text_base64}" download="ai_response.txt">Click here to download</a>'
    st.markdown(href, unsafe_allow_html=True)

def save_image_as_file(url):
    response = requests.get(url)
    image_content = response.content
    image = Image.open(BytesIO(image_content))
    image.save("ai_image.jpg")
    st.success("Image file saved as ai_image.jpg")
    image_file = open("ai_image.jpg", "rb")
    image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    href = f'<a href="data:image/jpg;base64,{image_base64}" download="ai_image.jpg">Click here to download</a>'
    st.markdown(href, unsafe_allow_html=True)


def generate_and_save_audio(text):
    try:
        with st.spinner("TTS in progress..."):
            response = requests.post(
                'https://texttospeech.googleapis.com/v1/text:synthesize?key=AIzaSyDqLUV9u5rxUbI5RRLSheyuiXk3JOpBm74',
                json={
                    "input": {
                        "text": text
                    },
                    "voice": {
                        "languageCode": "ko-KR"
                    },
                    "audioConfig": {
                        "audioEncoding": "MP3"
                    }
                }
            )
            if response.status_code == 200:
                audio_content = response.json()["audioContent"]
                with open("ai_response.mp3", "wb") as f:
                    f.write(base64.b64decode(audio_content))
                    st.success("TTS completed successfully. Audio file saved as ai_response.mp3")
                    audio_file = open("ai_response.mp3", "rb")
                    audio_bytes = audio_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    href = f'<a href="data:audio/mp3;base64,{audio_base64}" download="ai_response.mp3">Click here to download</a>'
                    st.markdown(href, unsafe_allow_html=True)
            else:
                st.error("Error occurred during TTS")

    except Exception as e:
        st.error(f"An error occurred during TTS: {e}")



def openai_create_text(user_prompt, temperature=0.7, authen=True):
    if not authen or user_prompt =="":
        return None

    st.session_state.prompt.append(
        {"role": "user", "content": user_prompt}
    )

    try:
        with st.spinner("AI is creating a scenario..."):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.prompt,
                temperature = temperature,
                max_tokens =  2048,
                top_p = 1,    #추가            
            )                
        generated_text = response.choices[0].message.content
    except openai.error.OpenAIError as e:
        generated_text = None
        st.error(f"An error occurred: {e}")
    
    if generated_text:
       st.session_state.prompt.append(
           {"role": "assistant", "content": generated_text}
       )
    if st.session_state.translate:
            translated_text = translate_text(generated_text)
            st.session_state.generated_text = translated_text
    else:
            st.session_state.generated_text = generated_text
    
    if st.session_state.tts:
            generate_and_save_audio(st.session_state.generated_text)

    if st.session_state.save_text:
            save_text_as_file(st.session_state.generated_text)

    return None

def openai_create_image(description, num_images=4, size="1024x1024", authen=True):
    if not authen or description.strip() == "":
        return None

    try:
        with st.spinner("AI is creating Scenes..."):
            response = openai.Image.create(
                prompt=description,
                n=num_images,
                size=size
            )
        image_urls = [image_data['url'] for image_data in response['data']]
        for image_url in image_urls:
            st.image(
                image=image_url,
                use_column_width=True
            )
        if st.session_state.save_image:
            for image_url in image_urls:
                save_image_as_file(image_url)

    except openai.error.OpenAIError as e:
        st.error(f"An error occurred: {e}")
    
    return None


def reset_conversation():
    to_clipboard = ""
    for (human, ai) in zip(st.session_state.human_enq, st.session_state.ai_resp):
        to_clipboard += "\nHuman: " + human + "\n"
        to_clipboard += "\nAI: " + ai + "\n"
        clipboard.copy(to_clipboard)

    st.session_state.generated_text = None
    st.session_state.prompt = initial_prompt
    st.session_state.human_enq = []
    st.session_state.ai_resp = []
    st.session_state.initial_temp = 0.7
    st.session_state.input_key = 0

def switch_between_two_apps():
    st.session_state.initial_temp = st.session_state.temp_value
    st.session_state.input_key = 0

def create_text(authen):
    st.write("**Save Text**")
    st.session_state.save_text = st.checkbox("Enable Text Save")


    if "generated_text" not in st.session_state:
        st.session_state.generated_text = None

    if "prompt" not in st.session_state:
        st.session_state.prompt = initial_prompt

    if "human_enq" not in st.session_state:
        st.session_state.human_enq = []

    if "ai_resp" not in st.session_state:
        st.session_state.ai_resp = []

    if "initial_temp" not in st.session_state:
        st.session_state.initial_temp = 0.7

    if "input_key" not in st.session_state:
        st.session_state.input_key = 0
    
    #tts

    with st.sidebar:
        st.write("")
        st.write("**Translation**")
        st.session_state.translate = st.checkbox("Translate to English")
        
        
        st.write("")
        st.write("**Temperature**")
        st.session_state.temp_value = st.slider(
            label="$\\hspace{0.08em}\\texttt{Temperature}\,$ (higher $\Rightarrow$ more random)",
            min_value=0.0, max_value=1.0, value=st.session_state.initial_temp,
            step=0.1, format="%.1f",
            label_visibility="collapsed"
        )
        st.write("(Higher $\Rightarrow$ More random)")

        st.write("")
        st.write("**Text to Speech**")
        st.session_state.tts = st.checkbox("Enable TTS")

    st.write("")
    left, right = st.columns([2, 3])
    left.write("##### Making a fairy tale book with ai") #수정
    right.write("(Displayed in reverse chronological order)")#수정

    for (human, ai) in zip(st.session_state.human_enq, st.session_state.ai_resp):
        st.write("**:blue[Human:]** " + human)
        st.write("**:blue[AI:]** " + ai)

    key = st.session_state.input_key
    st.text_area(
        label="$\\hspace{0.08em}\\texttt{Enter your query}$",
        value="",
        label_visibility="visible",
        key=key
    )
    user_input_stripped = st.session_state[key-1].strip() if key > 0 else ""

    left, right = st.columns(2) # To show the results below the button
    left.button(
        label="Send",
        on_click=openai_create_text(
            user_input_stripped,
            temperature=st.session_state.temp_value,
            authen=authen
        )
    )
    right.button(
        label="Reset",
        on_click=reset_conversation
    )
    #수정
  
    if authen:
        if user_input_stripped != "" and st.session_state.generated_text:
            st.write("**:blue[AI:]** " + st.session_state.generated_text)
            # TTS
            st.session_state.human_enq.append(user_input_stripped)
            st.session_state.ai_resp.append(st.session_state.generated_text)
            clipboard.copy(st.session_state.generated_text)
    

    for (human, ai) in zip(st.session_state.human_enq[::-1], st.session_state.ai_resp[::-1]):
        st.write("**:blue[Human:]** " + human)
        st.write("**:blue[AI:]** " + ai)
        st.write("---")

    st.session_state.input_key += 1

def create_image(authen):
    with st.sidebar:
        st.write("")
        st.write("**Pixel size**")
        image_size = st.radio(
            "$\\hspace{0.1em}\\texttt{Pixel size}$",
            ('256x256', '512x512', '1024x1024'),
            horizontal=True,
            index=1,
            label_visibility="collapsed"
        )
        st.write("**Save Image**")
        st.session_state.save_image = st.checkbox("Enable Image Save")
        st.write("**Number of Images**")
        num_images = st.slider(
            label="Number of Images",
            min_value=1, max_value=10, value=4,
            step=1, format="%d",
            label_visibility="collapsed"
        )
    st.write("")
    st.write(f"##### Description for your images (in English)")
    description = st.text_area(
        label="$\\hspace{0.1em}\\texttt{Description for your images}\,$ (in $\,$English)",
        value="",
        label_visibility="collapsed"
    )

    left, _ = st.columns(2) # To show the results below the button
    left.button(
        label="Generate",
        on_click=openai_create_image(description, num_images, image_size)
    )

def create_video(authen):
    if not authen:
        st.error("Authentication failed.")
        return

    audio_filename = "ai_response.mp3"  # 오디오 파일 이름
    image_folder = "C:\Programming\project\image"

    # 오디오 클립 생성
    audio_clip = AudioFileClip(audio_filename)

    clips = []
    duration_per_image = audio_clip.duration / len(os.listdir(image_folder))

    for i, image_file in enumerate(os.listdir(image_folder)):
        if image_file.endswith((".jpg", ".png")):
            image_path = os.path.join(image_folder, image_file)
            image_clip = ImageClip(image_path).set_duration(duration_per_image)
            image_clip = image_clip.set_audio(audio_clip.subclip(i * duration_per_image, (i + 1) * duration_per_image))
            clips.append(image_clip)

    final_clip = concatenate_videoclips(clips)

    # 출력 동영상 파일 생성
    output_video = "output.mp4"
    final_clip.write_videofile(output_video, fps=24)

    st.success(f"Video created successfully: {output_video}")
    st.video(output_video)

def openai_create():
    st.write("## Creating a Reading Picture Book Storybook Using Generative Models")

    with st.sidebar:
        st.write("")
        st.write("**Choic of API key**")
        choice_api = st.sidebar.radio(
            "$\\hspace{0.25em}\\texttt{Choic of API}$",
            ('Your key', 'My key'),
            label_visibility="collapsed",
            horizontal=True,
            on_change=reset_conversation
        )
        if choice_api == 'Your key':
            st.write("**Your API Key**")
            openai.api_key = st.text_input(
                label="$\\hspace{0.25em}\\texttt{Your OpenAI API Key}$",
                type="password",
                label_visibility="collapsed"
            )
            authen = True
        else:
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            stored_pin = st.secrets["USER_PIN"]
            st.write("**Password**")
            user_pin = st.text_input(
                label="Enter password", type="password", label_visibility="collapsed"
            )
            authen = user_pin == stored_pin

        st.write("")
        st.write("**What to Generate**")
        option = st.sidebar.radio(
            "$\\hspace{0.25em}\\texttt{What to generate}$",
            ('Text (GPT3.5)', 'Image (DALL·E)', 'video'),
            label_visibility="collapsed",
            horizontal=True,
            on_change=switch_between_two_apps
        )
        tts_api_key = st.text_input(
            label="$\\hspace{0.25em}\\texttt{Text-to-Speech API Key}$",
            type="password",
            key="tts_api_key"
        )

    if option == 'Text (GPT3.5)':
        create_text(authen)
    elif option == 'Image (DALL·E)':
        create_image(authen)
    elif option == 'video':
        create_video(authen)  # create_video 함수 호출

    with st.sidebar:
        st.write("")

    if not authen:
        st.error("**Incorrect password. Please try again.**")


if __name__ == "__main__":
    openai_create()
