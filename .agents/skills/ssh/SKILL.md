---
name: ssh
description: SSH into one of the registered KAIST servers (harvey/ws1/ws2) or run a one-shot command on it — e.g. to fetch result numbers (Sobol indices, R², rupture-location %) from the HPC and fill the `[TODO]` placeholders in the paper drafts.
argument-hint: "<harvey|ws1|ws2> [command]"
---

# /ssh — connect to a remote server or run a one-shot command

이 paperflow 프로젝트의 초안에는 원격(HPC/워크스테이션)에서만 얻을 수 있는 정량 수치가
`[TODO: 값]`로 비어 있다(예: Sobol S1/S_total, R²_LOO, 파열위치 %). 이 스킬로 그 값을
서버에서 직접 가져와 채운다. 또는 일반적인 원격 명령 실행에도 쓴다.

## Servers

| alias | host | port | user |
|---|---|---|---|
| `harvey` | harvey.kaist.ac.kr | 10022 | jeff |
| `ws1` (= `workstation1`) | cvbml01.kaist.ac.kr | 22 | jeff |
| `ws2` (= `workstation2`) | cvbml02.kaist.ac.kr | 22 | jeff |

**Auth:** SSH 키 전용 (`~/.ssh/id_ed25519`), 별칭은 `~/.ssh/config`에 등록돼 있음.
"Permission denied (publickey)"가 나면 그 서버에 키가 아직 신뢰되지 않은 것 → 사용자에게
`ssh-copy-id <alias>`를 안내한다.

## Action

1. **별칭만** 주어지면 (대화형 세션) → 이 도구 안에서는 대화형 셸이 잘 안 되므로, 사용자에게
   프롬프트에 직접 **`! ssh <alias>`** 를 입력하라고 안내한다.
2. **별칭 + 명령**이면 → `Bash`로 `ssh <alias> "<command>"`를 실행하고 출력을 보고한다.
3. 항상 **SSH config 별칭**(`harvey`, `ws1`, `ws2`)을 쓴다. 호스트명·포트를 하드코딩하지 않는다.
   별칭이 없으면 먼저 `~/.ssh/config`를 설정한다.

## 데이터 가져오기 패턴 (이 프로젝트의 주 용도)

원격에서 값을 가져올 때는 **비대화형 원샷**으로, 한 번에 필요한 것만:

```bash
# 예: Sobol 결과 csv의 상위 인자 확인
ssh ws1 "cat ~/plaque/results/sobol_VI1_LAP.csv | head"
# 예: 결과 파일을 로컬 data/로 복사
scp ws1:~/plaque/results/sobol_*.csv \
    /home/jeff/project/3_journal_template/paperflow/master_thesis/data/
```

- 가져온 수치는 **출처(서버:경로)를 명시**하고, 해당 `[TODO: 값]` 자리에 채운다.
- 값을 지어내지 않는다. 파일에 없으면 없다고 보고하고 어디를 봐야 할지 사용자에게 묻는다.
- 큰 디렉터리 전체 복사는 피하고, 필요한 파일만 `scp`/`rsync`로 좁혀서 가져온다.

Args: $ARGUMENTS
