import streamlit as st
from langchain_core.messages.chat import ChatMessage

from dotenv import load_dotenv
from streamlit_wrapper import create_graph, stream_graph
from langchain_teddynote import logging
from langsmith import Client
from langchain_core.messages import HumanMessage, AIMessage
from langchain_teddynote.messages import random_uuid

load_dotenv()

# 프로젝트 이름을 입력합니다.
LANGSMITH_PROJECT = "vulnerability chatbot prj"

# LangSmith 추적을 설정합니다.
logging.langsmith(LANGSMITH_PROJECT)


NAMESPACE = "langchain"

# LangSmith 클라이언트를 세션 상태에 저장합니다.
if "langsmith_client" not in st.session_state:
    st.session_state["langsmith_client"] = Client()

st.set_page_config(
    page_title="CVE 어시스턴트",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("CVE 어시스턴트💬")
st.markdown("NIST가 제공하는 CVE/CPE, 보안취약점 메타데이터를 기반으로 응답합니다.")

with st.sidebar:
    st.markdown("🧑‍💻저작자 [@유수영](https://github.com/USU091")


# 대화기록을 저장하기 위한 용도로 생성
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 스레드 ID를 저장하기 위한 용도로 생성
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = random_uuid()

# 사이드바 생성
with st.sidebar:
    st.markdown("---\n**대화 초기화**")

    # 초기화 버튼 생성
    clear_btn = st.button(
        "새로운 주제로 질문", type="primary", use_container_width=True
    )


# 이전 대화를 출력
def print_messages():
    for chat_message in st.session_state["messages"]:
        if chat_message.role == "user":
            st.chat_message(chat_message.role, avatar="🙎‍♂️").write(chat_message.content)
        else:
            st.chat_message(chat_message.role, avatar="😊").write(chat_message.content)


# 새로운 메시지를 추가
def add_message(role, message):
    st.session_state["messages"].append(ChatMessage(role=role, content=message))


def get_message_history():
    ret = []
    for chat_message in st.session_state["messages"]:
        if chat_message.role == "user":
            ret.append(HumanMessage(content=chat_message.content))
        else:
            ret.append(AIMessage(content=chat_message.content))

    return ret


if "feedback" not in st.session_state:
    st.session_state.feedback = {}

if "open_feedback" not in st.session_state:
    st.session_state["open_feedback"] = False


def submit_feedback():
    client = st.session_state["langsmith_client"]
    if client:
        feedback = st.session_state.feedback
        run = next(iter(client.list_runs(project_name=LANGSMITH_PROJECT, limit=1)))
        parent_run_id = run.parent_run_ids[0]

        for key, value in feedback.items():
            if key in ["올바른 답변", "도움됨", "구체성"]:
                client.create_feedback(parent_run_id, key, score=value)
            elif key == "의견":
                if value:
                    client.create_feedback(parent_run_id, key, comment=value)


@st.dialog("답변 평가")
def feedback():
    eval1 = st.number_input("올바른 답변", min_value=1, max_value=5, value=5)
    eval2 = st.number_input("도움됨", min_value=1, max_value=5, value=5)
    eval3 = st.number_input("구체성", min_value=1, max_value=5, value=5)

    if st.button("제출"):
        with st.spinner("평가를 제출하는 중입니다..."):
            st.session_state.feedback = {
                "올바른 답변": eval1,
                "도움됨": eval2,
                "구체성": eval3,
            }

            submit_feedback()

        st.rerun()


# 체인 생성
if "graph" not in st.session_state:
    st.session_state["graph"] = create_graph()


@st.dialog("답변 평가")
def feedback():
    st.session_state["open_feedback"] = False
    eval1 = st.number_input(
        "올바른 답변 (1:매우 낮음👎 ~ 5:매우 높음👍): 답변의 신뢰도",
        min_value=1,
        max_value=5,
        value=5,
    )
    eval2 = st.number_input(
        "도움됨 (1:매우 불만족👎 ~ 5:매우 만족👍): 답변 품질",
        min_value=1,
        max_value=5,
        value=5,
    )
    eval3 = st.number_input(
        "구체성 (1:매우 불만족👎 ~ 5:매우 만족👍): 답변의 구체성",
        min_value=1,
        max_value=5,
        value=5,
    )

    comment = st.text_area(
        "의견(선택)", value="", placeholder="의견을 입력해주세요(선택)"
    )

    if st.button("제출", type="primary"):
        with st.spinner("평가를 제출하는 중입니다..."):
            st.session_state.feedback = {
                "올바른 답변": eval1,
                "도움됨": eval2,
                "구체성": eval3,
                "의견": comment,
            }

            submit_feedback()

        st.rerun()


# 초기화 버튼이 눌리면...
if clear_btn:
    st.session_state["open_feedback"] = False
    st.session_state["messages"] = []
    st.session_state["thread_id"] = random_uuid()

# 이전 대화 기록 출력
print_messages()

# 사용자의 입력
user_input = st.chat_input("CVE와 관련된 내용을 물어보세요!")

# 만약에 사용자 입력이 들어오면...
if user_input:
    st.session_state["open_feedback"] = False
    # 사용자의 입력을 화면에 표시
    st.chat_message("user", avatar="🙎‍♂️").write(user_input)
    # 세션 상태에서 그래프 객체를 가져옴
    graph = st.session_state["graph"]

    # AI 답변을 화면에 표시
    with st.chat_message("assistant", avatar="😊"):
        streamlit_container = st.empty()
        # 그래프를 호출하여 응답 생성
        response = stream_graph(
            graph,
            user_input,
            streamlit_container,
            thread_id=st.session_state["thread_id"],
        )

        # 응답에서 AI 답변 추출
        ai_answer = response["generation"]

        st.write(ai_answer)

        # 평가 폼을 위한 빈 컨테이너 생성
        eval_container = st.empty()

    # 평가 폼 생성
    with eval_container.form("my_form"):
        st.write("답변을 평가해 주세요 🙏")
        # 피드백 창 열기 상태를 True로 설정
        st.session_state["open_feedback"] = True

        # 평가 제출 버튼 생성
        submitted = st.form_submit_button("평가하기", type="primary")
        if submitted:
            st.write("평가를 제출하였습니다.")

    # 대화기록을 저장한다.
    add_message("user", user_input)
    add_message("assistant", ai_answer)
else:
    if st.session_state["open_feedback"]:
        feedback()
