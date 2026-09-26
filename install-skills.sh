#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
codex_dir=${CODEX_HOME:-"$HOME/.codex"}
skills_dir="$codex_dir/skills"
skills="vacation-planner restaurant-finder"

mkdir -p "$skills_dir"

for skill in $skills; do
    source_path="$repo_dir/$skill"
    target_path="$skills_dir/$skill"

    if [ ! -f "$source_path/SKILL.md" ]; then
        printf 'Errore: skill non trovata: %s\n' "$source_path" >&2
        exit 1
    fi

    if [ ! -L "$target_path" ] && [ -e "$target_path" ]; then
        printf 'Errore: %s esiste e non e un symlink. Nessun file modificato.\n' "$target_path" >&2
        exit 1
    fi
done

for skill in $skills; do
    source_path="$repo_dir/$skill"
    target_path="$skills_dir/$skill"

    if [ -L "$target_path" ] && [ "$(readlink "$target_path")" = "$source_path" ]; then
        printf 'Gia collegata: %s\n' "$skill"
        continue
    fi

    if [ -L "$target_path" ]; then
        rm "$target_path"
    fi

    ln -s "$source_path" "$target_path"
    printf 'Collegata: %s -> %s\n' "$target_path" "$source_path"
done

printf 'Skill Codex pronte.\n'
