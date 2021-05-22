sudo -s
apt update
apt install \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    libbz2-dev

wget -c https://www.python.org/ftp/python/3.8.9/Python-3.8.9.tgz -O - | sudo tar -xz -C /etc
cd Python-3.8.9
./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall
echo `python3.8 --version`
python3.8 -m venv venv
