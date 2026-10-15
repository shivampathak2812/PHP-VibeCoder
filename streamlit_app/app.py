import os
import re
import sys
import time
import shutil
from pathlib import Path

import streamlit as st


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from agents.vibe_coder import PHPVibeCoder
from agents.code_understanding_agent import PHPCodeUnderstandingAgent
from agents.refactor_agent import PHPRefactorAgent
from agents.php_tester import PHPTester
from agents.explain_agent import PHPExplainAgent
from agents.intent_router import classify_intent, rule_based_intent, EXPLAIN, BUILD
from agents.gemini_model_manager import GeminiModelManager
from streamlit_app.rate_limiter import (
    GenerationLimiter,
    GENERATIONS_PER_WINDOW,
    WINDOW_SECONDS,
    user_id_from_context,
)
from streamlit_app.history_store import (
    append_message,
    create_history,
    get_or_create_history,
    list_projects_with_history,
    save_explanation,
    load_explanation,
    list_explanations,
    append_explanation_message,
)


# ============================================================
# CONFIG
# ============================================================

GENERATED_PROJECTS_DIR = os.path.join(
    PROJECT_ROOT,
    "generated_projects"
)

UPLOADED_FILES_DIR = os.path.join(
    PROJECT_ROOT,
    "uploaded_files"
)

os.makedirs(UPLOADED_FILES_DIR, exist_ok=True)

# Generation limits are kept on the server (see rate_limiter.py), so
# refreshing the page or opening a new tab does not reset them.


