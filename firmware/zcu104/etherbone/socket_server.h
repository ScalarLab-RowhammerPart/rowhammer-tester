#ifndef SOCKET_SERVER_H
#define SOCKET_SERVER_H

#include "debug.h"

// Callback function called on incoming packets
//
// It passes the number of bytes received (recv_len) and the buffer with the data.
// The callback should process the packet, write response to the buffer (at most
// buf_size bytes) and return number of response bytes written to be sent as reply.
// It can return -1 to signalize an error and terminate the server.
// arg can be used to pass user data.
typedef int (*socket_server_callback)(void *arg, char *buf, size_t buf_size, size_t recv_len);

int socket_server_run(void *arg, socket_server_callback callback, int port, size_t buf_size);

#endif /* SOCKET_SERVER_H */