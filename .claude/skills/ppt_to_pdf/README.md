# pdf-figure-crop

PDF의 각 페이지에서 위아래 흰 여백을 자동으로 잘라내고, 페이지마다 별도의 PDF 파일로 저장하는 Claude skill.

## 어디에 쓰는 거?

논문 figure들을 한 PDF에 모아둔 상태에서, 각 figure 크기에 맞게 위아래 여백만 잘라서 **개별 PDF로 분리**하고 싶을 때.
- LaTeX `\includegraphics`에 깔끔하게 넣고 싶을 때
- 공저자에게 figure 하나씩 따로 보내고 싶을 때
- PowerPoint에서 export한 figure 묶음 PDF를 정리할 때

좌우 폭은 그대로 유지하고 **위아래만** 자동으로 자릅니다.

## 설치 (Claude Code / Cowork)

이 폴더 전체(`SKILL.md` + `scripts/`)를 Claude의 skills 디렉토리에 넣으면 자동으로 인식돼요.

직접 스크립트로 돌려도 됩니다:

```bash
pip install pymupdf pillow numpy
python scripts/crop_figures.py <입력.pdf> <출력_폴더>
```

## 옵션 조정

`scripts/crop_figures.py` 상단에 세 가지 파라미터가 있어요:

- `WHITE_THRESHOLD` (기본 245): 이 값보다 어두운 픽셀만 "내용물"로 인정. 배경이 살짝 회색이면 250까지 올리세요.
- `MIN_CONTENT_PIXELS` (기본 3): 한 줄에 이 개수 이상의 비-흰 픽셀이 있어야 "내용이 있는 줄"로 인정. 스캔 노이즈 무시하려면 10 정도로.
- `PADDING` (기본 12pt): 내용물 주변에 남길 여백. 더 빡빡하게 자르려면 4~6, 여유 있게 하려면 20~30.

## 동작 원리 (요약)

1. 페이지를 150 DPI 흑백 이미지로 렌더링
2. 각 행(row)별로 비-흰 픽셀 개수를 세서 첫/마지막 "내용 행" 찾기
3. 그 범위를 PDF 좌표로 변환 + 패딩 추가
4. PyMuPDF의 `show_pdf_page(clip=...)`로 벡터 데이터 그대로 새 PDF에 복사 (래스터화 없음)