st.set_page_config(
    page_title="PHP Vibe Coder",
    page_icon="💻",
    layout="wide"
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "current_project": None,
    "generation_response": None,
    "understanding_answer": None,
    "last_test_result": None,
    "selected_file": None,
    "uploaded_file_info": None,
    "upload_message": None,
    "active_chat": None,
    "active_explanation": None,
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================

def get_project_directories():

    if not os.path.exists(GENERATED_PROJECTS_DIR):
        return []

    return sorted(
        [
            item
            for item in os.listdir(GENERATED_PROJECTS_DIR)
            if os.path.isdir(
                os.path.join(
                    GENERATED_PROJECTS_DIR,
                    item
                )
            )
        ]
    )


def get_project_files(project_name):

    if not project_name:
        return []

    project_path = os.path.join(
        GENERATED_PROJECTS_DIR,
        project_name
    )

    if not os.path.exists(project_path):
        return []

    files = []

    for root, _, filenames in os.walk(project_path):

        for filename in filenames:

            full_path = os.path.join(
                root,
                filename
            )

            relative_path = os.path.relpath(
                full_path,
                project_path
            )

            files.append(relative_path)

    return sorted(files)


def read_project_file(
    project_name,
    relative_file
):

    file_path = os.path.join(
        GENERATED_PROJECTS_DIR,
        project_name,
        relative_file
    )

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:

            return f.read()

    except Exception as e:

        return f"Unable to read file:\n{e}"


@st.cache_resource
def get_generation_limiter():
    """One limiter shared by every session of this app process."""
    return GenerationLimiter()


def current_user_id():
    return user_id_from_context(st.context)


def generations_left():
    return get_generation_limiter().left(current_user_id())


def format_wait(seconds):
    minutes = max(1, round(seconds / 60))
    return f"{minutes} minute(s)"


def open_chat(project):
    st.session_state.active_chat = project
    st.session_state.active_explanation = None
    st.session_state.current_project = project


def open_explanation(explanation_id):
    st.session_state.active_explanation = explanation_id
    st.session_state.active_chat = None


def start_new_project():
    st.session_state.active_chat = None
    st.session_state.active_explanation = None
    st.session_state.mode = "Generate Project"


def on_mode_change():
    st.session_state.active_chat = None
    st.session_state.active_explanation = None


def build_generation_summary(result, files):

    lines = []

    if result.get("success"):
        lines.append(
            f"Generated project **{result.get('project')}** "
            f"with {len(files)} file(s)."
        )
    else:
        lines.append(
            f"Generated project **{result.get('project')}**, "
            "but PHP validation did not fully pass."
        )

    if result.get("validated") is False:
        lines.append(
            "PHP is not installed here, so syntax validation was skipped."
        )
    elif result.get("success"):
        lines.append(
            f"All PHP files passed syntax validation "
            f"(attempt {result.get('attempts', 1)})."
        )

    if result.get("error"):
        lines.append(f"Problem: `{result.get('error')}`")

    if result.get("model"):
        lines.append(f"Model: `{result.get('model')}`")

    if files:
        lines.append(
            "**Files:**\n" + "\n".join(f"- `{f}`" for f in files)
        )

    lines.append(
        "Ask me anything about this project in the box below: "
        "how a file works, where to change something, how to run it..."
    )

    return "\n\n".join(lines)


def show_error(message, error):
    """
    Show a friendly message when Gemini is overloaded or rate limited,
    otherwise show the full error with traceback.
    """

    error_text = str(error)

    if any(
        code in error_text
        for code in ["503", "UNAVAILABLE", "high demand"]
    ):

        st.warning(
            "Gemini is busy right now (high demand on Google's side). "
            "Please wait a minute and try again."
        )

        return

    if any(
        code in error_text
        for code in ["429", "RESOURCE_EXHAUSTED"]
    ):

        st.warning(
            "All AI models are busy or out of quota right now. "
            "Please wait a bit and try again."
        )

        return

    if "GEMINI_API_KEY not found" in error_text:

        st.warning(
            "No Gemini API key configured on the server. "
            "Add GEMINI_API_KEY to .env or Streamlit secrets."
        )

        return

    st.error(message)

    st.exception(error)



# How often the live preview is redrawn while a project streams in.
LIVE_PREVIEW_INTERVAL_SECONDS = 0.5

# Only the end of the answer is shown, so redrawing stays fast.
LIVE_PREVIEW_TAIL_CHARS = 2500

FILE_LINE_PATTERN = re.compile(r"^FILE:\s*(\S+)", re.MULTILINE)


def make_live_preview(live, status, progress):
    """
    Returns a callback for PHPVibeCoder.run(on_progress=...).
    Shows which files are done and the code being written right now.
    """

    last_draw = [0.0]

    def on_progress(text):

        now = time.time()

        if now - last_draw[0] < LIVE_PREVIEW_INTERVAL_SECONDS:
            return

        last_draw[0] = now

        files = FILE_LINE_PATTERN.findall(text)

        if files:
            status.info(
                f"Writing **{files[-1]}** "
                f"({len(files)} file(s) so far)..."
            )
        else:
            status.info("Planning the project...")

        # Real total is unknown: creep from 20% towards 85%.
        progress.progress(min(20 + len(files) * 5, 85))

        tail = text[-LIVE_PREVIEW_TAIL_CHARS:]

        with live.container():

            if files:
                st.caption(
                    "Files: " + ", ".join(f"`{f}`" for f in files)
                )

            st.code(tail)

    return on_progress


def detect_request_type(text, choice):
    """
    choice: "Auto", "Explain only" or "Build project" from the UI.
    Returns EXPLAIN or BUILD.
    """

    if choice == "Explain only":
        return EXPLAIN

    if choice == "Build project":
        return BUILD

    # Auto: free rules first, Gemini only if the rules are unsure.
    intent = rule_based_intent(text)

    if intent:
        return intent

    return classify_intent(
        text,
        model_manager=GeminiModelManager()
    )


def show_explanation(question):

    agent = PHPExplainAgent()

    # Looking up PHP docs happens before the first word appears.
    try:

        with st.spinner("Searching PHP documentation..."):
            prompt = agent.build_prompt(question)

    except Exception as e:

        show_error("Error while explaining.", e)

        return

    st.subheader("Explanation")

    # The answer appears word by word.
    try:

        answer = st.write_stream(
            agent.explain_stream(prompt)
        )

    except Exception as e:

        show_error("Error while explaining.", e)

        return

    model = agent.model_manager.last_model

    st.caption(
        "Explanation only: no project was generated."
        + (f" Model: {model}" if model else "")
    )

    # Saved to the sidebar so it can be reopened (and continued) later.
    try:
        return save_explanation(
            question,
            answer,
            model
        )
    except Exception as e:
        st.caption(f"Could not save this explanation: {e}")

    return None





NAME_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "using", "use", "me", "my", "i", "want", "need", "please", "that",
    "which", "is", "it", "can", "should", "will", "be", "by", "from",
    "create", "build", "make", "generate", "develop", "write", "give",
    "php", "project", "app", "application", "complete", "full", "simple",
    "banao", "bana", "do", "de", "ek", "mujhe", "chahiye", "aur", "ka",
    "ki", "ke", "mein", "me",
}


