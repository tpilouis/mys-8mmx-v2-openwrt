FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential clang flex bison g++ gawk gcc-multilib g++-multilib gettext \
    git libncurses-dev libssl-dev python3 python3-setuptools python3-pyelftools \
    rsync swig unzip zlib1g-dev file wget curl ca-certificates patch time \
    subversion bzip2 xz-utils zstd cpio ecj fastjar perl autoconf automake \
    libtool libelf-dev pkg-config dosfstools mtools parted fdisk u-boot-tools \
    device-tree-compiler e2fsprogs qemu-user-static
RUN userdel -r ubuntu && groupadd -g 1000 builder && useradd -m -u 1000 -g 1000 -s /bin/bash builder
USER builder
WORKDIR /work
CMD ["/bin/bash"]
