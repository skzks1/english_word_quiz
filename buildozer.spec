[app]

# (필수) 앱 제목
title = EnglishWordQuiz

# (필수) 최종 APK 파일 버전
version = 1.0.12

# (필수) Python 패키지 요구사항 (Kivy 앱이라면 kivy 필수)
requirements = python3, kivy

# (필수) 패키지 이름 (com.yourdomain.yourapp)
package.name = com.quiz.englishwordquiz

# 패키지 도메인
package.domain = org.test

# Kivy main file to init
source.dir = .
main.py = main.py

# Icon for the application
icon.filename = %(source.dir)s/icon.png

# Android 빌드 설정
[app:android]

# 최소 API 레벨 (Kivy 기본값 21 사용)
android.minapi = 21

# 타겟 API 레벨
android.targetapi = 33

# 필요한 권한 (필요 시 주석 해제)
# android.permissions = INTERNET, WAKE_LOCK

# 이외의 모든 설정은 기본값 유지