def make_project_name(requirement):
    """
    Builds a folder name from the requirement, e.g.
    "create a login system with mysql" -> "login-system-mysql".
    Adds -2, -3 ... if that folder already exists.
    """

    words = re.findall(
        r"[a-z0-9]+",
        requirement.lower()
    )

    keep = [
        w for w in words
        if w not in NAME_STOPWORDS
    ][:3]

    base = "-".join(keep) or "php-project"

    name = base
    number = 2

    existing = set(get_project_directories())

    while name in existing:
        name = f"{base}-{number}"
        number += 1

    return name


def get_language(filename):

    ext = os.path.splitext(
        filename
    )[1].lower()

    languages = {
        ".php": "php",
        ".js": "javascript",
        ".css": "css",
        ".json": "json",
        ".sql": "sql",
        ".ini": "ini",
        ".md": "markdown",
        ".html": "html",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
    }

    return languages.get(
        ext,
        "text"
    )


def sanitize_filename(filename):

    filename = os.path.basename(
        filename
    )

    return filename.replace(
        "..",
        "_"
    )


def format_file_size(size_bytes):

    if size_bytes < 1024:
        return f"{size_bytes} B"

    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"

    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def save_uploaded_file(uploaded_file):

    if uploaded_file is None:
        return None

    filename = sanitize_filename(
        uploaded_file.name
    )

    destination = os.path.join(
        UPLOADED_FILES_DIR,
        filename
    )

    with open(
        destination,
        "wb"
    ) as output_file:

        output_file.write(
            uploaded_file.getbuffer()
        )

    return destination


def update_project_file(
    project_name,
    relative_file,
    uploaded_file
):

    if not project_name:
        raise ValueError(
            "Please select a project."
        )

    if not relative_file:
        raise ValueError(
            "Please select a project file."
        )

    project_dir = os.path.abspath(
        os.path.join(
            GENERATED_PROJECTS_DIR,
            project_name
        )
    )

    target_path = os.path.abspath(
        os.path.join(
            project_dir,
            relative_file
        )
    )

    if not target_path.startswith(
        project_dir + os.sep
    ):
        raise ValueError(
            "Invalid file path."
        )

    if not os.path.isfile(target_path):
        raise FileNotFoundError(
            f"Project file does not exist: {relative_file}"
        )

    data = uploaded_file.getbuffer()

    with open(
        target_path,
        "wb"
    ) as output_file:

        output_file.write(data)

    return target_path


def select_project(label="Select Project"):

    projects = get_project_directories()

    if not projects:

        st.warning(
            "No generated projects found."
        )

        return None

    current = st.session_state.current_project

    if current in projects:

        default_index = projects.index(
            current
        )

    else:

        default_index = 0

    project = st.selectbox(
        label,
        projects,
        index=default_index
    )

    return project


def display_file_tree(files):

    st.subheader(
        "Project Structure"
    )

    for file in files:

        normalized = file.replace(
            "\\",
            "/"
        )

        parts = normalized.split("/")

        indent = ""

        for index, part in enumerate(parts):

            if index == len(parts) - 1:

                st.write(
                    f"{indent}📄 `{part}`"
                )

            else:

                st.write(
                    f"{indent}📁 `{part}`"
                )

            indent += "　"


