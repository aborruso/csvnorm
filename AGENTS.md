<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## GH CLI comment note

When posting issue comments with `gh`, avoid shell expansion by using a quoted heredoc or a file:

```sh
cat << 'EOF' | gh issue comment 24 -R aborruso/csvnorm -F -
Your comment with `backticks` and `head` here.
EOF
```

or

```sh
gh issue comment 24 -R aborruso/csvnorm -F /path/to/comment.md
```
