# agent-memory/

`memory: project` frontmatter를 가진 subagent의 영속 메모리가 쌓이는 곳.
세션 메인 대화의 auto-memory와는 **별개** — 각 에이전트가 자기 `<에이전트이름>/MEMORY.md`를
스스로 읽고 쓴다 (사람이 직접 쓰는 파일 아님).

## 켜는 법
`.claude/agents/<에이전트>.md` frontmatter에 다음을 추가하면 이 폴더에 디렉토리가 생김:

```yaml
memory: project   # 이 repo 공유 (여기, .claude/agent-memory/)
# memory: local   # 커밋 안 함 (.claude/agent-memory-local/)
# memory: user    # 모든 프로젝트 공유 (~/.claude/agent-memory/)
```

## 쓸 만한 곳 (아직 안 켬, 필요하면 추가)
- `reviewer` / `advisor` 에 붙이면 → 이 author가 자주 하는 실수·문체 약점을
  세션 넘어 누적 기억 → 갈수록 날카로워짐
