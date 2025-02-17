FROM public.ecr.aws/lambda/python@sha256:63811c90432ba7a9e4de4fe1e9797a48dae0762f1d56cb68636c3d0a7239ff68 as build

# 🔹 필수 패키지 및 Chrome, ChromeDriver 다운로드
RUN dnf install -y unzip fontconfig google-noto-sans-cjk-fonts && \
    curl -Lo "/tmp/chromedriver-linux64.zip" "https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.159/linux64/chromedriver-linux64.zip" && \
    curl -Lo "/tmp/chrome-linux64.zip" "https://storage.googleapis.com/chrome-for-testing-public/132.0.6834.159/linux64/chrome-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/ && \
    unzip /tmp/chrome-linux64.zip -d /opt/ && \
    fc-cache -f -v 
# ✅ 설치된 폰트 리스트 확인
RUN fc-list | grep "Noto"

# ✅ 환경 변수 설정 (자동 한글 폰트 적용)
ENV LANG=ko_KR.UTF-8
ENV FONTCONFIG_PATH="/etc/fonts"

FROM public.ecr.aws/lambda/python@sha256:63811c90432ba7a9e4de4fe1e9797a48dae0762f1d56cb68636c3d0a7239ff68

RUN dnf install -y atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel nss mesa-libgbm \
    fontconfig google-noto-sans-cjk-fonts && \
    fc-cache -f -v

RUN pip install selenium==4.28.1

COPY --from=build /opt/chrome-linux64 /opt/chrome
COPY --from=build /opt/chromedriver-linux64 /opt/

COPY main.py ./
CMD [ "main.handler" ]