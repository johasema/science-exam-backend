import fitz  # PyMuPDF
import json
import os
import re

def extract_science_quiz(pdf_path):
    doc = fitz.open(pdf_path)
    quiz_data = []
    
    # 이미지 저장 폴더 생성
    if not os.path.exists('images'):
        os.makedirs('images')

    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text()
        
        # 1. ID 추출 (# 뒤의 6자리)
        id_match = re.search(r'#(\d{6})', text)
        question_id = id_match.group(1) if id_match else f"unknown_{page_index}"

        # 2. Unit 추출 (Unit: 뒤의 숫자)
        unit_match = re.search(r'Unit:\s*(\d+)', text)
        unit = int(unit_match.group(1)) if unit_match else 0

        # 3. Content 및 Options 분리
        # content: 뒤부터 Options: 전까지를 content로 취급
        content_pattern = re.compile(r'content:(.*?)Options:', re.DOTALL)
        content_match = content_pattern.search(text)
        content_text = content_match.group(1).strip() if content_match else ""

        # 4. Options 추출 (Options: 뒤의 내용)
        options_pattern = re.compile(r'Options:(.*)', re.DOTALL)
        options_match = options_pattern.search(text)
        options_raw = options_match.group(1).strip() if options_match else ""
        # 원문자나 번호 등으로 분리 (샘플에 따라 조정 가능)
        options = [opt.strip() for opt in options_raw.split('\n') if opt.strip()]

        # 5. 이미지 추출 및 URL(경로) 변환
        image_list = page.get_images(full=True)
        image_urls = []
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 이미지 파일 저장 (ID 기반 이름 생성)
            image_filename = f"images/{question_id}_{img_index}.png"
            with open(image_filename, "wb") as f:
                f.write(image_bytes)
            
            # 나중에 Firebase 업로드 후 이 경로를 URL로 교체하게 됩니다.
            image_urls.append(image_filename)

        # 데이터 구조화
        quiz_item = {
            "id": question_id,
            "unit": unit,
            "content": content_text,
            "image_urls": image_urls,
            "options": options
        }
        quiz_data.append(quiz_item)

    # 6. JSON 파일로 저장
    with open('quiz_database.json', 'w', encoding='utf-8') as f:
        json.dump(quiz_data, f, ensure_ascii=False, indent=4)

    print(f"추출 완료! 총 {len(quiz_data)}개의 문제가 quiz_database.json에 저장되었습니다.")

# 실행
extract_science_quiz("통합과학샘플.pdf")