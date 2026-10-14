# ASI onboarding

To repozytorium służy do pracy podczas **dwojga pierwszych zajęć** z przedmiotu *Architektury rozwiązań i wdrożeń*.

Na początku pracujemy indywidualnie.
Chcemy upewnić się, że kazdy ma działające środowisko,
potrafi uruchomić notebook od początku do końca
i umie zapisać swoją pracę w GitHubie.
Od trzecich zajęć zaczniemy pracę zespołową nad właściwym projektem semestralnym.

## Wybierz sposób pracy

Masz do wyboru dwie wspierane ścieżki:

- **lokalnie:** conda/Miniforge + VS Code,
- **Codespaces:** gotowe środowisko z pliku `.devcontainer/devcontainer.json`.

Instrukcje poniżej dotyczą pracy lokalnej. Jeśli lokalne środowisko nie działa mimo próby rozwiązania problemu, przejdź na Codespaces.
Nie musisz czekać z pracą na zajęciach.

## Praca lokalna

### 1. Utwórz środowisko

W terminalu, w katalogu repozytorium:

```bash
conda env create -f environment.yml
conda activate asi-ml
python --version
```

Powinna pojawić się wersja Python 3.11.x.

Jeśli środowisko `asi-ml` już istnieje, nie twórz go drugi raz. Zaktualizuj je:

```bash
conda env update -n asi-ml -f environment.yml --prune
conda activate asi-ml
```

### 2. Zarejestruj kernel Jupyter

```bash
python -m ipykernel install --user \
  --name asi-ml \
  --display-name "Python (asi-ml)"
```

W VS Code wybierz dla notebooka kernel **Python (asi-ml)**.

### 3. Włącz pre-commit

```bash
pre-commit install
```

Od tej chwili przed commitem Git automatycznie uruchomi podstawowe kontrole jakości plików.

### 4. Sprawdź środowisko

```bash
python scripts/check_env.py
```

Skrypt zapisze w katalogu repozytorium:

```text
env_report.json
```

Nie edytuj tego pliku ręcznie.

Jeśli skrypt kończy się komunikatem **„Środowisko jest gotowe”**, możesz przejść do notebooka.

## Codespaces — ścieżka awaryjna

Na stronie swojego repozytorium na GitHubie wybierz:

**Code → Codespaces → Create codespace on main**

Konfiguracja repozytorium utworzy środowisko `asi-ml`, zarejestruje kernel i włączy pre-commit automatycznie.

Po otwarciu terminala sprawdź:

```bash
python scripts/check_env.py
```

## Pierwsze zajęcia

Notebook:

```text
notebooks/01_onboarding_eda.ipynb
```

Pracuj kolejno od początku notebooka. Podczas pierwszych zajęć:

- sprawdzisz strukturę danych,
- przyjrzysz się jakości danych,
- zbadasz zmienną docelową,
- wykonasz krótkie EDA,
- zapiszesz własne obserwacje.

Na tym etapie **nie czyścimy jeszcze danych i nie budujemy modelu**.

Przed zakończeniem pracy uruchom w notebooku:

**Restart → Run All**

Wszystkie komórki powinny przejść bez błędów.

Następnie:

```bash
git status
git add notebooks/01_onboarding_eda.ipynb env_report.json
git commit -m "cp1: eda"
git push
```

Na GitHubie sprawdź, czy commit jest widoczny i czy automatyczny check `env` jest zielony.

## Gdy coś nie działa

Zanim zgłosisz problem:

1. przeczytaj pełny komunikat błędu,
2. sprawdź, czy aktywne jest środowisko `asi-ml`,
3. uruchom ponownie `python scripts/check_env.py`,
4. sprawdź, czy problem nie wynika z pominiętego kroku w tej instrukcji.

Jeśli nadal jesteś zablokowany, zgłoś:

- komendę, którą uruchamiasz,
- pełny komunikat błędu jako tekst,
- system operacyjny,
- co zostało już sprawdzone.

Nie wysyłaj samego zrzutu ekranu z fragmentem błędu.

## Drugie zajęcia

Na drugich zajęciach domkniemy workflow od danych do pierwszego modelu oraz dołożymy pracę na gałęzi i Pull Request.
Szczegółowa instrukcja pojawi się wraz z drugim notebookiem.
