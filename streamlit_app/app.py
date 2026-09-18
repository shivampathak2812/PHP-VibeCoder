import os
import sys
import types
import shutil
from pathlib import Path

import streamlit as st


# ============================================================
# TORCHVISION STUB
# ============================================================
# We only use sentence-transformers/all-MiniLM-L6-v2, a pure text
# embedding model. It never needs torchvision. But Streamlit's
# module inspection can trigger `transformers`'s lazy loader to
# probe torchvision-dependent submodules, causing a hard crash
# (ModuleNotFoundError) even though the actual code path is never
# used. Stub the two specific broken imports so the probe finds
# something importable and moves on, without installing the real
# (huge, CUDA-pulling) torchvision package.

if "torchvision" not in sys.modules:
    try:
        import torchvision  # noqa: F401
    except ImportError:
        _tv = types.ModuleType("torchvision")

        _tv_io = types.ModuleType("torchvision.io")
        _tv_io.read_image = lambda *a, **kw: None

        _tv_transforms = types.ModuleType("torchvision.transforms")
        _tv_transforms_v2 = types.ModuleType("torchvision.transforms.v2")
        _tv_transforms_v2_functional = types.ModuleType(
            "torchvision.transforms.v2.functional"
        )

        _tv.io = _tv_io
        _tv.transforms = _tv_transforms
        _tv_transforms.v2 = _tv_transforms_v2
        _tv_transforms_v2.functional = _tv_transforms_v2_functional

        sys.modules["torchvision"] = _tv
        sys.modules["torchvision.io"] = _tv_io
        sys.modules["torchvision.transforms"] = _tv_transforms
        sys.modules["torchvision.transforms.v2"] = _tv_transforms_v2
        sys.modules["torchvision.transforms.v2.functional"] = (
            _tv_transforms_v2_functional
        )


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

mode = st.sidebar.radio(
    "Operation",
    [
        "Generate Project",
        "Project Workspace",
        "Understand Code",
        "Refactor Code",
        "Test Project"
    ]
)

st.sidebar.markdown(
    "---"
)

st.sidebar.caption(
    "PHP 8.x • Gemini • RAG • FAISS"
)


# ============================================================
# 1. GENERATE PROJECT
# ============================================================

if mode == "Generate Project":

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
                    attachment_type=attachment_type
                )

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

                st.error(
                    "Error while running Vibe Coder."
                )

                st.exception(e)


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

                        answer = agent.understand(
                            project_path=os.path.join(
                                GENERATED_PROJECTS_DIR,
                                project
                            ),
                            question=question
                        )

                        st.session_state.understanding_answer = answer

                    except Exception as e:

                        st.error(
                            "Error while understanding project."
                        )

                        st.exception(e)

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

            if refactor:

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

                        result = agent.refactor(
                            project_path=os.path.join(
                                GENERATED_PROJECTS_DIR,
                                project
                            ),
                            file_path=file_path
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

                    st.error(
                        "Error while refactoring."
                    )

                    st.exception(e)


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

                    st.error(
                        "Error while testing project."
                    )

                    st.exception(e)

        display_test_result(
            st.session_state.last_test_result
        )