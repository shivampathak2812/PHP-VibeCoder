from pathlib import Path

from agents.rag_agent import RAGAgent
from agents.project_writer import ProjectWriter
from agents.gemini_model_manager import GeminiModelManager


class PHPCodeAgent:

    def __init__(self, top_k=5):
        self.rag_agent = RAGAgent(top_k=top_k)
        self.project_writer = ProjectWriter()
        self.model_manager = GeminiModelManager()

    def generate_code(
        self,
        requirement,
        project_name="php-project",
        attachment_path=None,
        attachment_type=None
    ):

        # ---------------------------------------------------------
        # Get relevant PHP documentation from RAG
        # ---------------------------------------------------------

        context = self.rag_agent.context_builder.build_context(
            requirement
        )

        # ---------------------------------------------------------
        # Attachment information
        # ---------------------------------------------------------

        attachment_instruction = ""

        if attachment_path:

            attachment_name = Path(
                attachment_path
            ).name

            if attachment_type == "photo":

                attachment_instruction = f"""
USER PROVIDED IMAGE:

The user has provided an image named:
{attachment_name}

The image is part of the project requirement.

Analyze the image carefully and use it as a design/reference
for the generated PHP project.

If the image represents:

- a website UI
- a dashboard
- a form
- a webpage
- an application screen
- a layout
- a component

then reproduce the relevant structure, layout, components,
styling requirements, fields, buttons, navigation, and
visual behavior in the generated PHP project.

Do not ignore the image.
"""

            else:

                attachment_instruction = f"""
USER PROVIDED FILE:

The user has provided a file named:
{attachment_name}

Use the uploaded file as additional project input.

Analyze its relevant contents and incorporate them into
the generated PHP project where appropriate.

Do not ignore the uploaded file.
"""

        # ---------------------------------------------------------
        # Create prompt for Gemini
        # ---------------------------------------------------------

        prompt = f"""
You are an expert PHP 8.x developer and software architect.

Your task is to generate a complete PHP project based on the
user's requirement and any optional user-provided attachment.

USER REQUIREMENT:
{requirement}

{attachment_instruction}

PHP DOCUMENTATION RETRIEVED FROM RAG:
{context}

Follow these requirements:

1. Understand the user's requirement completely.
2. Use any uploaded file or image as additional project input.
3. If an image is provided, analyze the image and implement
   the relevant UI/design shown in it.
4. Identify the functional requirements.
5. Design a suitable PHP 8.x architecture.
6. Identify all required files.
7. Generate complete working PHP code.
8. Use modern PHP 8.x practices.
9. If MySQL is required, use PDO.
10. Use prepared statements for SQL queries.
11. Use password_hash() when storing passwords.
12. Include proper error handling.
13. Do not use deprecated mysql_* functions.
14. Do not put passwords or API keys directly in source code.
15. Use the provided PHP documentation as the primary PHP
    knowledge source.
16. Do not generate placeholder code.
17. Do not claim that the code has been tested unless it has
    actually been tested.
18. Make the generated project match the user's requirement,
    not a fixed example or predefined application.
19. Do not introduce unrelated features.
20. Generate all files required for the project to work.

Return the answer using exactly these sections:

PROJECT OVERVIEW

Explain what the project does.

REQUIREMENTS

List the requirements understood from the user.

ARCHITECTURE

Explain the architecture.

PROJECT STRUCTURE

Show the complete folder and file structure.

FILES

For every required file provide:

FILE: path/to/file.php

Then provide the complete code for that file.

Also provide complete code for SQL, JSON, configuration,
HTML, CSS, JavaScript, and other required files.

Each file must have exactly one FILE declaration.

Use this format:

FILE: index.php
```php
complete code

FILE: css/style.css

complete code

FILE: js/app.js

complete code

Do not combine multiple files into one code block.

DATABASE

If a database is required, explain:

Database name
Tables
Columns
Primary keys
Foreign keys
Indexes
Relationships

Also provide the complete SQL schema.

API ENDPOINTS

If the project is an API, explain:

HTTP method
Endpoint
Purpose
Request body
Response

SETUP

Explain how to:

Install dependencies.
Configure the database.
Configure environment variables.
Start the application.
Test the application.

IMPORTANT:

Generate actual complete code.

Do not use placeholders such as:

TODO
[code here]
[implementation here]
...
"""

        # ---------------------------------------------------------
        # Gemini 3.6 Flash -> Gemini 3.5 Flash automatic fallback
        # ---------------------------------------------------------

        print("\nGenerating project...")
        print(
            "Model priority: "
            "Gemini 3.6 Flash -> Gemini 3.5 Flash"
        )

        if attachment_path:
            print(
                f"Attachment included: {attachment_path}"
            )

        result = self.model_manager.generate(
            prompt,
            attachment_path=attachment_path,
            attachment_type=attachment_type
        )

        if not result.get("success"):
            raise RuntimeError(
                f"Gemini generation failed: "
                f"{result.get('error')}"
            )

        response = result["response"]
        selected_model = result["model"]

        print(
            f"\nMODEL USED: {selected_model}"
        )

        # ---------------------------------------------------------
        # Write generated project
        # ---------------------------------------------------------

        result = self.project_writer.write_project(
            project_name,
            response
        )

        return {
            "project_dir": result["project_dir"],
            "files_created": result["files_created"],
            "file_count": result["file_count"],
            "gemini_response": response,
            "model": selected_model
        }

    if __name__ == "__main__":

        print("=" * 70)
        print("PHP VibeCoder - Code Agent")
        print("=" * 70)
        print("Code Agent is ready.")
        print(
            "Use PHPCodeAgent.generate_code() "
            "with a dynamic requirement."
        )