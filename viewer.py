import json
import os

def search_quiz_by_id():
    # 1. JSON 파일 로드
    file_path = 'quiz_database.json'
    
    if not os.path.exists(file_path):
        print(f"오류: '{file_path}' 파일이 존재하지 않습니다. 먼저 추출 프로그램을 실행해주세요.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        quiz_db = json.load(f)

    # 2. 사용자로부터 ID 입력 받기
    search_id = input("조회할 문제 ID(6자리 숫자)를 입력하세요: ").strip()

    # 3. 데이터 검색
    # quiz_db는 리스트 형태이므로 하나씩 꺼내어 id가 일치하는지 확인합니다.
    target_quiz = next((item for item in quiz_db if item["id"] == search_id), None)

    # 4. 결과 출력
    if target_quiz:
        print("\n" + "="*50)
        print(f" [문제 조회 결과] ")
        print("="*50)
        print(f"▶ ID    : {target_quiz['id']}")
        print(f"▶ 단원  : {target_quiz['unit']}단원")
        print(f"▶ 본문  : \n{target_quiz['content']}")
        
        if target_quiz['image_urls']:
            print(f"▶ 이미지 경로: {', '.join(target_quiz['image_urls'])}")
        else:
            print("▶ 이미지 : 없음")
            
        print("-" * 50)
        print(" [보기(Options)] ")
        for i, option in enumerate(target_quiz['options'], 1):
            print(f" {i}. {option}")
        print("="*50 + "\n")
    else:
        print(f"\nID '{search_id}'에 해당하는 문제를 찾을 수 없습니다. 다시 확인해주세요.")

# 프로그램 실행
if __name__ == "__main__":
    while True:
        search_quiz_by_id()
        cont = input("계속 조회하시겠습니까? (y/n): ").lower()
        if cont != 'y':
            print("프로그램을 종료합니다.")
            break