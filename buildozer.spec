name: Android Build with Buildozer

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Code
      uses: actions/checkout@v4

    - name: Setup Java (for Android tools)
      uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '17'

    - name: Install system and native build dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y --no-install-recommends \
          build-essential git wget curl unzip ca-certificates \
          autoconf automake libtool libtool-bin m4 \
          pkg-config gettext \
          libffi-dev libssl-dev zlib1g-dev \
          python3-dev

    - name: Show versions (debug)
      run: |
        autoconf --version || true
        autoreconf --version || true
        libtoolize --version || true
        python --version
        pip --version

    - name: Conditional autoupdate/autoreconf (only if configure.ac exists)
      run: |
        if [ -f configure.ac ]; then
          echo "configure.ac found — running autoupdate/autoreconf"
          autoupdate || true
          autoreconf -fi || true
        else
          echo "configure.ac not found — skipping autoupdate/autoreconf"
        fi

    - name: Upgrade pip and install Python build tools
      run: |
        python -m pip install --upgrade pip setuptools wheel
        pip install --upgrade Cython buildozer python-for-android

    - name: Run Buildozer (verbose)
      env:
        BUILD_ACCEPT_SDK_LICENSE: 1
      run: |
        buildozer android debug --verbose

    - name: Upload Artifact
      uses: actions/upload-artifact@v4
      with:
        name: english-word-quiz-apk
        path: bin/*.apk