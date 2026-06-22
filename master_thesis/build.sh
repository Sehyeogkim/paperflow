#!/usr/bin/env bash
# Compile 20244152_sehyeog_0619.tex → PDF in cwd, aux files into ./log/
# Runs the full pdflatex + bibtex + pdflatex x2 sequence so \cite{} resolves
# against reference/references.bib.
# NOTE: pdflatex returns a non-zero exit code on benign font warnings with this
# Korean class, so we do NOT use `set -e`; success is checked by PDF existence.
cd "$(dirname "$0")"
mkdir -p log
NAME=20244152_sehyeog_0619
TEX="$NAME.tex"
PDF="$NAME.pdf"

# 1) first pass (writes .aux into ./log/)
pdflatex -interaction=nonstopmode -output-directory=log "$TEX" > /dev/null
# 2) resolve citations from reference/references.bib
BIBINPUTS="$PWD:$PWD/reference:" bibtex "log/$NAME" > /dev/null
# 3) two more passes to settle references / ToC / page numbers
pdflatex -interaction=nonstopmode -output-directory=log "$TEX" > /dev/null
pdflatex -interaction=nonstopmode -output-directory=log "$TEX" > /dev/null

if [ -f "log/$PDF" ]; then
  mv -f "log/$PDF" "./$PDF"
  echo "✔ $PDF generated; aux files in ./log/"
else
  echo "�’ build failed: log/$PDF not produced — see log/$NAME.log" >&2
  exit 1
fi
