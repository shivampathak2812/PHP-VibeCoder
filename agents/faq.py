"""
Built-in answers to questions about PHP Vibe Coder itself
("what is the scope of this project?", "which models does it use?").

These are answered from the text below, with NO LLM call, so they are
instant, always correct and cost no quota. There is no FAQ page in the
UI: the chat simply checks here first.

Matching is deliberately strict, so normal PHP questions ("variable
scope in PHP", "how do I test a login form") still go to the model:
a question matches only if it clearly talks about this app.
"""

import re

from agents.reply_language import detect_reply_language, ENGLISH


# Words that show the question is about this app, not about PHP.
APP_REFERENCE = re.compile(
    r"(vibe ?coder|vibe ?coding|vibecoder"
    r"|\b(this|your|is|iss|ye|yeh|tumhare|aapke)\s+"
    r"(app|application|tool|project|website|platform|software|system)\b"
    r"|\bthe (app|tool|platform)\b)",
    re.IGNORECASE,
)


# Each entry:
#   strong: patterns that are enough on their own
#   topic:  patterns that count only together with APP_REFERENCE
FAQ = [
    {
        "id": "overview",
        "strong": [
            r"\bwhat is (php )?vibe ?cod(er|ing)\b",
            r"\b(php )?vibe ?cod(er|ing) (kya|kya hai|kya hota hai)\b",
            r"\babout (php )?vibe ?cod(er|ing)\b",
        ],
        "topic": [
            r"\b(what is|what does|tell me about|introduce|overview)\b",
            r"\b(kya hai|kya karta|kya karti|ke baare|ke bare)\b",
        ],
        "en": (
            "**PHP Vibe Coding** is an AI assistant for PHP.\n\n"
            "- **Build:** describe an app in plain English or Hinglish "
            "and it writes a complete PHP + MySQL project, checks the "
            "PHP syntax, fixes errors automatically and saves it.\n"
            "- **Explain:** ask any PHP question and get a short, clear "
            "explanation with small examples.\n"
            "- **Chat about a project:** after a project is generated, "
            "ask how it works, how to run it, or what to change.\n"
            "- **Download:** get the whole project as a ZIP or any "
            "single file."
        ),
        "hinglish": (
            "**PHP Vibe Coding** PHP ke liye ek AI assistant hai.\n\n"
            "- **Build:** apni app English ya Hinglish mein describe "
            "karo, yeh poora PHP + MySQL project likhta hai, PHP syntax "
            "check karta hai, errors khud theek karta hai aur save "
            "karta hai.\n"
            "- **Explain:** PHP ka koi bhi sawaal poocho, chhota aur "
            "saaf explanation chhote examples ke saath milta hai.\n"
            "- **Project chat:** project banne ke baad poocho ki woh "
            "kaise kaam karta hai, kaise chalana hai, ya kya badalna hai.\n"
            "- **Download:** poora project ZIP mein ya koi ek file."
        ),
    },
    {
        "id": "scope",
        "strong": [
            r"\bscope of (the |this |your )?(project|app|application|tool|vibe ?cod(er|ing))\b",
            r"\b(project|app|tool|vibe ?cod(er|ing)) (ka|ki) scope\b",
            r"\bwhat can (you|it|this (app|tool|project)) (do|build|make)\b",
            r"\blimitations? of (the |this |your )?(project|app|tool|vibe ?cod(er|ing))\b",
        ],
        "topic": [
            r"\bscope\b", r"\blimitations?\b", r"\bcan(not|'t)? (do|build)\b",
            r"\bkya kya (kar|bana)\b", r"\bkya nahi\b", r"\bfeatures?\b",
        ],
        "en": (
            "### Scope\n"
            "**What it does**\n"
            "- Generates complete PHP 8 projects with plain PHP, PDO and "
            "MySQL: login systems, CRUD apps, REST APIs, blogs, booking "
            "systems, dashboards and similar web apps.\n"
            "- Can use an attached file or screenshot as input for the "
            "project.\n"
            "- Explains PHP concepts in English, Hinglish or Hindi.\n"
            "- Answers questions about a generated project, using its "
            "real code.\n"
            "- Checks every PHP file's syntax and fixes errors "
            "automatically.\n"
            "- Lets you download the project as a ZIP or any single "
            "file, and keeps a history of chats.\n\n"
            "**What it does not do**\n"
            "- It does not host or deploy the project, and does not "
            "create or run your database: you import `schema.sql` "
            "yourself.\n"
            "- Testing is a syntax check (`php -l`), not a run of the "
            "app in a browser.\n"
            "- It is built for plain PHP, not frameworks such as "
            "Laravel or Symfony.\n"
            "- Very large systems (an ERP with dozens of modules) are "
            "better built one module at a time."
        ),
        "hinglish": (
            "### Scope\n"
            "**Kya karta hai**\n"
            "- Plain PHP, PDO aur MySQL mein poore PHP 8 projects banata "
            "hai: login system, CRUD apps, REST API, blog, booking "
            "system, dashboard jaisi web apps.\n"
            "- Attach ki hui file ya screenshot ko project ke input ki "
            "tarah use kar sakta hai.\n"
            "- PHP concepts English, Hinglish ya Hindi mein samjhata hai.\n"
            "- Bane hue project ke baare mein uske asli code se sawaalon "
            "ke jawaab deta hai.\n"
            "- Har PHP file ka syntax check karta hai aur errors khud "
            "theek karta hai.\n"
            "- Project ZIP mein ya koi ek file download karne deta hai, "
            "aur chats ki history rakhta hai.\n\n"
            "**Kya nahi karta**\n"
            "- Project host ya deploy nahi karta, aur database banata ya "
            "chalata nahi: `schema.sql` aapko khud import karni hoti hai.\n"
            "- Testing sirf syntax check (`php -l`) hai, browser mein app "
            "chala ke test nahi hota.\n"
            "- Plain PHP ke liye bana hai, Laravel ya Symfony jaise "
            "frameworks ke liye nahi.\n"
            "- Bahut bade system (dozens of modules wala ERP) ek-ek "
            "module karke banwana better hai."
        ),
    },
    {
        "id": "parts",
        "strong": [
            r"\bparts of (the |this |your )?(project|app|application|tool|system|vibe ?cod(er|ing))\b",
            r"\b(components|modules|architecture) of (the |this |your )?(project|app|application|tool|system|vibe ?cod(er|ing))\b",
            r"\b(project|app|tool|vibe ?cod(er|ing)) (ke|ka) (parts|components|modules|architecture)\b",
        ],
        "topic": [
            r"\bparts?\b", r"\bcomponents?\b", r"\bmodules?\b",
            r"\barchitecture\b", r"\bstructure\b", r"\bhow (is it|it is) built\b",
            r"\bkaise bana\b",
        ],
        "en": (
            "### Parts of the project\n"
            "1. **Chat UI** (`streamlit_app/app.py`): Streamlit app with "
            "the chat box, history, file viewer and downloads.\n"
            "2. **Intent router** (`agents/intent_router.py`): decides "
            "if a message is a question (explain) or a project "
            "request (build). Rules first, a small model only if unsure.\n"
            "3. **FAQ** (`agents/faq.py`): answers questions about this "
            "app without any AI call.\n"
            "4. **RAG knowledge base** (`rag/`): the PHP manual split "
            "into chunks, turned into embeddings and stored in a FAISS "
            "index; the most relevant parts are added to every prompt.\n"
            "5. **Code agent** (`agents/code_agent.py`) and **project "
            "writer**: write the project and save each file.\n"
            "6. **PHP tester** (`agents/php_tester.py`): runs `php -l` "
            "on every PHP file.\n"
            "7. **Debug agent** (`agents/debug_agent.py`): fixes files "
            "that fail the test, then they are tested again.\n"
            "8. **Explain agent** and **project chat agent**: answer PHP "
            "questions and questions about a generated project.\n"
            "9. **Model manager** (`agents/gemini_model_manager.py`, "
            "`agents/fallback_providers.py`): picks Gemini, Groq or "
            "NVIDIA models and switches when one is busy.\n"
            "10. **Rate limiter and history** "
            "(`streamlit_app/rate_limiter.py`, `history_store.py`): "
            "generation limits and saved chats."
        ),
        "hinglish": (
            "### Project ke parts\n"
            "1. **Chat UI** (`streamlit_app/app.py`): Streamlit app, "
            "jisme chat box, history, file viewer aur downloads hain.\n"
            "2. **Intent router** (`agents/intent_router.py`): decide "
            "karta hai ki message sawaal hai (explain) ya project ki "
            "request (build). Pehle rules, confuse ho to chhota model.\n"
            "3. **FAQ** (`agents/faq.py`): is app ke baare mein sawaalon "
            "ke jawaab bina AI call ke deta hai.\n"
            "4. **RAG knowledge base** (`rag/`): PHP manual ke chunks "
            "ki embeddings FAISS index mein rakhi hain; sabse relevant "
            "hisse har prompt mein jaate hain.\n"
            "5. **Code agent** (`agents/code_agent.py`) aur **project "
            "writer**: project likhte hain aur har file save karte hain.\n"
            "6. **PHP tester** (`agents/php_tester.py`): har PHP file "
            "par `php -l` chalata hai.\n"
            "7. **Debug agent** (`agents/debug_agent.py`): fail hui "
            "files theek karta hai, phir dobara test hota hai.\n"
            "8. **Explain agent** aur **project chat agent**: PHP ke "
            "sawaal aur bane hue project ke sawaalon ke jawaab dete hain.\n"
            "9. **Model manager** (`agents/gemini_model_manager.py`, "
            "`agents/fallback_providers.py`): Gemini, Groq ya NVIDIA "
            "model chunta hai aur busy hone par doosra use karta hai.\n"
            "10. **Rate limiter aur history** "
            "(`streamlit_app/rate_limiter.py`, `history_store.py`): "
            "generation limit aur saved chats."
        ),
    },
    {
        "id": "workflow",
        "strong": [
            r"\bhow does (php )?vibe ?cod(er|ing) work\b",
            r"\b(php )?vibe ?cod(er|ing) kaise (kaam|work) kar(ta|ti)\b",
            r"\b(workflow|pipeline|flow) of (the |this |your )?(project|app|tool|vibe ?cod(er|ing))\b",
        ],
        "topic": [
            r"\bhow does (it|this) work\b", r"\bhow (it|this) works\b",
            r"\bworkflow\b", r"\bpipeline\b", r"\bkaise kaam\b",
            r"\bkaise work\b", r"\bprocess\b",
        ],
        "en": (
            "### How it works\n"
            "1. You type a request.\n"
            "2. The intent router decides: explanation or new project.\n"
            "3. If a very similar project was built before, it is "
            "reused or only the changed files are written.\n"
            "4. Otherwise the most relevant parts of the PHP manual are "
            "found with semantic search (RAG).\n"
            "5. A model writes the project, streamed live on screen "
            "file by file; a ready-made, secure database layer is added "
            "from templates.\n"
            "6. A fast model checks the code against your requirement; "
            "any missing feature is added.\n"
            "7. Every PHP file is checked with `php -l`; broken files "
            "are fixed and tested again (up to 3 test rounds).\n"
            "8. The project is saved and opens as a chat, where you can "
            "ask questions or download it."
        ),
        "hinglish": (
            "### Kaise kaam karta hai\n"
            "1. Aap request likhte ho.\n"
            "2. Intent router decide karta hai: explanation ya naya "
            "project.\n"
            "3. Agar pehle bahut milta-julta project bana hai, to woh "
            "reuse hota hai ya sirf badli hui files likhi jaati hain.\n"
            "4. Warna semantic search (RAG) se PHP manual ke sabse "
            "relevant hisse dhoondhe jaate hain.\n"
            "5. Model project likhta hai, screen par file by file live "
            "dikhta hai; secure database layer templates se judti hai.\n"
            "6. Ek tez model code ko aapki requirement se milata hai; koi "
            "feature chhoota ho to jod diya jaata hai.\n"
            "7. Har PHP file `php -l` se check hoti hai; toot-ti files "
            "theek hoke dobara test hoti hain (3 test rounds tak).\n"
            "8. Project save hota hai aur chat ki tarah khulta hai, "
            "jahan sawaal pooch sakte ho ya download kar sakte ho."
        ),
    },
    {
        "id": "models",
        "strong": [
            r"\bwhich (ai |llm )?(models?|llms?|ai) (do you|does (it|this|vibe ?coder)|is|are) (use|used)\b",
            r"\b(kaun ?sa|konsa|kaunsa) (model|llm|ai)\b",
            r"\bwhat (ai|llm|model|models) (do you|does it) use\b",
        ],
        "topic": [
            r"\b(models?|llms?|gemini|groq|nvidia|ai)\b.*\b(use|used|uses|lagta|chalta)\b",
            r"\bwhich (model|llm|ai)\b", r"\bpowered by\b",
        ],
        "en": (
            "### AI models used\n"
            "- **Project generation, refactor and debug:** Google "
            "Gemini flash models first (several, each with its own "
            "quota), then Groq, then NVIDIA if Gemini is busy.\n"
            "- **Explanations and project chat:** Groq first "
            "(`gpt-oss-120b`, Qwen, `gpt-oss-20b`), then NVIDIA "
            "(Nemotron and others), with Gemini as the backup.\n"
            "- **Explain-or-build decision:** rules first; if unsure, "
            "the smallest Groq model.\n"
            "- **Images:** only Gemini can read them, so requests with "
            "a screenshot always start on Gemini.\n"
            "- **Questions about this app:** answered from a built-in "
            "FAQ, with no model at all.\n"
            "- **Adaptive thinking:** simple projects use low thinking "
            "(fast); projects with payments, roles or booking conflicts "
            "get medium or high thinking for better logic.\n\n"
            "The model that answered is shown under each reply."
        ),
        "hinglish": (
            "### Kaunse AI models use hote hain\n"
            "- **Project generation, refactor aur debug:** pehle Google "
            "Gemini flash models (kai models, har ek ka alag kota), "
            "Gemini busy ho to Groq, phir NVIDIA.\n"
            "- **Explanation aur project chat:** pehle Groq "
            "(`gpt-oss-120b`, Qwen, `gpt-oss-20b`), phir NVIDIA "
            "(Nemotron waghera), aur Gemini backup.\n"
            "- **Explain ya build ka faisla:** pehle rules; confuse ho "
            "to Groq ka sabse chhota model.\n"
            "- **Images:** sirf Gemini padh sakta hai, isliye screenshot "
            "wali request hamesha Gemini se shuru hoti hai.\n"
            "- **Is app ke baare mein sawaal:** built-in FAQ se jawaab, "
            "koi model use nahi hota.\n"
            "- **Adaptive thinking:** simple projects mein kam thinking "
            "(tez); payment, roles ya booking conflict wale projects ko "
            "medium ya high thinking milti hai, taaki logic behtar ho.\n\n"
            "Har jawaab ke neeche dikhta hai ki kis model ne diya."
        ),
    },
    {
        "id": "testing",
        "strong": [
            r"\bhow (is|does) (the )?test(ing)? (done|happen|work)\b",
            r"\bhow do you test\b",
            r"\btesting kaise (hoti|hota|karta|karte)\b",
        ],
        "topic": [r"\btest(ing|ed|s)?\b", r"\bvalidat(e|ion)\b", r"\bsyntax check\b"],
        "en": (
            "### How testing works\n"
            "- After the project is written, every `.php` file is "
            "checked with `php -l` (PHP's own syntax checker).\n"
            "- Simple mistakes (a leftover ``` fence, a missing `<?php` "
            "tag) are fixed by code, with no AI call.\n"
            "- Other errors go to the debug agent with their line "
            "numbers; it returns only the lines to change (a patch), "
            "so the rest of the file stays untouched.\n"
            "- The project is tested again, up to 3 rounds in total.\n"
            "- The result (passed, or what still fails) is shown in the "
            "project summary. You can run it again any time with "
            "**🧪 Run tests**.\n\n"
            "This is a syntax check: it catches broken PHP code, but it "
            "does not open the pages or connect to a database."
        ),
        "hinglish": (
            "### Testing kaise hoti hai\n"
            "- Project likhne ke baad har `.php` file `php -l` (PHP ka "
            "apna syntax checker) se check hoti hai.\n"
            "- Chhoti galtiyan (bacha hua ``` fence, `<?php` tag na hona) "
            "code se hi theek hoti hain, bina AI call ke.\n"
            "- Baaki errors line numbers ke saath debug agent ke paas "
            "jaate hain; woh sirf badalne wali lines (patch) deta hai, "
            "baaki file waisi hi rehti hai.\n"
            "- Project dobara test hota hai, kul 3 rounds tak.\n"
            "- Result (pass, ya kya abhi bhi fail hai) project summary "
            "mein dikhta hai. **🧪 Run tests** se kabhi bhi dobara chala "
            "sakte ho.\n\n"
            "Yeh syntax check hai: toota hua PHP code pakadta hai, lekin "
            "pages khol ke ya database se jod ke test nahi karta."
        ),
    },
    {
        "id": "rag",
        "strong": [
            r"\b(how|where) (is|does) (the )?rag\b",
            r"\brag (kaise|kahan|kya)\b",
            r"\bknowledge base\b",
            r"\bwhere does (it|this|the data) (get|come)\b",
        ],
        "topic": [r"\brag\b", r"\bembedding", r"\bfaiss\b", r"\bnlp\b", r"\bdata ?source\b"],
        "en": (
            "### RAG (knowledge base)\n"
            "- **Source:** the official PHP manual.\n"
            "- **Preparation** (`rag/ingest.py`): the manual's XML is "
            "cleaned and split into overlapping chunks.\n"
            "- **Embeddings** (`rag/build_index.py`): each chunk is "
            "turned into a vector with `all-MiniLM-L6-v2` and stored in "
            "a FAISS index.\n"
            "- **At question time** (`rag/retriever.py`): the question "
            "is embedded too, and the 3 closest chunks are added to the "
            "model's prompt, so answers follow the real PHP docs."
        ),
        "hinglish": (
            "### RAG (knowledge base)\n"
            "- **Source:** official PHP manual.\n"
            "- **Taiyari** (`rag/ingest.py`): manual ka XML saaf karke "
            "overlap wale chunks mein toda jaata hai.\n"
            "- **Embeddings** (`rag/build_index.py`): har chunk "
            "`all-MiniLM-L6-v2` se vector banta hai aur FAISS index mein "
            "save hota hai.\n"
            "- **Sawaal ke time** (`rag/retriever.py`): sawaal ka bhi "
            "vector banta hai, aur sabse milte-julte 3 chunks prompt mein "
            "jaate hain, taaki jawaab asli PHP docs ke hisaab se ho."
        ),
    },
    {
        "id": "limits",
        "strong": [
            r"\bgenerations? (left|limit)\b",
            r"\bhow many (projects|generations)\b",
            r"\bkitne (projects?|generations?)\b",
            r"\brate limit\b",
        ],
        "topic": [r"\blimit\b", r"\bquota\b", r"\bkitne\b"],
        "en": (
            "### Generation limit\n"
            "- Each user can generate **{per_user} projects every "
            "{window} minutes**. Each one frees up {window} minutes "
            "after it was used.\n"
            "- The whole app allows **{global_limit} projects per hour** "
            "across all users, to protect the shared AI quota.\n"
            "- Explanations, project chat and these FAQ answers do not "
            "count. Failed generations do not count either."
        ),
        "hinglish": (
            "### Generation limit\n"
            "- Har user **{window} minute mein {per_user} projects** bana "
            "sakta hai. Har generation use hone ke {window} minute baad "
            "wapas milti hai.\n"
            "- Shared AI kota bachane ke liye poori app mein sab users "
            "milake **ek ghante mein {global_limit} projects** ban sakte "
            "hain.\n"
            "- Explanation, project chat aur yeh FAQ jawaab nahi ginte. "
            "Fail hui generation bhi nahi ginti."
        ),
    },
    {
        "id": "languages",
        "strong": [
            r"\bwhich languages? (do you|does it|can you)\b",
            r"\b(hindi|hinglish) (support|mein jawab)\b",
            r"\bkaunsi (language|bhasha)\b",
        ],
        "topic": [r"\blanguages?\b", r"\bhindi\b", r"\bhinglish\b", r"\bbhasha\b"],
        "en": (
            "### Languages\n"
            "- Write in **English** and the answer is in English.\n"
            "- Write in **Hinglish** (Hindi in English letters) and the "
            "answer is in Hinglish.\n"
            "- Write in Devanagari, or ask \"in Hindi\", and the answer "
            "is in Hindi.\n"
            "- Code, file names and technical terms always stay in "
            "English. Generated projects are PHP, HTML, CSS, JS and SQL."
        ),
        "hinglish": (
            "### Languages\n"
            "- **English** mein likho to jawaab English mein.\n"
            "- **Hinglish** (English letters mein Hindi) mein likho to "
            "jawaab Hinglish mein.\n"
            "- Devanagari mein likho, ya \"hindi mein\" bolo, to jawaab "
            "Hindi mein.\n"
            "- Code, file names aur technical words hamesha English "
            "mein rehte hain. Projects PHP, HTML, CSS, JS aur SQL mein "
            "bante hain."
        ),
    },
    {
        "id": "stack",
        "strong": [
            r"\btech ?stack\b",
            r"\b(built|made|developed) (with|using|in)\b",
            r"\bkis(me|mein| technology| language) (bana|banaya)\b",
        ],
        "topic": [r"\btechnolog(y|ies)\b", r"\bstack\b", r"\bframework\b", r"\blibrar(y|ies)\b"],
        "en": (
            "### Tech stack\n"
            "- **Language:** Python 3.13, dependencies managed with "
            "Poetry.\n"
            "- **UI:** Streamlit.\n"
            "- **AI:** Google Gemini (`google-genai`), Groq and NVIDIA "
            "NIM through their OpenAI-compatible APIs.\n"
            "- **RAG:** `fastembed` (all-MiniLM-L6-v2) embeddings and "
            "`faiss-cpu`, over the PHP manual.\n"
            "- **Testing:** PHP CLI (`php -l`).\n"
            "- **Generated projects:** PHP 8, PDO, MySQL, HTML, CSS and "
            "JavaScript."
        ),
        "hinglish": (
            "### Tech stack\n"
            "- **Language:** Python 3.13, dependencies Poetry se manage "
            "hoti hain.\n"
            "- **UI:** Streamlit.\n"
            "- **AI:** Google Gemini (`google-genai`), Groq aur NVIDIA "
            "NIM unki OpenAI-compatible APIs se.\n"
            "- **RAG:** PHP manual par `fastembed` (all-MiniLM-L6-v2) "
            "embeddings aur `faiss-cpu`.\n"
            "- **Testing:** PHP CLI (`php -l`).\n"
            "- **Bane hue projects:** PHP 8, PDO, MySQL, HTML, CSS aur "
            "JavaScript."
        ),
    },
    {
        "id": "download",
        "strong": [
            r"\bhow (do|can) i download\b",
            r"\bdownload kaise\b",
            r"\bhow (do|can) i (run|use) (the )?(generated )?project\b",
        ],
        "topic": [r"\bdownload\b", r"\bzip\b", r"\bexport\b"],
        "en": (
            "### Downloading a project\n"
            "- Open the project's chat (it opens by itself after "
            "generation, or from the sidebar).\n"
            "- **📥 Download ZIP** downloads the whole project.\n"
            "- Below it, pick a file in **Download a single file** to "
            "download only that file.\n"
            "- To run it: import `schema.sql` into MySQL, set your "
            "database details in the config file, and start it with "
            "`php -S localhost:8000` (or ask **▶ How to run**)."
        ),
        "hinglish": (
            "### Project download karna\n"
            "- Project ki chat kholo (generation ke baad khud khulti "
            "hai, ya sidebar se).\n"
            "- **📥 Download ZIP** se poora project download hota hai.\n"
            "- Uske neeche **Download a single file** mein file chuno, "
            "sirf woh file download hogi.\n"
            "- Chalane ke liye: `schema.sql` MySQL mein import karo, "
            "config file mein database details daalo, aur "
            "`php -S localhost:8000` se start karo (ya **▶ How to run** "
            "poocho)."
        ),
    },
    {
        "id": "privacy",
        "strong": [
            r"\b(is my|are my) (data|code|prompts?|chats?) (saved|stored|safe|private)\b",
            r"\bprivacy\b",
            r"\b(data|chat) (save|store) (hota|hoti|hote)\b",
        ],
        "topic": [r"\b(saved|stored|store|save)\b", r"\bprivate\b", r"\bsafe\b"],
        "en": (
            "### Your data\n"
            "- Chats and generated projects are saved on the app's "
            "server (`chat_history/` and `generated_projects/`) so they "
            "appear in the sidebar. They are reset when the server is "
            "redeployed.\n"
            "- Prompts are sent to Gemini, Groq or NVIDIA to be "
            "answered. Their free tiers may log prompts, so never "
            "paste passwords, API keys or other secrets.\n"
            "- Your IP address is never stored; only a short hash is "
            "kept in memory for the generation limit."
        ),
        "hinglish": (
            "### Aapka data\n"
            "- Chats aur bane hue projects app ke server par save hote "
            "hain (`chat_history/` aur `generated_projects/`), taaki "
            "sidebar mein dikhein. Server redeploy hone par yeh reset "
            "ho jaate hain.\n"
            "- Prompts jawaab ke liye Gemini, Groq ya NVIDIA ko jaate "
            "hain. Unke free tiers prompts log kar sakte hain, isliye "
            "password, API key ya koi secret kabhi paste mat karo.\n"
            "- Aapka IP address save nahi hota; generation limit ke liye "
            "sirf uska chhota hash memory mein rehta hai."
        ),
    },
]


def _normalize(text):
    return " ".join((text or "").lower().replace("?", " ").split())


def find_faq(question):
    """The matching FAQ entry, or None. No model is called."""

    text = _normalize(question)

    if not text or len(text) > 300:
        return None

    mentions_app = bool(APP_REFERENCE.search(text))

    for entry in FAQ:

        if any(re.search(p, text) for p in entry["strong"]):
            return entry

    if mentions_app:

        for entry in FAQ:

            if any(re.search(p, text) for p in entry["topic"]):
                return entry

    return None


def answer_faq(question, **values):
    """
    Built-in answer for a question about this app, in the user's
    language (English, or Hinglish for Hinglish/Hindi), or None.
    values fill placeholders such as {per_user}.
    """

    entry = find_faq(question)

    if not entry:
        return None

    language = detect_reply_language(question)

    text = entry["en"] if language == ENGLISH else entry["hinglish"]

    try:
        return text.format(**values) if values else text
    except (KeyError, IndexError):
        return text