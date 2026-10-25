# MCQApp

**Application web de QCM (Questionnaires à Choix Multiples) avec évaluation par thème, graphiques de performance, historique et export PDF.**  
**Web-based Multiple Choice Question (MCQ) application with theme-based scoring, performance charts, score history, and PDF export.**

🌐 [🇫🇷 Version française](#-français) | [🇬🇧 English version](#-english)

---

## 🇫🇷 Français

### Présentation

**MCQApp** est une application web développée avec **Flask** permettant de créer, passer et analyser des questionnaires à choix multiples (QCM).  
Les questionnaires sont définis dans de simples fichiers **YAML** déposés dans le dossier `data/`. Chaque question peut comporter une ou plusieurs bonnes réponses, être rattachée à un ou plusieurs **thèmes**, posséder un **coefficient de difficulté**, une **image** d'illustration et une **explication**.

À la fin du test, l'application génère et sauvegarde automatiquement un bilan complet comprenant :
- Le score détaillé et le pourcentage de réussite par thème (avec pénalisation des réponses fausses sur les questions à choix multiples).
- Un graphique de performance (**radar** à partir de 3 thèmes, ou **diagramme en barres**).
- La correction détaillée question par question avec code couleur (*Correct*, *Partiel*, *Faux*) et explications.
- Un **rapport PDF** horodaté enregistré automatiquement dans `reports/` sur la machine hôte et téléchargeable depuis l'interface.
- Un **historique des sessions** (`reports/history.csv`) consultable depuis l'onglet **History**.

### Fonctionnalités principales

- **Multi-quiz** : détection automatique de tous les fichiers `.yaml` présents dans le dossier `data/`.
- **Filtrage dynamique par thème** : sélection des thèmes souhaités avant de lancer le quiz.
- **Paramètres de session configurables** :
  - Mélange aléatoire de l'ordre des questions et des propositions.
  - Limitation optionnelle du nombre de questions tirées au sort.
  - Chronomètre (timer) optionnel avec soumission automatique en fin de temps.
- **Choix unique ou multiple** : affichage automatique de boutons radio (1 réponse attendue) ou de cases à cocher (plusieurs réponses possibles).
- **Navigation rapide avec sauvegarde** : passage d'une question à l'autre (*Previous*, *Next* ou boutons directs `Q1`, `Q2`...) en conservant la réponse cochée.
- **Export PDF & Historique sur l'hôte** : génération automatique de `reports/report_<user>_<quiz>_<timestamp>.pdf` et journalisation dans `reports/history.csv`.
- **Sécurité renforcée** : protection des fichiers YAML contre le téléchargement direct, assainissement des noms de fichiers et exécution Docker non-root avec **Gunicorn**.

### Structure du projet

```text
MCQApp/
├── app.py                 # Application Flask (routes, calcul des scores, génération PDF/graphiques, historique)
├── data/                  # Fichiers de quiz (.yaml) et sous-dossiers d'images (monté en lecture seule sous Docker)
│   ├── questions.yaml
│   ├── quiz1.yaml
│   └── System.yaml
├── reports/               # Rapports PDF horodatés et history.csv (monté sur la machine hôte)
├── static/
│   └── css/
│       └── style.css      # Feuille de style (thème sombre)
├── templates/             # Templates HTML (Jinja2 / Bootstrap 5)
│   ├── base.html
│   ├── index.html
│   ├── quiz_start.html
│   ├── quiz_question.html
│   ├── quiz_report.html
│   └── history.html
├── requirements.txt       # Dépendances Python (versions figées + Gunicorn)
├── Dockerfile             # Image Docker (Python 3.12-slim, utilisateur non-root, Gunicorn)
└── docker-compose.yml     # Orchestration Docker Compose avec volumes hôtes
```

### Prérequis

- **Docker & Docker Compose** (recommandé) **ou** **Python 3.10+**.

### Installation et démarrage

#### Option 1 — Avec Docker Compose (recommandé)

```bash
git clone https://github.com/Seb75000/MCQApp.git
cd MCQApp
docker compose up --build -d
```

L'application est accessible sur : **[http://localhost:5000](http://localhost:5000)**

##### Points de montage Docker (machine hôte ↔ conteneur)

Le fichier `docker-compose.yml` configure deux volumes persistants sur la machine hôte :
- `./data:/app/data:ro` : vos fichiers `.yaml` de questions et vos images restent sur la machine hôte (montés en lecture seule dans le conteneur). Vous pouvez ajouter ou modifier un fichier YAML dans `./data` sans reconstruire l'image Docker.
- `./reports:/app/reports` : tous les rapports PDF générés (`report_<user>_<quiz>_<date>.pdf`) ainsi que le fichier `history.csv` sont écrits directement dans le dossier `./reports` de votre machine hôte.

#### Option 2 — Installation locale avec Python

```bash
git clone https://github.com/Seb75000/MCQApp.git
cd MCQApp

# Créer et activer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sous Windows : venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python app.py
```

Ouvrez ensuite **[http://localhost:5000](http://localhost:5000)** dans votre navigateur.

### Utilisation

1. Depuis la page d'accueil, cliquez sur **Start Quiz**.
2. Configurez votre session :
   - Choisissez un **quiz** dans la liste déroulante.
   - Renseignez votre **nom ou identifiant** (`User ID`).
   - Cochez ou décochez les **thèmes** à inclure (chargés dynamiquement selon le quiz choisi).
   - *(Optionnel)* Indiquez un **nombre maximum de questions** et une **durée en minutes** (chronomètre).
   - Activez ou non le **mélange aléatoire des questions**.
3. Répondez aux questions :
   - Utilisez **Previous**, **Next** ou les boutons de **navigation rapide** (`Q1`, `Q2`...) pour parcourir le quiz (la réponse en cours est sauvegardée automatiquement).
   - Cliquez sur **Finish** lorsque vous avez terminé.
4. Consultez votre **rapport de résultats** :
   - Le rapport PDF est automatiquement sauvegardé dans `reports/` sur l'hôte et téléchargeable via **Download PDF report**.
   - Consultez l'historique complet des passages via l'onglet **History** (`/history`).

### Créer ou modifier un quiz

Ajoutez simplement un fichier `<nom_du_quiz>.yaml` dans le dossier `data/` :

```yaml
- id: 1
  question: "Quelle commande permet de lister tous les fichiers, y compris les fichiers cachés, sous Linux ?"
  options:
    - "ls -a"
    - "dir"
    - "list /all"
    - "show hidden"
  correct_answers:
    - "ls -a"
  themes:
    - "Linux"
  difficulty: 2
  image: null
  explanations: "L'option -a affiche toutes les entrées, y compris celles commençant par un point."
```

#### Description des champs YAML

| Champ | Type | Obligatoire | Description |
| :--- | :--- | :---: | :--- |
| `id` | Entier | Oui | Identifiant de la question. |
| `question` | Texte | Oui | Intitulé de la question. |
| `options` | Liste de textes | Oui | Propositions de réponse (mélangées aléatoirement à l'affichage). |
| `correct_answers` | Liste de textes | Oui | Bonne(s) réponse(s) (doivent correspondre exactement aux valeurs de `options`). |
| `themes` | Liste de textes | Oui | Thème(s) évalué(s) par la question (ex. `["Linux", "Network"]`). |
| `difficulty` | Nombre | Non | Pondération de la question dans le calcul du score (défaut : `1`). |
| `image` | Texte ou `null` | Non | Nom du fichier image placé dans `data/<nom_du_quiz>/` (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`). |
| `explanations` | Texte | Non | Explication affichée dans le rapport final et dans le PDF. |
| `multiple` | Booléen | Non | Force l'affichage de cases à cocher même s'il n'y a qu'une seule bonne réponse. |

### Variables d'environnement

| Variable | Valeur par défaut | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | Port d'écoute de l'application. |
| `FLASK_DEBUG` | `false` | Active le mode debug si défini à `1`, `true`, `yes` ou `on`. |
| `SECRET_KEY` | `dev-secret-key-change-me` | Clé secrète Flask pour signer les cookies de session. |
| `DATA_DIR` | `data` | Chemin du dossier contenant les fichiers YAML de quiz. |
| `REPORTS_DIR` | `reports` | Chemin du dossier où sont stockés les PDF et `history.csv`. |

---

## 🇬🇧 English

### Overview

**MCQApp** is a web application built with **Flask** for creating, taking, and evaluating Multiple Choice Question (MCQ) quizzes.  
Quizzes are defined in simple **YAML** files stored in the `data/` directory. Each question can have one or multiple correct answers, belong to one or more **themes**, and include a **difficulty weight**, an optional **image**, and an **explanation**.

Upon completing a quiz, the application automatically generates and saves a comprehensive report featuring:
- Detailed scores and percentages per theme (with penalty for wrong selections on multiple-answer questions).
- A visual performance chart (**radar chart** for 3 or more themes, or a **bar chart**).
- A color-coded question-by-question review (*Correct*, *Partial*, *Wrong*) with explanations.
- A timestamped **PDF report** automatically saved to `reports/` on the host machine and downloadable from the browser.
- A persistent **score history** (`reports/history.csv`) viewable in the **History** tab.

### Key Features

- **Multiple quizzes**: automatically detects all `.yaml` files inside the `data/` folder.
- **Dynamic theme filtering**: select which themes to include before starting the quiz.
- **Configurable quiz sessions**:
  - Automatic shuffling of questions and answer options.
  - Optional maximum number of questions randomly drawn from the pool.
  - Optional countdown timer with automatic submission when time expires.
- **Single & multiple choice**: automatically renders radio buttons (single answer) or checkboxes (multiple answers).
- **Fast navigation with auto-save**: jump between questions (*Previous*, *Next*, or direct `Q1`, `Q2`... buttons) without losing your current selection.
- **Host PDF export & history**: automatically writes `reports/report_<user>_<quiz>_<timestamp>.pdf` and logs attempts to `reports/history.csv`.
- **Hardened security**: blocks direct HTTP access to raw `.yaml` quiz files, sanitizes filenames, and runs as a non-root Docker user under **Gunicorn**.

### Project Structure

```text
MCQApp/
├── app.py                 # Flask application (routes, scoring logic, chart & PDF generation, history)
├── data/                  # Quiz YAML files and image subfolders (mounted read-only in Docker)
│   ├── questions.yaml
│   ├── quiz1.yaml
│   └── System.yaml
├── reports/               # Timestamped PDF reports and history.csv (mounted on the host machine)
├── static/
│   └── css/
│       └── style.css      # Dark theme stylesheet
├── templates/             # HTML templates (Jinja2 / Bootstrap 5)
│   ├── base.html
│   ├── index.html
│   ├── quiz_start.html
│   ├── quiz_question.html
│   ├── quiz_report.html
│   └── history.html
├── requirements.txt       # Pinned Python dependencies (+ Gunicorn)
├── Dockerfile             # Docker image (Python 3.12-slim, non-root user, Gunicorn)
└── docker-compose.yml     # Docker Compose configuration with host volume mounts
```

### Requirements

- **Docker & Docker Compose** (recommended) **or** **Python 3.10+**.

### Installation & Setup

#### Option 1 — With Docker Compose (recommended)

```bash
git clone https://github.com/Seb75000/MCQApp.git
cd MCQApp
docker compose up --build -d
```

The application will be available at: **[http://localhost:5000](http://localhost:5000)**

##### Docker Volume Mounts (Host ↔ Container)

`docker-compose.yml` configures two bind mounts on the host machine:
- `./data:/app/data:ro`: keeps your `.yaml` quiz files and images on the host machine (mounted read-only inside the container). You can add or edit YAML files in `./data` on the host without rebuilding the container.
- `./reports:/app/reports`: all generated PDF reports (`report_<user>_<quiz>_<timestamp>.pdf`) and `history.csv` are saved directly into `./reports` on your host machine.

#### Option 2 — Local Python installation

```bash
git clone https://github.com/Seb75000/MCQApp.git
cd MCQApp

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

Then open **[http://localhost:5000](http://localhost:5000)** in your browser.

### Usage

1. On the home page, click **Start Quiz**.
2. Configure your quiz session:
   - Choose a **quiz** from the dropdown menu.
   - Enter your **Name / User ID**.
   - Check or uncheck the **themes** you want to be tested on (loaded dynamically for the selected quiz).
   - *(Optional)* Set a **maximum number of questions** and a **timer (in minutes)**.
   - Toggle **question order shuffling**.
3. Answer the questions:
   - Use **Previous**, **Next**, or the **Fast navigation** buttons (`Q1`, `Q2`...) to move through the quiz (your current selection is saved automatically).
   - Click **Finish** when done.
4. Review your **quiz report**:
   - The PDF report is automatically saved in `reports/` on the host and can also be downloaded via **Download PDF report**.
   - View all past attempts in the **History** tab (`/history`).

### Creating or Editing a Quiz

Create a `<quiz_name>.yaml` file inside the `data/` folder:

```yaml
- id: 1
  question: "Which command is used to list all files, including hidden ones, in Linux?"
  options:
    - "ls -a"
    - "dir"
    - "list /all"
    - "show hidden"
  correct_answers:
    - "ls -a"
  themes:
    - "Linux"
  difficulty: 2
  image: null
  explanations: "The -a flag lists all entries, including dotfiles."
```

#### YAML Field Reference

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `id` | Integer | Yes | Question identifier. |
| `question` | String | Yes | Question prompt. |
| `options` | List of strings | Yes | Answer choices (automatically shuffled when displayed). |
| `correct_answers` | List of strings | Yes | Correct option(s) (must exactly match entries in `options`). |
| `themes` | List of strings | Yes | Theme(s) associated with the question (e.g., `["Linux", "Network"]`). |
| `difficulty` | Number | No | Weight of the question in score calculations (default: `1`). |
| `image` | String or `null` | No | Image filename located in `data/<quiz_name>/` (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`). |
| `explanations` | String | No | Explanation shown in the final web and PDF reports. |
| `multiple` | Boolean | No | Forces checkboxes even when there is only one correct answer. |

### Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `5000` | Port on which the server listens. |
| `FLASK_DEBUG` | `false` | Enables Flask debug mode when set to `1`, `true`, `yes`, or `on`. |
| `SECRET_KEY` | `dev-secret-key-change-me` | Flask secret key used to sign session cookies. |
| `DATA_DIR` | `data` | Directory path containing quiz YAML files. |
| `REPORTS_DIR` | `reports` | Directory path where PDF reports and `history.csv` are stored. |
