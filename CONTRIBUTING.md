# Contributing / Mitwirken

## English

After cloning, activate the local hook from the repository root. To propose a change, stage only the intended files, review the staged diff and run the commands below in a development environment with pytest installed. A nonzero guard exit blocks the commit. If it flags a report, remove it from the index with `git rm --cached -- <path>` and keep the working copy in a private directory. Use synthetic examples in issues, tests and pull requests. Describe the tested platform and any limitations.

## Deutsch

Aktiviere nach dem Klonen im Projektverzeichnis den lokalen Hook. Merke nur die beabsichtigten Dateien vor, lies den vorgemerkten Diff und führe die folgenden Befehle in einer Entwicklungsumgebung mit pytest aus. Ein Fehlerstatus des Guards sperrt den Commit. Entferne beanstandete Berichte mit `git rm --cached -- <Pfad>` aus dem Index und bewahre die Arbeitskopie in einem privaten Ordner auf. Nutze synthetische Beispiele für Issues, Tests und Pull Requests. Nenne getestete Plattformen und Einschränkungen.

```sh
git config --local core.hooksPath .githooks
git diff --cached
python scripts/privacy_guard.py
python -m pytest tests/test_privacy_guard.py
```

Please submit original contributions only when you can license them for use and redistribution under the project license. Contributors retain rights they hold in their contributions. / Reiche eigene Beiträge ein, für die du die Nutzungsrechte gemäß der Projektlizenz einräumen kannst. Mitwirkende behalten die Rechte an ihren eigenen Beiträgen. [License / Lizenz](LICENSE)
