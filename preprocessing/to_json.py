import pandas as pd
import json
import os

def convert_tag_code_csv_to_json():
    """
    'preprocessing/file_dir.json'을 읽어, 'tag_code' 디렉토리 안에 있는
    CSV 파일들만 'data/tag_code/training/json' 디렉토리에 JSON으로 저장합니다.
    """
    # JSON 파일을 저장할 디렉토리 경로
    output_dir = 'data/tag_code/training/json'

    # 저장할 디렉토리가 없으면 생성
    os.makedirs(output_dir, exist_ok=True)
    print(f"'{output_dir}' 디렉토리를 확인하고 생성했습니다.")

    # 파일 경로가 담긴 JSON 파일 열기
    file_dir_path = 'preprocessing/file_dir.json'
    try:
        with open(file_dir_path, 'r', encoding='utf-8') as f:
            file_paths = json.load(f)
        print(f"'{file_dir_path}' 파일을 성공적으로 읽었습니다.")
    except FileNotFoundError:
        print(f"오류: '{file_dir_path}' 파일을 찾을 수 없습니다.")
        return
    except json.JSONDecodeError:
        print(f"오류: '{file_dir_path}' 파일이 올바른 JSON 형식이 아닙니다.")
        return

    # 각 파일을 순회하며 JSON으로 변환
    print("\n'tag_code' 디렉토리의 파일 변환을 시작합니다...")
    for key, csv_path in file_paths.items():
        # 파일 경로에 'tag_code'가 포함되어 있는지 확인
        if 'tag_code' in csv_path:
            try:
                # CSV 파일을 DataFrame으로 읽기
                df = pd.read_csv(csv_path, encoding='utf-8-sig')

                # 저장할 JSON 파일 이름 설정
                file_name = os.path.basename(csv_path)
                json_file_name = os.path.splitext(file_name)[0] + '.json'
                json_file_path = os.path.join(output_dir, json_file_name)

                # DataFrame을 JSON 파일로 저장
                df.to_json(json_file_path, orient='records', force_ascii=False, indent=4)
                print(f"✅ 성공: '{csv_path}' -> '{json_file_path}'")

            except FileNotFoundError:
                print(f"⚠️ 경고: '{csv_path}' 파일을 찾을 수 없습니다. 건너뜁니다.")
            except Exception as e:
                print(f"❌ 오류: '{csv_path}' 파일 처리 중 오류 발생: {e}")
        else:
            # 'tag_code'가 경로에 없는 파일은 건너뜀
            print(f"➡️ 건너뜀: '{csv_path}' (tag_code 디렉토리 아님)")


if __name__ == '__main__':
    convert_tag_code_csv_to_json()