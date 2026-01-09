FROM docker.io/i386/alpine:3.21.0

ENV KERNEL=virt
ENV ADDPKGS="nodejs docker go"
#  alpine-base alpine-conf openrc
RUN apk add agetty linux-$KERNEL $ADDPKGS

RUN sed -i 's/getty 38400 tty1/agetty --autologin root tty1 linux/' /etc/inittab
RUN echo 'ttyS0::respawn:/sbin/agetty --autologin root -s ttyS0 115200 vt100' >> /etc/inittab
RUN echo "root:" | chpasswd

# RUN setup-hostname localhost

# Adding networking.sh script
RUN echo -e "ip link set eth0 up && udhcpc -i eth0" > /root/networking.sh && chmod +x /root/networking.sh

RUN echo 'console.log("Hello, world!");' > /root/hello.js
RUN wget https://dimathenekov.github.io/go_server.go
RUN wget https://dimathenekov.github.io/node_server.js
RUN wget https://dimathenekov.github.io/hello-world.tar
RUN mv hello-world.tar /root/hello-world.tar

# https://wiki.alpinelinux.org/wiki/Alpine_Linux_in_a_chroot#Preparing_init_services
# hwdrivers mdev
# RUN for i in devfs dmesg; do rc-update add $i sysinit; done
# RUN for i in hwclock modules sysctl hostname syslog bootmisc; do rc-update add $i boot; done
# RUN rc-update add killprocs shutdown

# Generate initramfs with 9p modules
RUN mkinitfs -F "base virtio 9p" $(cat /usr/share/kernel/$KERNEL/kernel.release)
