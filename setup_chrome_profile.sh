#!/usr/bin/env bash
# DigiKey 스크래퍼 Chrome 쿠키 초기 설정
# 스크래퍼 전용 Chrome 프로파일로 DigiKey를 열어 CF 쿠키를 저장합니다.

set -e

SCRAPER_PROFILE="${HOME}/.local/share/digikey-scraper/chrome-profile"
CHROME_BIN=""
for c in /opt/google/chrome/chrome /usr/bin/google-chrome-stable /usr/bin/google-chrome /usr/bin/chromium; do
    if [ -x "$c" ]; then CHROME_BIN="$c"; break; fi
done

if [ -z "$CHROME_BIN" ]; then
    echo "[ERROR] Chrome을 찾을 수 없습니다. Google Chrome을 설치해주세요."
    exit 1
fi

mkdir -p "$SCRAPER_PROFILE"

# 손상된 Preferences 제거 (크래시 방지)
if [ -f "$SCRAPER_PROFILE/Default/Preferences" ]; then
    python3 -c "
import json, sys
try:
    d = json.loads(open('${SCRAPER_PROFILE}/Default/Preferences').read())
    name = d.get('profile', {}).get('name', '')
    # 이중 인코딩 감지: 정상 UTF-8 문자열에 ÃÂÃÂ 패턴이 없어야 함
    if 'ÃÂ' in name or len(name.encode()) > len(name) * 3:
        print('손상된 Preferences 감지 → 삭제')
        import os; os.remove('${SCRAPER_PROFILE}/Default/Preferences')
    else:
        print('Preferences 정상')
except Exception:
    import os, sys
    if os.path.exists('${SCRAPER_PROFILE}/Default/Preferences'):
        print('Preferences 파싱 실패 → 삭제')
        os.remove('${SCRAPER_PROFILE}/Default/Preferences')
" 2>/dev/null
fi

# 락 파일 제거
for f in SingletonLock SingletonSocket SingletonCookie DevToolsActivePort; do
    rm -f "$SCRAPER_PROFILE/$f"
done

echo "================================================================"
echo " DigiKey CF 쿠키 설정 (스크래퍼 전용 프로파일)"
echo "================================================================"
echo ""
echo "[1단계] 스크래퍼 Chrome 프로파일로 DigiKey를 엽니다..."
echo "        Chrome 창이 열리면 DigiKey 페이지가 로드될 때까지 기다리세요."
echo ""

"$CHROME_BIN" \
    --no-sandbox \
    --user-data-dir="$SCRAPER_PROFILE" \
    --no-first-run \
    --no-default-browser-check \
    "https://www.digikey.com/en/products/result?keywords=lm358" \
    2>/dev/null &

CHROME_PID=$!
echo "  Chrome PID: $CHROME_PID"
echo ""
echo "[2단계] Chrome 창에서:"
echo "        - Cloudflare '잠시만 기다리십시오...' 화면이 자동으로 통과될 때까지 대기"
echo "        - DigiKey 검색 결과 페이지가 완전히 로드되면 확인"
echo ""
echo "  준비되면 Enter를 눌러주세요..."
read -r

echo ""
echo "[3단계] Chrome 창을 닫아주세요."
echo "        (같은 프로파일을 Chrome과 앱이 동시에 사용할 수 없습니다)"
echo ""
echo "  Chrome 종료 후 Enter를 눌러주세요..."
read -r

# 프로세스 정리
kill "$CHROME_PID" 2>/dev/null || true
sleep 1
# 락 파일 제거 (Chrome이 남겼을 수 있음)
for f in SingletonLock SingletonSocket SingletonCookie DevToolsActivePort; do
    rm -f "$SCRAPER_PROFILE/$f"
done

echo ""
echo "================================================================"
echo " 설정 완료. 아래 명령으로 앱을 실행하세요:"
echo ""
echo "   source .venv/bin/activate"
echo "   python digikey_price_scraper.py"
echo ""
echo " 쿠키 유효기간 약 24~48시간."
echo " 만료 시 이 스크립트를 다시 실행하세요."
echo "================================================================"
