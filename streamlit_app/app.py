import os
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
from streamlit_app.history_store import (
    append_message,
    create_history,
    get_or_create_history,
    list_projects_with_history,
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

# Cooldown when everyone shares the app's Gemini key.
# Users who enter their own key are not limited.
GENERATIONS_PER_WINDOW = 3
GENERATION_WINDOW_SECONDS = 10 * 60


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
    "user_api_key": "",
    "generation_times": [],
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


def get_user_api_key():
    """The user's own Gemini key from the sidebar, or None."""

    key = (st.session_state.get("user_api_key") or "").strip()

    return key or None


def recent_generation_times():

    now = time.time()

    times = [
        t
        for t in st.session_state.generation_times
        if now - t < GENERATION_WINDOW_SECONDS
    ]

    st.session_state.generation_times = times

    return times


def generations_left():
    """None means unlimited (user brought their own key)."""

    if get_user_api_key():
        return None

    return max(
        0,
        GENERATIONS_PER_WINDOW - len(recent_generation_times())
    )


def seconds_until_next_generation():

    times = recent_generation_times()

    if len(times) < GENERATIONS_PER_WINDOW:
        return 0

    return int(
        GENERATION_WINDOW_SECONDS - (time.time() - min(times))
    ) + 1


def open_chat(project):
    st.session_state.active_chat = project
    st.session_state.current_project = project


def start_new_project():
    st.session_state.active_chat = None
    st.session_state.mode = "Generate Project"


def on_mode_change():
    st.session_state.active_chat = None


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

    if result.get("model"):
        lines.append(f"Model: `{result.get('model')}`")

    if files:
        lines.append(
            "**Files:**\n" + "\n".join(f"- `{f}`" for f in files)
        )

    lines.append(
        "Ask me anything about this project below."
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
            "Gemini quota / rate limit reached. "
            "Please wait a bit and try again, or enter your own "
            "free Gemini API key in the sidebar (🔑) to keep going."
        )

        return

    if "GEMINI_API_KEY not found" in error_text:

        st.warning(
            "No Gemini API key configured. Enter your own key "
            "in the sidebar (🔑)."
        )

        return

    st.error(message)

    st.exception(error)


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

with st.sidebar.expander(
    "🔑 Your Gemini API key (optional)"
):

    st.text_input(
        "Gemini API key",
        type="password",
        key="user_api_key",
        placeholder="AIza...",
        label_visibility="collapsed"
    )

    st.caption(
        "Use your own free key from "
        "[Google AI Studio](https://aistudio.google.com/apikey) "
        "for unlimited generations. It stays in this browser "
        "session only and is never saved."
    )

# Filled at the end of the script so the count is up to date.
usage_placeholder = st.sidebar.empty()

st.sidebar.caption(
    "PHP 8.x • Gemini • RAG • FAISS"
)


def render_usage_sidebar():

    left = generations_left()

    if left is None:

        usage_placeholder.caption(
            "✅ Using your own API key: no generation limit."
        )

    else:

        usage_placeholder.caption(
            f"Generations left: {left}/{GENERATIONS_PER_WINDOW} "
            f"(resets every {GENERATION_WINDOW_SECONDS // 60} min)"
        )


def render_history_sidebar():

    with history_container:

        st.markdown(
            "**History**"
        )

        items = list_projects_with_history(
            GENERATED_PROJECTS_DIR
        )

        if not items:

            st.caption(
                "No projects yet."
            )

            return

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

        with st.spinner(
            "Thinking..."
        ):

            try:

                agent = PHPCodeUnderstandingAgent(
                    api_key=get_user_api_key()
                )

                answer = agent.ask(
                    project_path=project_dir,
                    question=question,
                    history=earlier_messages,
                    requirement=record.get("requirement")
                )

            except Exception as e:

                show_error(
                    "Error while answering.",
                    e
                )

                return

        st.markdown(answer)

    append_message(record, "user", question)
    append_message(record, "assistant", answer)


# ============================================================
# CHAT FOR A PROJECT FROM HISTORY
# ============================================================

if st.session_state.active_chat:

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
        "Describe your requirement and generate a complete PHP project."
    )

    requirement = st.text_area(
        "Project Requirement",
        height=180,
        placeholder="Describe your PHP project here...",
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

    project_name = st.text_input(
        "Project Name",
        value="my-php-project",
        key="requirement_project_name"
    )

    generate = st.button(
        "Generate Project",
        type="primary",
        use_container_width=True,
        key="generate_project_button"
    )

    if generate:

        if not requirement.strip():

            st.warning(
                "Please enter a project requirement."
            )

        elif not project_name.strip():

            st.warning(
                "Please enter a project name."
            )

        elif generations_left() == 0:

            wait_minutes = max(
                1,
                round(seconds_until_next_generation() / 60)
            )

            st.warning(
                f"You've used all {GENERATIONS_PER_WINDOW} free "
                f"generations for now. Try again in about "
                f"{wait_minutes} minute(s), or enter your own free "
                "Gemini API key in the sidebar (🔑) for no limit."
            )

        else:

            project_name = (
                project_name
                .strip()
                .replace(
                    " ",
                    "-"
                )
            )

            progress = st.progress(
                0
            )

            status = st.empty()

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
                    max_retries=3,
                    api_key=get_user_api_key()
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
                    attachment_type=attachment_type
                )

                progress.progress(
                    100
                )

                # Only count runs that produced a project.
                if not get_user_api_key():
                    st.session_state.generation_times.append(
                        time.time()
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

                st.button(
                    "💬 Open chat for this project",
                    on_click=open_chat,
                    args=(project,),
                    key="open_generated_chat"
                )

                # --------------------------------------------
                # SUCCESS
                # --------------------------------------------

                if result.get("success"):

                    st.success(
                        "Vibe Coding completed successfully."
                    )

                    attempts = result.get(
                        "attempts",
                        0
                    )

                    if result.get("validated") is False:

                        st.info(
                            "PHP is not installed on this server, "
                            "so syntax validation was skipped."
                        )

                    else:

                        st.info(
                            f"Validation completed in {attempts} attempt(s)."
                        )

                    project = st.session_state.current_project

                    files = get_project_files(
                        project
                    )

                    # --------------------------------------------
                    # WORKFLOW
                    # --------------------------------------------

                    st.subheader(
                        "Vibe Coding Workflow"
                    )

                    c1, c2, c3, c4 = st.columns(4)

                    c1.success(
                        "Generated"
                    )

                    c2.success(
                        "Tested"
                    )

                    c3.success(
                        "Validated"
                    )

                    c4.success(
                        "Delivered"
                    )

                    # --------------------------------------------
                    # STRUCTURE
                    # --------------------------------------------

                    display_file_tree(
                        files
                    )

                    # --------------------------------------------
                    # COMPLETE FILE CONTENT
                    # --------------------------------------------

                    st.subheader(
                        "Generated Project Files"
                    )

                    for file in files:

                        content = read_project_file(
                            project,
                            file
                        )

                        with st.expander(
                            f"📄 {file}"
                        ):

                            st.code(
                                content,
                                language=get_language(
                                    file
                                )
                            )

                    st.divider()

                    st.success(
                        f"Project `{project}` is ready."
                    )

                else:

                    st.error(
                        "Vibe Coder could not complete the project."
                    )

                    if result.get("error"):

                        st.code(
                            str(
                                result.get("error")
                            )
                        )

            except Exception as e:

                progress.empty()

                status.empty()

                show_error(
                    "Error while running Vibe Coder.",
                    e
                )


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

                        agent = PHPCodeUnderstandingAgent(
                            api_key=get_user_api_key()
                        )

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

                        agent = PHPRefactorAgent(
                            api_key=get_user_api_key()
                        )

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
