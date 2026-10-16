import os
import re
import sys
import time
import shutil
import io
import zipfile
from datetime import datetime, timedelta
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
from agents.faq import answer_faq
from streamlit_app.rate_limiter import (
    GenerationLimiter,
    GENERATIONS_PER_WINDOW,
    WINDOW_SECONDS,
    GLOBAL_GENERATIONS_PER_HOUR,
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
    page_icon="🐘",
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
            f"### Project ready ✓\n"
            f"Generated **{result.get('project')}** "
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

    # No model line when no AI was used (exact cache or reused project).
    if result.get("model") and result.get("source") not in ("cache", "reuse"):
        lines.append(
            f"Model: `{result.get('model')}`"
            + (
                f" · thinking: `{result['thinking']}`"
                if result.get("thinking") else ""
            )
        )

    if files:
        lines.append(
            " ".join(f"`✓ {f}`" for f in files)
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



FILE_BLOCK_PATTERN = re.compile(
    r"^FILE:\s*(\S+)\s*\n(?:```[\w+-]*\n)?(.*?)(?=^FILE:|\Z)",
    re.MULTILINE | re.DOTALL
)


def make_live_preview(live, status, progress):
    """
    Returns a callback for PHPVibeCoder.run(on_progress=...).
    Shows the finished files with a tick and the file being written
    right now with its code.
    """

    last_draw = [0.0]

    def on_progress(text):

        now = time.time()

        if now - last_draw[0] < LIVE_PREVIEW_INTERVAL_SECONDS:
            return

        last_draw[0] = now

        blocks = FILE_BLOCK_PATTERN.findall(text)

        if not blocks:
            status.info("Planning the project...")
            progress.progress(15)
            return

        files = [name for name, _ in blocks]
        current, code = blocks[-1]

        status.info(f"Writing **{current}** ({len(files)} file(s) so far)...")

        # Real total is unknown: creep from 20% towards 85%.
        progress.progress(min(20 + len(files) * 5, 85))

        code = code.split("```")[0][-LIVE_PREVIEW_TAIL_CHARS:]

        with live.container():

            st.markdown(
                " ".join(f"`✓ {name}`" for name in files[:-1])
                + f" `⏳ {current}`"
            )

            st.code(code, language=get_language(current))

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

    # The answer appears word by word.
    try:

        answer = st.write_stream(
            agent.explain_stream(prompt)
        )

    except Exception as e:

        show_error("Error while explaining.", e)

        return

    model = agent.model_manager.last_model

    if model:
        st.caption(f"Model: {model}")

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
# LOOK & FEEL (colours come from .streamlit/config.toml)
# ============================================================

ACCENT = "#777BB4"

AVATARS = {"user": "🧑‍💻", "assistant": "🐘"}


def chat_bubble(role):
    """st.chat_message with the app's own avatars."""
    return st.chat_message(role, avatar=AVATARS.get(role))

st.markdown(
    """
    <style>
    /* Readable column, like a chat app. */
    .block-container {max-width: 920px; padding-top: 2.2rem;
                      padding-bottom: 7rem;}

    /* Headings inside answers stay modest. */
    [data-testid="stChatMessage"] h1 {font-size: 1.35rem;}
    [data-testid="stChatMessage"] h2 {font-size: 1.2rem;}
    [data-testid="stChatMessage"] h3 {font-size: 1.05rem;}
    [data-testid="stChatMessage"] h4 {font-size: 1rem;}

    /* Sidebar brand */
    .vc-brand {display:flex; align-items:center; gap:10px;
               font-weight:700; font-size:1.15rem; margin:0 0 .4rem;}
    .vc-logo {width:32px; height:32px; border-radius:9px;
              background:#777BB4; color:#fff; display:grid;
              place-items:center; font-size:.72rem; font-weight:800;
              letter-spacing:.3px;}
    .vc-group {font-size:.7rem; text-transform:uppercase;
               letter-spacing:.08em; opacity:.6; margin:.7rem 0 .1rem .3rem;}
    .vc-badge {display:inline-block; border:1px solid #2a2f42;
               background:#22283a; border-radius:999px;
               padding:.15rem .6rem; font-size:.75rem;}
    .vc-badge b {color:#4cc38a;}

    /* History list: compact, left aligned rows. */
    .st-key-history_list button {justify-content:flex-start;
               padding:.3rem .55rem; min-height:2rem; width:100%;}
    .st-key-history_list button > div,
    .st-key-history_list button > div > span {width:100%;
               justify-content:flex-start;}
    .st-key-history_list button p {text-align:left; white-space:nowrap;
               overflow:hidden; text-overflow:ellipsis; font-size:.88rem;}
    .st-key-history_list [data-testid="stVerticalBlock"] {gap:.1rem;}

    /* Home */
    .vc-hero {text-align:center; margin:9vh 0 1.6rem;}
    .vc-hero .vc-logo {width:56px; height:56px; border-radius:15px;
                       font-size:1rem; margin:0 auto 1rem;}
    .vc-hero h1 {font-size:2.1rem; margin:0; padding:0;}
    .vc-hero p {opacity:.7; margin-top:.4rem;}
    .st-key-example_chips button {height:100%; min-height:5.2rem;
               justify-content:flex-start; align-items:flex-start;
               text-align:left; border-radius:12px; padding:.75rem .9rem;}
    .st-key-example_chips button > div,
    .st-key-example_chips button > div > span {width:100%;
               justify-content:flex-start;}
    .st-key-example_chips [data-testid="stMarkdownContainer"] {
               width:100%;}
    .st-key-example_chips button p {text-align:left; font-size:.9rem;
               line-height:1.45; white-space:normal; overflow:visible;
               display:block;}
    .st-key-example_chips button p strong {font-size:.68rem;
               letter-spacing:.08em; color:#8f93cf;}
    .st-key-example_chips [data-testid="stMarkdownContainer"].stMarkdownEllipsis {
               overflow:visible; white-space:normal;}

    /* Chat bubbles: the user's message sits on the right. */
    [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
               background:#262b3d;}

    /* Project actions row */
    .st-key-project_actions button {border-radius:999px;}
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    '<div class="vc-brand"><div class="vc-logo">PHP</div>'
    'Vibe Coder</div>',
    unsafe_allow_html=True
)

st.sidebar.button(
    "＋ New chat",
    use_container_width=True,
    type="primary",
    on_click=start_new_project,
    key="new_project_button"
)

st.sidebar.text_input(
    "Search chats",
    placeholder="🔍 Search chats",
    label_visibility="collapsed",
    key="history_search"
)

# Filled at the end of the script so a project generated
# in this run shows up immediately.
history_container = st.sidebar.container()

st.sidebar.markdown("---")

# The older single-purpose pages, kept for power users.
TOOL_LABELS = {
    "Generate Project": "💬 Chat",
    "Project Workspace": "📁 Project workspace",
    "Understand Code": "🔍 Understand code",
    "Refactor Code": "✏️ Refactor code",
    "Test Project": "🧪 Test project",
}

with st.sidebar.expander(
    "🛠 Tools",
    expanded=st.session_state.get("mode", "Generate Project")
    != "Generate Project"
):

    mode = st.radio(
        "Tools",
        list(TOOL_LABELS),
        format_func=TOOL_LABELS.get,
        key="mode",
        on_change=on_mode_change,
        label_visibility="collapsed"
    )

# Filled at the end of the script so the count is up to date.
usage_placeholder = st.sidebar.empty()


def render_usage_sidebar():

    left = generations_left()

    usage_placeholder.markdown(
        f'<span class="vc-badge" title="Each generation frees up '
        f'{WINDOW_SECONDS // 60} min after use"><b>●</b> '
        f'{left}/{GENERATIONS_PER_WINDOW} generations</span>',
        unsafe_allow_html=True
    )


def _history_group(timestamp):
    """Today / Yesterday / Previous 7 days / Older."""

    try:
        day = datetime.fromisoformat(timestamp).date()
    except Exception:
        return "Older"

    today = datetime.now().date()

    if day == today:
        return "Today"
    if day == today - timedelta(days=1):
        return "Yesterday"
    if day > today - timedelta(days=7):
        return "Previous 7 days"
    return "Older"


def _short(text, limit=34):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def render_history_sidebar():
    """One list for projects and explanations, newest first."""

    entries = []

    for item in list_projects_with_history(GENERATED_PROJECTS_DIR):
        entries.append({
            "kind": "project",
            "id": item["project"],
            "label": item["project"],
            "search": f"{item['project']} {item.get('requirement') or ''}",
            "help": (item.get("requirement") or "")[:200] or None,
            "time": item.get("sort_key") or "",
        })

    for record in list_explanations():
        question = record.get("question") or ""
        entries.append({
            "kind": "explanation",
            "id": record["id"],
            "label": question,
            "search": question,
            "help": question[:200] or None,
            "time": record.get("updated_at") or record.get("created_at") or "",
        })

    query = (st.session_state.get("history_search") or "").strip().lower()

    if query:
        entries = [e for e in entries if query in e["search"].lower()]

    entries.sort(key=lambda e: e["time"], reverse=True)

    with history_container:

        if not entries:
            st.caption("No matching chats." if query else "No chats yet.")
            return

        with st.container(key="history_list"):

            current_group = None

            for entry in entries:

                group = _history_group(entry["time"])

                if group != current_group:
                    st.markdown(
                        f'<div class="vc-group">{group}</div>',
                        unsafe_allow_html=True
                    )
                    current_group = group

                if entry["kind"] == "project":
                    active = st.session_state.active_chat == entry["id"]
                    icon, callback = "📦", open_chat
                    key = f"history_{entry['id']}"
                else:
                    active = st.session_state.active_explanation == entry["id"]
                    icon, callback = "💡", open_explanation
                    key = f"explain_{entry['id']}"

                st.button(
                    f"{icon} {_short(entry['label'])}",
                    key=key,
                    help=entry["help"],
                    use_container_width=True,
                    type="secondary" if active else "tertiary",
                    on_click=callback,
                    args=(entry["id"],)
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

    st.markdown("#### 💡 Explanation")

    with chat_bubble("user"):

        st.markdown(
            record.get("question", "")
        )

    with chat_bubble("assistant"):

        st.markdown(
            record.get("answer", "")
        )

        if record.get("model") and record["model"] != FAQ_MODEL_LABEL:
            st.caption(f"Model: {record['model']}")

    for message in record.get("messages", []):

        with chat_bubble(message["role"]):

            st.markdown(message["content"])

            if message.get("model"):
                st.caption(f"Model: {message['model']}")

    question = st.chat_input(
        "Ask a follow-up question..."
    )

    if not question:
        return

    with chat_bubble("user"):

        st.markdown(question)

    # The whole conversation so far, so "this" / "that example"
    # in the new question makes sense to the model.
    history = [
        {"role": "user", "content": record.get("question", "")},
        {"role": "assistant", "content": record.get("answer", "")},
    ] + list(record.get("messages", []))

    with chat_bubble("assistant"):

        answer = faq_answer(question)

        if answer:

            st.markdown(answer)
            model = None

        else:

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


def project_zip_bytes(project):
    """The whole project as a .zip, built in memory."""

    project_dir = os.path.join(GENERATED_PROJECTS_DIR, project)

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in get_project_files(project):
            archive.write(
                os.path.join(project_dir, relative),
                arcname=os.path.join(project, relative)
            )

    return buffer.getvalue()


# Questions sent by the action buttons under a project.
PROJECT_ACTIONS = {
    "run": (
        "▶ How to run",
        "How do I run this project step by step? Include the database "
        "setup, configuration and the URL to open."
    ),
    "structure": (
        "🔍 Explain structure",
        "Explain the structure of this project: what each folder and "
        "file does and how a request flows through it."
    ),
    "feature": (
        "✏️ Add a feature",
        "Suggest 3 useful features I could add to this project, and for "
        "each one list which files I would change and how."
    ),
}


def queue_project_question(text):
    st.session_state.pending_question = text


def queue_project_tests():
    st.session_state.pending_tests = True


def render_project_files(project, files):
    """File list on the left, the selected file's code on the right."""

    if not files:
        st.caption("No files found in this project.")
        return

    left, right = st.columns([1, 2.6])

    with left:
        selected = st.radio(
            "Files",
            files,
            key=f"file_pick_{project}",
            label_visibility="collapsed"
        )

    with right:
        st.caption(f"`{selected}`")
        st.code(
            read_project_file(project, selected),
            language=get_language(selected)
        )


def render_project_actions(project):

    with st.container(key="project_actions"):

        columns = st.columns([1.25, 1, 1.3, 1.15, 1])

        try:
            zip_bytes = project_zip_bytes(project)
        except Exception:
            zip_bytes = None

        if zip_bytes:
            columns[0].download_button(
                "📥 Download ZIP",
                data=zip_bytes,
                file_name=f"{project}.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
                key=f"zip_{project}"
            )

        for column, (key, (label, question)) in zip(
            columns[1:4], PROJECT_ACTIONS.items()
        ):
            column.button(
                label,
                key=f"action_{key}_{project}",
                use_container_width=True,
                on_click=queue_project_question,
                args=(question,)
            )

        columns[4].button(
            "🧪 Run tests",
            key=f"action_tests_{project}",
            use_container_width=True,
            on_click=queue_project_tests
        )

    render_single_file_download(project)


def render_single_file_download(project):
    """Dropdown under Download ZIP: pick one file and download only it."""

    files = get_project_files(project)

    if not files:
        return

    pick_column, button_column = st.columns([3, 1.25])

    with pick_column:
        selected = st.selectbox(
            "Download a single file",
            files,
            index=None,
            placeholder="Download a single file…",
            key=f"single_file_{project}",
            label_visibility="collapsed"
        )

    with button_column:

        if selected:

            path = os.path.join(GENERATED_PROJECTS_DIR, project, selected)

            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except OSError:
                data = None

            if data is not None:
                st.download_button(
                    "⬇ Download file",
                    data=data,
                    file_name=os.path.basename(selected),
                    use_container_width=True,
                    key=f"single_file_button_{project}"
                )

        else:
            st.button(
                "⬇ Download file",
                disabled=True,
                use_container_width=True,
                key=f"single_file_disabled_{project}"
            )


def test_report_markdown(report):
    """PHP syntax test results as a chat message."""

    if not report.get("php_available", True):
        return (
            "PHP is not installed on this server, so the syntax test "
            "could not run. Run `php -l <file>` on your computer instead."
        )

    lines = [
        f"### Test results\n"
        f"**{report.get('passed', 0)}** passed, "
        f"**{report.get('failed', 0)}** failed "
        f"(of {report.get('total_files', 0)} PHP files)."
    ]

    for item in report.get("results", []):
        name = os.path.basename(str(item.get("file", "")))
        if item.get("status") == "FAIL":
            lines.append(f"- ❌ `{name}`: {item.get('error')}")
        else:
            lines.append(f"- ✅ `{name}`")

    return "\n".join(lines)


def render_chat(project):

    project_dir = os.path.join(GENERATED_PROJECTS_DIR, project)

    if not os.path.isdir(project_dir):
        st.warning(f"Project `{project}` no longer exists.")
        return

    record = get_or_create_history(project, project_dir)

    files = get_project_files(project)

    st.markdown(f"#### 📦 {project}")

    messages = record.get("messages", [])

    def project_panel():
        with st.expander(f"📁 Files ({len(files)})"):
            render_project_files(project, files)
        render_project_actions(project)

    if not messages:
        st.info(
            "This project was generated before chat history existed. "
            "Ask anything about it below."
        )
        project_panel()

    for index, message in enumerate(messages):

        with chat_bubble(message["role"]):

            st.markdown(message["content"])

            # The first answer (the generation summary) carries the
            # files and the action buttons, like the mockup.
            if index == 1 and message["role"] == "assistant":
                project_panel()

    if len(messages) == 1:
        project_panel()

    typed = st.chat_input(f"Ask anything about {project}…")

    # ---------------- Run tests button ----------------
    if not typed and st.session_state.pop("pending_tests", False):

        with chat_bubble("user"):
            st.markdown("🧪 Run tests")

        with chat_bubble("assistant"):
            try:
                with st.spinner("Checking PHP syntax..."):
                    report = PHPTester().test_project(project_dir)
                answer = test_report_markdown(report)
            except Exception as e:
                answer = f"Could not run the tests: `{e}`"
            st.markdown(answer)

        append_message(record, "user", "🧪 Run tests")
        append_message(record, "assistant", answer)
        return

    question = typed or st.session_state.pop("pending_question", None)

    if not question:
        return

    with chat_bubble("user"):
        st.markdown(question)

    earlier_messages = list(messages)

    with chat_bubble("assistant"):

        try:

            agent = PHPCodeUnderstandingAgent()

            with st.spinner("Reading the project..."):

                prompt = agent.build_prompt(
                    project_path=project_dir,
                    question=question,
                    history=earlier_messages,
                    requirement=record.get("requirement")
                )

            answer = st.write_stream(agent.ask_stream(prompt))

        except Exception as e:

            show_error("Error while answering.", e)

            return

        model = agent.model_manager.last_model

        if model:
            st.caption(f"Model: {model}")

    append_message(record, "user", question)
    append_message(record, "assistant", answer)


# ============================================================
# HOME: one chat box for questions and new projects
# ============================================================

# (label shown on the card, prompt that is sent)
EXAMPLE_PROMPTS = [
    ("BUILD", "Login & register system with MySQL and sessions",
     "Create a PHP login and registration system with MySQL, "
     "password hashing and sessions."),
    ("BUILD", "REST API for products with CRUD using PDO",
     "Create a REST API in PHP for products with CRUD operations "
     "using PDO."),
    ("BUILD", "Hotel table booking with date & time slots",
     "Build a hotel table booking system in PHP with date and "
     "time slots."),
    ("EXPLAIN", "PDO kya hai aur mysqli se safe kyun hai?",
     "PDO kya hai aur mysqli se safe kyun hai?"),
    ("EXPLAIN", "Sessions vs cookies in PHP",
     "Explain sessions vs cookies in PHP."),
    ("EXPLAIN", "How does password_hash() work?",
     "How does password_hash() and password_verify() work?"),
]

ATTACHMENT_TYPES = [
    "png", "jpg", "jpeg", "webp", "gif",
    "txt", "md", "php", "html", "css", "js", "json", "sql",
    "csv", "xml", "pdf", "docx",
]


def queue_prompt(prompt):
    st.session_state.pending_prompt = prompt


# Shown as the "model" of answers that came from agents/faq.py.
FAQ_MODEL_LABEL = "built-in FAQ (no AI call)"


def faq_answer(question):
    """Answer from the built-in FAQ about this app, or None (no LLM)."""

    try:
        return answer_faq(
            question,
            per_user=GENERATIONS_PER_WINDOW,
            window=WINDOW_SECONDS // 60,
            global_limit=GLOBAL_GENERATIONS_PER_HOUR,
        )
    except Exception as e:
        print(f"FAQ lookup failed: {e}")
        return None


def attachment_from_chat_input(value):
    """Save the file sent with the chat box, in the old upload format."""

    files = getattr(value, "files", None) or []

    if not files:
        return None

    uploaded = files[0]

    path = save_uploaded_file(uploaded)

    return {
        "name": uploaded.name,
        "path": path,
        "type": (
            "photo"
            if (uploaded.type or "").startswith("image/")
            else "file"
        ),
        "size": uploaded.size,
    }


def show_limit_warning(reason, wait_seconds):

    if reason == "global":
        st.warning(
            "The app has reached its generation limit for this hour "
            "(shared by all users). Try again in about "
            f"{format_wait(wait_seconds)}. Explanations still work."
        )
    else:
        st.warning(
            f"You've used all {GENERATIONS_PER_WINDOW} free generations "
            f"for now. Try again in about {format_wait(wait_seconds)}. "
            "Explanations still work."
        )


def handle_request(requirement, attachment=None):
    """
    Answer a question or build a project, shown as a chat.
    Returns True when the finished chat should be opened (rerun).
    """

    with chat_bubble("user"):

        st.markdown(requirement)

        if attachment:
            icon = "🖼️" if attachment["type"] == "photo" else "📎"
            st.caption(
                f"{icon} {attachment['name']} • "
                f"{format_file_size(attachment['size'])}"
            )

    # ---------------- question about this app: no LLM ----------------
    answer = None if attachment else faq_answer(requirement)

    if answer:

        with chat_bubble("assistant"):
            st.markdown(answer)

        try:
            explanation_id = save_explanation(
                requirement, answer, FAQ_MODEL_LABEL
            )
        except Exception as e:
            st.caption(f"Could not save this answer: {e}")
            return False

        open_explanation(explanation_id)
        return True

    # ---------------- explanation ----------------
    if detect_request_type(requirement, "Auto") == EXPLAIN:

        with chat_bubble("assistant"):
            explanation_id = show_explanation(requirement)

        if explanation_id:
            open_explanation(explanation_id)
            return True

        return False

    # ---------------- new project ----------------
    ok, reason, wait_seconds, slot_token = (
        get_generation_limiter().try_acquire(current_user_id())
    )

    if not ok:
        with chat_bubble("assistant"):
            show_limit_warning(reason, wait_seconds)
        return False

    project_name = make_project_name(requirement)

    with chat_bubble("assistant"):

        status = st.empty()
        progress = st.progress(0)
        live = st.empty()

        try:

            status.info(
                "Planning the project..."
                + (" (using your attachment)" if attachment else "")
            )

            progress.progress(10)

            result = PHPVibeCoder(max_retries=3).run(
                requirement=requirement,
                project_name=project_name,
                attachment_path=(attachment or {}).get("path"),
                attachment_type=(attachment or {}).get("type"),
                on_progress=make_live_preview(live, status, progress)
            )

        except Exception as e:

            # Failed runs do not use up a generation.
            get_generation_limiter().release(current_user_id(), slot_token)

            status.empty()
            progress.empty()
            live.empty()

            show_error("Error while running Vibe Coder.", e)

            return False

        status.empty()
        progress.empty()
        live.empty()

    project = result.get("project", project_name)

    st.session_state.generation_response = result
    st.session_state.current_project = project

    create_history(
        project=project,
        requirement=requirement,
        summary=build_generation_summary(
            result,
            get_project_files(project)
        ),
        model=result.get("model")
    )

    # Open the project's chat: the summary is the first answer and the
    # question box sits at the bottom for follow-ups.
    open_chat(project)

    return True


def render_home():

    value = st.chat_input(
        "Ask a PHP question or describe a project…",
        accept_file=True,
        file_type=ATTACHMENT_TYPES,
        key="home_input"
    )

    prompt, attachment = None, None

    if value:
        prompt = (getattr(value, "text", None) or "").strip()

        try:
            attachment = attachment_from_chat_input(value)
        except Exception as e:
            st.error(f"Could not save the attachment: {e}")

        if attachment and not prompt:
            prompt = "Create a PHP project based on the attached file."

    else:
        prompt = (st.session_state.pop("pending_prompt", None) or "").strip()

    if prompt:

        if handle_request(prompt, attachment):
            st.rerun()

        return

    # ---------------- empty state ----------------
    st.markdown(
        '<div class="vc-hero"><div class="vc-logo">PHP</div>'
        "<h1>PHP Vibe Coding</h1>"
        "<p>Describe a project to generate it, or ask any PHP "
        "question.</p></div>",
        unsafe_allow_html=True
    )

    with st.container(key="example_chips"):

        for row in range(0, len(EXAMPLE_PROMPTS), 3):

            columns = st.columns(3)

            for column, (kind, label, prompt_text) in zip(
                columns, EXAMPLE_PROMPTS[row:row + 3]
            ):

                column.button(
                    f"**{kind}**  \n{label}",
                    key=f"example_{row}_{label}",
                    use_container_width=True,
                    on_click=queue_prompt,
                    args=(prompt_text,)
                )

    st.caption(
        "Projects open as a chat — keep asking questions about them. "
        "Attach a file or screenshot with the ＋ in the box."
    )


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

    render_home()


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