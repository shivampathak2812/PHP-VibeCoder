# PHP Vibe Coder

PHP Vibe Coder is an AI-assisted development workspace for creating and working with PHP projects. It turns a plain-English requirement into a PHP project, checks the generated PHP files, and helps developers understand or refactor existing code.

The application is built with Streamlit and uses Google Gemini for generation and code assistance. A local PHP documentation knowledge base, sentence-transformer embeddings, and FAISS provide relevant PHP context to the AI before it responds.

## What it can do

- Generate a complete PHP project from a written requirement.
- Accept an optional document or image as additional project input.
- Use PHP documentation through retrieval-augmented generation (RAG).
- Browse generated project files in a workspace view.
- Explain an existing PHP project, including its structure and code flow.
- Refactor a selected PHP file while preserving its intended behavior.
- Check every PHP file with PHP's built-in syntax validator.
- Send syntax failures to a debugging agent and retry validation up to three times.
- Keep generated projects in `generated_projects/` for later review.

## How the workflow works

```text
Requirement or attachment
          |
          v
PHP documentation retrieval (Sentence Transformers + FAISS)
          |
          v
Gemini code generation
          |
          v
Write project files to generated_projects/
          |
          v
PHP syntax validation -> debug failures -> validate again
```

## Technology

- Python 3.13 or newer
- Streamlit
- Google Gemini through `google-genai`
- FAISS for vector search
- Sentence Transformers with `all-MiniLM-L6-v2` embeddings
- BeautifulSoup and lxml for document processing
- PHP 8.x CLI for syntax checks
- Poetry for Python dependency management

## Project structure

```text
.
├── agents/                  AI agents and project workflow
│   ├── code_agent.py        Generates PHP code with Gemini and RAG
│   ├── vibe_coder.py        Coordinates generation, testing, and retries
│   ├── php_tester.py        Runs `php -l` on PHP files
│   ├── debug_agent.py       Repairs files with syntax errors
│   ├── project_analyzer.py  Extracts PHP project structure and symbols
│   ├── code_understanding_agent.py
│   ├── refactor_agent.py
│   ├── project_writer.py
│   └── gemini_model_manager.py
├── rag/                     Documentation ingestion and retrieval
├── knowledge_base/          PHP documentation, chunks, metadata, and FAISS index
├── streamlit_app/app.py     Main user interface
├── generated_projects/      Generated and example PHP projects
├── uploaded_files/          Files uploaded through the UI
├── .streamlit/config.toml   Streamlit settings
├── pyproject.toml           Project metadata and dependencies
└── poetry.lock              Locked dependency versions
```

## Requirements

Install the following before running the application:

1. Python 3.13 or newer.
2. Poetry.
3. PHP 8.x available on your system `PATH`.
4. A Google Gemini API key.

Check the PHP installation with:

```powershell
php -v
```

The application can start without PHP, but project validation will fail until the PHP CLI is installed and available as `php`.

## Setup

Open PowerShell in the project directory and install the dependencies:

```powershell
poetry install
```

Create a `.env` file in the project root and add your Gemini key:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Keep this file private. Do not commit API keys or generated `.env` files to source control.

## Run the application

```powershell
poetry run streamlit run streamlit_app/app.py
```

Streamlit will print a local URL, normally `http://localhost:8501`.

## Using the application

### Generate Project

Describe the PHP application you want to build, enter a project name, and optionally upload a file or image. The generated project is written to `generated_projects/<project-name>/`.

The generator uses the PHP RAG context, calls the configured Gemini model, writes the returned files, and validates the PHP syntax. If validation fails, the application attempts to repair the affected files and test them again.

### Project Workspace

Select a generated project to view its file tree and inspect the contents of individual files.

### Understand Code

Select a project and ask a question about its architecture, request flow, classes, methods, routing, or database usage. The analyzer provides the project context and the RAG layer provides supporting PHP documentation.

### Refactor Code

Select a PHP file and describe the improvement you want. The refactor agent sends the project context and selected file to Gemini, then writes the returned PHP code back to the selected file.

Review refactored files before using them in production.

### Test Project

The tester recursively finds PHP files and runs:

```text
php -l path/to/file.php
```

This checks PHP syntax only. It does not run the application, execute database queries, call HTTP endpoints, or perform integration tests.

## RAG knowledge base

The repository includes a prepared PHP knowledge base:

- Source documentation: `knowledge_base/php/`
- Text chunks: `knowledge_base/chunks/php_chunks.jsonl`
- FAISS index: `knowledge_base/processed/php_faiss.index`
- Chunk metadata: `knowledge_base/processed/php_metadata.json`

If the source documentation changes, rebuild the chunks and index:

```powershell
poetry run python rag/ingest.py
poetry run python rag/build_index.py
```

The index builder downloads or loads the `sentence-transformers/all-MiniLM-L6-v2` model as required by the local Python environment.

## Programmatic usage

The main workflow can also be used from Python:

```python
from agents.vibe_coder import PHPVibeCoder

coder = PHPVibeCoder(max_retries=3)

result = coder.run(
    requirement="Build a PHP login application with MySQL and session-based authentication.",
    project_name="login-app",
)

print(result["success"])
print(result["project_dir"])
```

Other useful entry points include:

```python
from agents.project_analyzer import PHPProjectAnalyzer
from agents.php_tester import PHPTester
from agents.refactor_agent import PHPRefactorAgent
from agents.code_understanding_agent import PHPCodeUnderstandingAgent
```

## Configuration notes

- The Streamlit upload limit is configured to 500 MB in `.streamlit/config.toml`.
- Gemini generation tries the configured primary model and then the configured fallback model when necessary.
- The default project output directory is `generated_projects/`.
- Several scripts currently use the repository path `D:\PHP-VibeCoder` internally. If the project is moved or cloned to another directory, update those path constants before using the RAG and project-writing scripts.

## Testing and production considerations

The current repository does not include a populated automated test suite. The built-in PHP tester performs syntax checks only, so generated code should still be reviewed and tested against its real database, web server, environment variables, and application requirements.

Generated code is AI-produced and should be treated as a starting point. Before deployment:

- Review authentication, authorization, input validation, and database queries.
- Check all secrets and environment configuration.
- Run the generated application in a safe environment.
- Add project-specific unit and integration tests.
- Verify dependencies and PHP runtime compatibility.

## Troubleshooting

### `GEMINI_API_KEY not found in .env`

Create `.env` in the project root and add a valid `GEMINI_API_KEY` value. Restart Streamlit after changing the file.

### `PHP executable was not found`

Install PHP 8.x and add its directory to `PATH`. Confirm that `php -v` works in the same terminal used to start the application.

### RAG index files are missing

Run the ingestion and index commands in the [RAG knowledge base](#rag-knowledge-base) section. Confirm that both files in `knowledge_base/processed/` exist afterward.

### Generation or model loading is slow

The first run may download the sentence-transformer model and initialize FAISS. Gemini requests also depend on network access, API quota, and model availability.

## License

No license file is currently included in this repository. Add a license before distributing the project.
