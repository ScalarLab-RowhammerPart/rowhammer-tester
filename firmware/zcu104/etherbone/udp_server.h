#ifndef UDP_SERVER_H
#define UDP_SERVER_H

#include "socket_server.h"

int udp_server_run(void *arg, socket_server_callback callback, int port, size_t buf_size);

#endif /* UDP_SERVER_H */