def display_test_result(result):

    if not result:
        return

    total = result.get(
        "total_files",
        0
    )

    passed = result.get(
        "passed",
        0
    )

    failed = result.get(
        "failed",
        0
    )

    st.subheader(
        "Test Results"
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "PHP Files",
        total
    )

    col2.metric(
        "Passed",
        passed
    )

    col3.metric(
        "Failed",
        failed
    )

    if failed == 0:

        st.success(
            f"All {passed}/{total} PHP files passed syntax validation."
        )

    else:

        st.error(
            f"{failed} PHP file(s) failed validation."
        )

        failures = result.get(
            "failures",
            []
        )

        for failure in failures:

            filename = failure.get(
                "file",
                "Unknown file"
            )

            error = failure.get(
                "error",
                "Unknown error"
            )

            with st.expander(
                filename
            ):

                st.code(
                    error
                )


# ============================================================
# ATTACHMENT MENU FOR GENERATE PROJECT REQUIREMENT BOX
# (the only "+" left in the app — bottom-left of the
#  Project Requirement box: Upload File, Upload Image)
# ============================================================

def render_requirement_attachment_menu():

    st.markdown(
        """
        <style>
        div[data-testid="stTextArea"] textarea {
            padding-bottom: 46px !important;
        }

        .st-key-requirement_attach_wrapper {
            margin-top: -46px;
            margin-bottom: 8px;
            margin-left: 10px;
            width: fit-content;
            position: relative;
            z-index: 5;
        }

        .st-key-requirement_attach_wrapper button {
            padding: 0.15rem 0.6rem !important;
            min-height: 1.8rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container(key="requirement_attach_wrapper"):

        with st.popover(
            "+",
            use_container_width=False
        ):

            st.markdown(
                "**Add to Requirement**"
            )

            attach_action = st.radio(
                "Choose action",
                [
                    "Upload File",
                    "Upload Image",
                ],
                key="requirement_attach_radio",
                label_visibility="collapsed"
            )

            # ------------------------------------------------
            # FILE
            # ------------------------------------------------

            if attach_action == "Upload File":

                req_file = st.file_uploader(
                    "Choose file",
                    key="requirement_file_uploader"
                )

                if req_file:

                    st.caption(
                        f"{req_file.name} • "
                        f"{format_file_size(req_file.size)}"
                    )

                    if st.button(
                        "Save File",
                        type="primary",
                        use_container_width=True,
                        key="save_requirement_file"
                    ):

                        try:

                            saved_path = save_uploaded_file(
                                req_file
                            )

                            st.session_state.uploaded_file_info = {
                                "name": req_file.name,
                                "path": saved_path,
                                "type": "file",
                                "size": req_file.size,
                            }

                            st.success(
                                "File uploaded successfully."
                            )

                        except Exception as e:

                            st.error(
                                "Unable to save file."
                            )

                            st.exception(e)

            # ------------------------------------------------
            # IMAGE
            # ------------------------------------------------

            else:

                req_image = st.file_uploader(
                    "Choose image",
                    type=[
                        "png",
                        "jpg",
                        "jpeg",
                        "webp",
                        "gif"
                    ],
                    key="requirement_image_uploader"
                )

                if req_image:

                    st.image(
                        req_image,
                        caption=req_image.name,
                        use_container_width=True
                    )

                    if st.button(
                        "Save Image",
                        type="primary",
                        use_container_width=True,
                        key="save_requirement_image"
                    ):

                        try:

                            saved_path = save_uploaded_file(
                                req_image
                            )

                            st.session_state.uploaded_file_info = {
                                "name": req_image.name,
                                "path": saved_path,
                                "type": "photo",
                                "size": req_image.size,
                            }

                            st.success(
                                "Image uploaded successfully."
                            )

                        except Exception as e:

                            st.error(
                                "Unable to save image."
                            )

                            st.exception(e)


# ============================================================
# HEADER
# ============================================================

st.title(
    "PHP Vibe Coder"
)

st.caption(
    "Requirement → Architecture → Code → Test → Debug → Retest → Deliver"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "PHP Vibe Coder"
)

st.sidebar.button(
    "➕ New Project",
    use_container_width=True,
    on_click=start_new_project,
    key="new_project_button"
)

mode = st.sidebar.radio(
    "Operation",
    [
        "Generate Project",
        "Project Workspace",
        "Understand Code",
        "Refactor Code",
        "Test Project"
    ],
    key="mode",
    on_change=on_mode_change
)

st.sidebar.markdown(
    "---"
)

# Filled at the end of the script so a project generated
# in this run shows up immediately.
history_container = st.sidebar.container()

st.sidebar.markdown(
    "---"
)

# Filled at the end of the script so the count is up to date.
usage_placeholder = st.sidebar.empty()

st.sidebar.caption(
    "PHP 8.x • Gemini • RAG • FAISS"
)


def render_usage_sidebar():

    left = generations_left()

    usage_placeholder.caption(
        f"Generations left: {left}/{GENERATIONS_PER_WINDOW} "
        f"(each one frees up {WINDOW_SECONDS // 60} min after use)"
    )


def render_history_sidebar():

    with history_container:

        st.markdown(
            "**History**"
        )

        items = list_projects_with_history(
            GENERATED_PROJECTS_DIR
        )

        explanations = list_explanations()

        if not items and not explanations:

            st.caption(
                "Nothing yet."
            )

            return

        if items:

            st.caption(
                "Projects"
            )

        for item in items:

            project = item["project"]

            requirement = (
                item.get("requirement") or ""
            ).strip().replace("\n", " ")

            label = f"💬 {project}"

            st.button(
                label,
                key=f"history_{project}",
                help=requirement[:200] or None,
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.active_chat == project
                    else "secondary"
                ),
                on_click=open_chat,
                args=(project,)
            )

        if explanations:

            st.caption(
                "Explanations"
            )

        for record in explanations:

            question = (
                record.get("question") or ""
            ).strip().replace("\n", " ")

            short = (
                question[:28] + "..."
                if len(question) > 28
                else question
            )

            st.button(
                f"💡 {short}",
                key=f"explain_{record['id']}",
                help=question[:200] or None,
                use_container_width=True,
                type=(
                    "primary"
                    if st.session_state.active_explanation == record["id"]
                    else "secondary"
                ),
                on_click=open_explanation,
                args=(record["id"],)
            )


def render_explanation(explanation_id):

    record = load_explanation(
        explanation_id
    )

    if not record:

        st.warning(
            "This explanation no longer exists."
        )

        return

    st.header(
        "💡 Explanation"
    )

    with st.chat_message("user"):

        st.markdown(
            record.get("question", "")
        )

    with st.chat_message("assistant"):

        st.markdown(
            record.get("answer", "")
        )

        if record.get("model"):
            st.caption(f"Model: {record['model']}")

    for message in record.get("messages", []):

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

            if message.get("model"):
                st.caption(f"Model: {message['model']}")

    question = st.chat_input(
        "Ask a follow-up question..."
    )

    if not question:
        return

    with st.chat_message("user"):

        st.markdown(question)

    # The whole conversation so far, so "this" / "that example"
    # in the new question makes sense to the model.
    history = [
        {"role": "user", "content": record.get("question", "")},
        {"role": "assistant", "content": record.get("answer", "")},
    ] + list(record.get("messages", []))

    with st.chat_message("assistant"):

        try:

            agent = PHPExplainAgent()

            with st.spinner("Searching PHP documentation..."):
                prompt = agent.build_prompt(question, history=history)

            answer = st.write_stream(
                agent.explain_stream(prompt)
            )

        except Exception as e:

            show_error("Error while answering.", e)

            return

        model = agent.model_manager.last_model

        if model:
            st.caption(f"Model: {model}")

    append_explanation_message(explanation_id, "user", question)
    append_explanation_message(
        explanation_id, "assistant", answer, model=model
    )


def render_chat(project):

    project_dir = os.path.join(
        GENERATED_PROJECTS_DIR,
        project
    )

    if not os.path.isdir(project_dir):

        st.warning(
            f"Project `{project}` no longer exists."
        )

        return

    record = get_or_create_history(
        project,
        project_dir
    )

    st.header(
        f"💬 {project}"
    )

    files = get_project_files(
        project
    )

    with st.expander(
        f"📁 Project files ({len(files)})"
    ):

        for file in files:

            with st.expander(
                f"📄 {file}"
            ):

                st.code(
                    read_project_file(project, file),
                    language=get_language(file)
                )

    if not record.get("messages"):

        st.info(
            "This project was generated before chat history existed. "
            "Ask anything about it below."
        )

    for message in record.get("messages", []):

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    question = st.chat_input(
        f"Ask anything about {project}..."
    )

    if not question:
        return

    with st.chat_message("user"):

        st.markdown(question)

    earlier_messages = list(
        record.get("messages", [])
    )

    with st.chat_message("assistant"):

        try:

            agent = PHPCodeUnderstandingAgent()

            with st.spinner(
                "Analyzing project..."
            ):

                prompt = agent.build_prompt(
                    project_path=project_dir,
                    question=question,
                    history=earlier_messages,
                    requirement=record.get("requirement")
                )

            # The answer appears word by word.
            answer = st.write_stream(
                agent.ask_stream(prompt)
            )

        except Exception as e:

            show_error(
                "Error while answering.",
                e
            )

            return

    append_message(record, "user", question)
    append_message(record, "assistant", answer)


# ============================================================
# CHAT FOR A PROJECT FROM HISTORY
# ============================================================

if st.session_state.active_explanation:

    render_explanation(
        st.session_state.active_explanation
    )


elif st.session_state.active_chat:

    render_chat(
        st.session_state.active_chat
    )


# ============================================================
# 1. GENERATE PROJECT
# ============================================================

elif mode == "Generate Project":

    st.header(
        "Generate PHP Project"
    )

    st.write(
        "Ask a PHP question to get an explanation, or describe a "
        "project to build it. Projects are saved automatically."
    )

    # A finished request empties the box for the next one. This must
    # happen before the widget is created.
    if st.session_state.pop("clear_requirement", False):
        st.session_state.requirement_text_area = ""

    requirement = st.text_area(
        "Ask or Describe",
        height=180,
        placeholder=(
            "Ask a question (e.g. explain database connection) "
            "or describe a project to build..."
        ),
        key="requirement_text_area"
    )

    render_requirement_attachment_menu()

    # Show the currently selected attachment outside the popover.
    uploaded_info = st.session_state.get(
        "uploaded_file_info"
    )

    if uploaded_info:
        attachment_name = uploaded_info.get(
            "name",
            "Uploaded attachment"
        )
        attachment_size = uploaded_info.get(
            "size",
            0
        )
        attachment_type = uploaded_info.get(
            "type",
            "file"
        )

        if attachment_type == "photo":
            attachment_icon = "🖼️"
        else:
            attachment_icon = "📎"

        st.caption(
            f"{attachment_icon} {attachment_name} • "
            f"{format_file_size(attachment_size)} • "
            f"Ready for generation"
        )

    generate = st.button(
        "Generate",
        type="primary",
        use_container_width=True,
        key="generate_project_button"
    )

    # Set when an answer is ready and its chat should be opened.
    switch_view = False

    if generate:

        if not requirement.strip():

            st.warning(
                "Please enter a project requirement."
            )

        elif detect_request_type(
            requirement,
            "Auto"
        ) == EXPLAIN:

            # Explanation only: no project, no files, and it does not
            # use up a generation. Then open it as a chat so follow-up
            # questions can be asked below.
            explanation_id = show_explanation(requirement)

            if explanation_id:
                open_explanation(explanation_id)
                st.session_state.clear_requirement = True
                switch_view = True

        # Take a generation slot before starting (given back on failure).
        elif not (
            slot := get_generation_limiter().try_acquire(current_user_id())
        )[0]:

            _, reason, wait_seconds, _ = slot

            if reason == "global":
                st.warning(
                    "The app has reached its generation limit for this "
                    "hour (shared by all users). Try again in about "
                    f"{format_wait(wait_seconds)}. Explanations still work."
                )
            else:
                st.warning(
                    f"You've used all {GENERATIONS_PER_WINDOW} free "
                    f"generations for now. Try again in about "
                    f"{format_wait(wait_seconds)}. Explanations still work."
                )

        else:

            slot_token = slot[3]

            # Project name is made automatically from the requirement.
            project_name = make_project_name(
                requirement
            )

            progress = st.progress(
                0
            )

            status = st.empty()

            # Live view of the project while the model writes it.
            live = st.empty()

            try:

                # --------------------------------------------
                # GENERATION
                # --------------------------------------------

                status.info(
                    "Generating PHP project with RAG + Gemini..."
                )

                progress.progress(
                    20
                )

                coder = PHPVibeCoder(
                    max_retries=3
                )

                # ------------------------------------------------
                # OPTIONAL USER ATTACHMENT
                # ------------------------------------------------

                attachment_path = None
                attachment_type = None

                uploaded_info = st.session_state.get(
                    "uploaded_file_info"
                )

                if uploaded_info:
                    attachment_path = uploaded_info.get("path")
                    attachment_type = uploaded_info.get("type")

                    if attachment_path:
                        status.info(
                            "Generating PHP project with "
                            "RAG + Gemini + uploaded input..."
                        )

                result = coder.run(
                    requirement=requirement,
                    project_name=project_name,
                    attachment_path=attachment_path,
                    attachment_type=attachment_type,
                    on_progress=make_live_preview(
                        live,
                        status,
                        progress
                    )
                )

                live.empty()

                progress.progress(
                    100
                )

                st.session_state.generation_response = result

                st.session_state.current_project = result.get(
                    "project",
                    project_name
                )

                status.empty()

                progress.empty()

                # --------------------------------------------
                # SAVE TO HISTORY (shows in the sidebar)
                # --------------------------------------------

                project = st.session_state.current_project

                create_history(
                    project=project,
                    requirement=requirement,
                    summary=build_generation_summary(
                        result,
                        get_project_files(project)
                    ),
                    model=result.get("model")
                )

                # Open the project's chat right away, like ChatGPT:
                # the summary is the first answer and the question
                # box sits at the bottom for follow-ups.
                open_chat(project)

                st.session_state.clear_requirement = True

                switch_view = True

            except Exception as e:

                # Failed runs do not use up a generation.
                get_generation_limiter().release(
                    current_user_id(),
                    slot_token
                )

                progress.empty()

                status.empty()

                live.empty()

                show_error(
                    "Error while running Vibe Coder.",
                    e
                )

    # Outside the try block: st.rerun() works by raising an exception.
    if switch_view:
        st.rerun()


# ============================================================
# 2. PROJECT WORKSPACE
# ============================================================

elif mode == "Project Workspace":

    st.header(
        "Project Workspace"
    )

    project = select_project(
        "Select Project"
    )

    if project:

        files = get_project_files(
            project
        )

        if files:

            left, right = st.columns(
                [1, 3]
            )

            with left:

                st.subheader(
                    "Files"
                )

                selected_file = st.selectbox(
                    "Open File",
                    files
                )

            with right:

                st.subheader(
                    selected_file
                )

                content = read_project_file(
                    project,
                    selected_file
                )

                st.code(
                    content,
                    language=get_language(
                        selected_file
                    )
                )

        else:

            st.warning(
                "No files found in this project."
            )


# ============================================================
# 3. UNDERSTAND CODE
# ============================================================

elif mode == "Understand Code":

    st.header(
        "Understand PHP Code"
    )

    project = select_project(
        "Select Project"
    )

    if project:

        st.write(
            f"Selected Project: **{project}**"
        )

        question = st.text_area(
            "What do you want to understand?",
            height=130,
            placeholder="Ask a question about this PHP project..."
        )

        understand = st.button(
            "Understand Project",
            type="primary",
            use_container_width=True
        )

        if understand:

            if not question.strip():

                st.warning(
                    "Please enter a question."
                )

            else:

                with st.spinner(
                    "Analyzing project and retrieving PHP knowledge..."
                ):

                    try:

                        agent = PHPCodeUnderstandingAgent()

                        answer = agent.ask(
                            project_path=os.path.join(
                                GENERATED_PROJECTS_DIR,
                                project
                            ),
                            question=question
                        )

                        st.session_state.understanding_answer = answer

                    except Exception as e:

                        show_error(
                            "Error while understanding project.",
                            e
                        )

        if st.session_state.understanding_answer:

            st.subheader(
                "Code Understanding"
            )

            st.markdown(
                st.session_state.understanding_answer
            )


# ============================================================
# 4. REFACTOR CODE
# ============================================================

elif mode == "Refactor Code":

    st.header(
        "Refactor PHP Code"
    )

    project = select_project(
        "Select Project"
    )

    if project:

        files = get_project_files(
            project
        )

        php_files = [
            file
            for file in files
            if file.lower().endswith(
                ".php"
            )
        ]

        if not php_files:

            st.warning(
                "No PHP files found in this project."
            )

        else:

            selected_file = st.selectbox(
                "Select PHP File",
                php_files
            )

            instruction = st.text_area(
                "Refactoring Instruction",
                height=120,
                placeholder="Describe how you want this code refactored..."
            )

            refactor = st.button(
                "Refactor Code",
                type="primary",
                use_container_width=True
            )

            if refactor and not instruction.strip():

                st.warning(
                    "Please describe how you want this code refactored."
                )

            elif refactor:

                file_path = os.path.join(
                    GENERATED_PROJECTS_DIR,
                    project,
                    selected_file
                )

                try:

                    with st.spinner(
                        "Refactoring code with Gemini..."
                    ):

                        agent = PHPRefactorAgent()

                        refactored_code = agent.refactor_file(
                            project_path=os.path.join(
                                GENERATED_PROJECTS_DIR,
                                project
                            ),
                            file_path=file_path,
                            instructions=instruction
                        )

                        agent.write_refactored_file(
                            file_path,
                            refactored_code
                        )

                    st.success(
                        "Refactoring completed successfully."
                    )

                    updated_code = read_project_file(
                        project,
                        selected_file
                    )

                    st.subheader(
                        "Updated Code"
                    )

                    st.code(
                        updated_code,
                        language="php"
                    )

                except Exception as e:

                    show_error(
                        "Error while refactoring.",
                        e
                    )


# ============================================================
# 5. TEST PROJECT
# ============================================================

elif mode == "Test Project":

    st.header(
        "Test PHP Project"
    )

    project = select_project(
        "Select Project"
    )

    if project:

        st.write(
            f"Selected Project: **{project}**"
        )

        test = st.button(
            "Run PHP Tests",
            type="primary",
            use_container_width=True
        )

        if test:

            project_path = os.path.join(
                GENERATED_PROJECTS_DIR,
                project
            )

            with st.spinner(
                "Running PHP syntax validation..."
            ):

                try:

                    tester = PHPTester()

                    result = tester.test_project(
                        project_path
                    )

                    st.session_state.last_test_result = result

                except Exception as e:

                    show_error(
                        "Error while testing project.",
                        e
                    )

        display_test_result(
            st.session_state.last_test_result
        )


render_history_sidebar()

render_usage_sidebar()