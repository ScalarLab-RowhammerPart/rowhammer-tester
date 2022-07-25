#ifndef TCP_SERVER_H
#define TCP_SERVER_H

#include "socket_server.h"

int tcp_server_run(void *arg, socket_server_callback callback, int port, size_t buf_size);

#endif /* TCP_SERVER_H */
