#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <unistd.h>
#include <assert.h>

#include "socket_server.h"

struct socket_server {
    struct sockaddr_in addr;
    int socket_fd;
    char *buf;
};
